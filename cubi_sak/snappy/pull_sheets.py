"""``cubi-sak snappy pull-sheet``: pull BiomedSheet files from SODAR.

More Information
----------------

- Also see ``cubi-sak snappy`` :ref:`cli_main <CLI documentation>` and ``cubi-sak snappy pull-sheet --help`` for more information.
- `SNAPPY Pipeline GitLab Project <https://cubi-gitlab.bihealth.org/CUBI/Pipelines/snappy>`__.
- `BiomedSheet Documentation <https://biomedsheets.readthedocs.io/en/master/>`__.
"""

import argparse
import os
import pathlib
from uuid import UUID
import typing

import attr
from logzero import logger
import toml

from ..common import CommonConfig, find_base_path, overwrite_helper
from ..sodar.api import Client
from .models import load_datasets
from .isa_support import InvestigationTraversal, IsaNodeVisitor

#: Paths to search the global configuration in.
GLOBAL_CONFIG_PATHS = ("~/.cubitkrc.toml",)

#: Template for the to-be-generated file.
HEADER_TPL = (
    "[Metadata]",
    "schema\tgermline_variants",
    "schema_version\tv1",
    "",
    "[Custom Fields]",
    "key\tannotatedEntity\tdocs\ttype\tminimum\tmaximum\tunit\tchoices\tpattern",
    "batchNo\tbioEntity\tBatch No.\tinteger\t.\t.\t.\t.\t.",
    "familyId\tbioEntity\tFamily\tstring\t.\t.\t.\t.\t.",
    "projectUuid\tbioEntity\tProject UUID\tstring\t.\t.\t.\t.\t.",
    "libraryKit\tngsLibrary\tEnrichment kit\tstring\t.\t.\t.\t.\t.",
    "",
    "[Data]",
    (
        "familyId\tpatientName\tfatherName\tmotherName\tsex\tisAffected\tlibraryType\tfolderName"
        "\tbatchNo\thpoTerms\tprojectUuid\tseqPlatform\tlibraryKit"
    ),
)

#: Mapping from ISA-tab sex to sample sheet sex.
MAPPING_SEX = {"female": "F", "male": "M", "unknown": "U", None: "."}

#: Mapping from disease status to sample sheet status.
MAPPING_STATUS = {"affected": "Y", "carrier": "Y", "unaffected": "N", "unknown": ".", None: "."}


@attr.s(frozen=True, auto_attribs=True)
class PullSheetsConfig:
    """Configuration for the ``cubi-sak snappy pull-sheets`` command."""

    #: Global configuration.
    global_config: CommonConfig

    base_path: typing.Optional[pathlib.Path]
    yes: bool
    dry_run: bool
    show_diff: bool
    show_diff_side_by_side: bool
    library_types: typing.Tuple[str]

    @staticmethod
    def create(args, global_config, toml_config=None):
        # toml_config = toml_config or {}
        return PullSheetsConfig(
            global_config=global_config,
            base_path=pathlib.Path(args.base_path),
            yes=args.yes,
            dry_run=args.dry_run,
            show_diff=args.show_diff,
            show_diff_side_by_side=args.show_diff_side_by_side,
            library_types=tuple(args.library_types),
        )


@attr.s(frozen=True, auto_attribs=True)
class Source:
    family: typing.Optional[str]
    source_name: str
    batch_no: int
    father: str
    mother: str
    sex: str
    affected: str
    sample_name: str


@attr.s(frozen=True, auto_attribs=True)
class Sample:
    source: Source
    library_name: str
    library_type: str
    folder_name: str
    seq_platform: str
    library_kit: str


def strip(x):
    if hasattr(x, "strip"):
        return x.strip()
    else:
        return x


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    """Setup argument parser for ``cubi-sak snappy pull-sheet``."""
    parser.add_argument("--hidden-cmd", dest="snappy_cmd", default=run, help=argparse.SUPPRESS)

    parser.add_argument(
        "--base-path",
        default=os.getcwd(),
        required=False,
        help=(
            "Base path of project (contains '.snappy_pipeline/' etc.), spiders up from current "
            "work directory and falls back to current working directory by default."
        ),
    )

    parser.add_argument(
        "--yes", default=False, action="store_true", help="Assume all answers are yes."
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        default=False,
        action="store_true",
        help="Perform a dry run, i.e., don't change anything only display change, implies '--show-diff'.",
    )
    parser.add_argument(
        "--no-show-diff",
        "-D",
        dest="show_diff",
        default=True,
        action="store_false",
        help="Don't show change when creating/updating sample sheets.",
    )
    parser.add_argument(
        "--show-diff-side-by-side",
        default=False,
        action="store_true",
        help="Show diff side by side instead of unified.",
    )

    parser.add_argument(
        "--library-types", help="Library type(s) to use, comma-separated, default is to use all."
    )


def load_toml_config(args):
    # Load configuration from TOML cubitkrc file, if any.
    if args.config:
        config_paths = (args.config,)
    else:
        config_paths = GLOBAL_CONFIG_PATHS
    for config_path in config_paths:
        config_path = os.path.expanduser(os.path.expandvars(config_path))
        if os.path.exists(config_path):
            with open(config_path, "rt") as tomlf:
                return toml.load(tomlf)
    else:
        logger.info("Could not find any of the global configuration files %s.", config_paths)
        return None


def check_args(args) -> int:
    """Argument checks that can be checked at program startup but that cannot be sensibly checked with ``argparse``."""
    any_error = False

    # Postprocess arguments.
    if args.library_types:
        args.library_types = args.library_types.split(",")  # pragma: nocover
    else:
        args.library_types = []

    return int(any_error)


def first_value(key, node_path, default=None, ignore_case=True):
    for node in node_path:
        for attr_type in ("characteristics", "parameter_values"):
            for x in getattr(node, attr_type, ()):
                if (ignore_case and x.name.lower() == key.lower()) or (
                    not ignore_case and x.name == key
                ):
                    return ";".join(x.value)
    return default


class SampleSheetBuilder(IsaNodeVisitor):
    def __init__(self):
        #: Source by sample name.
        self.sources = {}
        #: Sample by sample name.
        self.samples = {}

    def on_visit_material(self, material, node_path, study=None, assay=None):
        super().on_visit_material(material, node_path, study, assay)
        material_path = [x for x in node_path if hasattr(x, "type")]
        source = material_path[0]
        if material.type == "Sample Name" and assay is None:
            sample = material
            characteristics = {c.name: c for c in source.characteristics}
            self.sources[material.name] = Source(
                family=characteristics["Family"].value[0],
                source_name=source.name,
                batch_no=characteristics["Batch"].value[0],
                father=characteristics["Father"].value[0],
                mother=characteristics["Mother"].value[0],
                sex=characteristics["Sex"].value[0],
                affected=characteristics["Disease status"].value[0],
                sample_name=sample.name,
            )
        elif material.type == "Library Name":
            library = material
            sample = material_path[0]
            if library.name.split("-")[-1].startswith("WGS"):
                library_type = "WGS"
            elif library.name.split("-")[-1].startswith("WES"):
                library_type = "WES"
            elif library.name.split("-")[-1].startswith("Panel_seq"):
                library_type = "Panel_seq"
            else:
                raise Exception("Cannot infer library type from %s" % library.name)

            self.samples[sample.name] = Sample(
                source=self.sources[sample.name],
                library_name=library.name,
                library_type=library_type,
                folder_name=first_value("Folder Name", node_path),
                seq_platform=first_value("Instrument Model", node_path),
                library_kit=first_value("Library Kit", node_path),
            )


def build_sheet(config: PullSheetsConfig, project_uuid: typing.Union[str, UUID]) -> str:
    """Build sheet TSV file."""

    result = []

    # Obtain ISA-tab from SODAR REST API.
    client = Client(config.global_config.sodar_server_url, config.global_config.sodar_api_token)
    isa = client.samplesheets.get(project_uuid)

    builder = SampleSheetBuilder()
    iwalker = InvestigationTraversal(isa.investigation, isa.studies, isa.assays)
    iwalker.run(builder)

    # Generate the resulting sample sheet.
    result.append("\n".join(HEADER_TPL))
    for sample_name, source in builder.sources.items():
        sample = builder.samples.get(sample_name, None)
        row = [
            source.family or "FAM",
            source.source_name or ".",
            source.father or "0",
            source.mother or "0",
            MAPPING_SEX[source.sex.lower()],
            MAPPING_STATUS[source.affected.lower()],
            sample.library_type or "." if sample else ".",
            sample.folder_name or "." if sample else ".",
            "0" if source.batch_no is None else source.batch_no,
            ".",
            str(project_uuid),
            "Illumina",
            sample.library_kit or "." if source else ".",
        ]
        result.append("\t".join(row))
    result.append("")

    return "\n".join(result)


def run(
    args, _parser: argparse.ArgumentParser, _subparser: argparse.ArgumentParser
) -> typing.Optional[int]:
    """Run ``cubi-sak snappy pull-sheet``."""
    res: typing.Optional[int] = check_args(args)
    if res:  # pragma: nocover
        return res

    logger.info("Starting to pull sheet...")
    logger.info("  Args: %s", args)

    logger.debug("Load config...")
    toml_config = load_toml_config(args)
    global_config = CommonConfig.create(args, toml_config)
    args.base_path = find_base_path(args.base_path)
    config = PullSheetsConfig.create(args, global_config, toml_config)

    config_path = config.base_path / ".snappy_pipeline"
    datasets = load_datasets(config_path / "config.yaml")
    logger.info("Pulling for %d datasets", len(datasets))
    for dataset in datasets.values():
        if dataset.sodar_uuid:
            overwrite_helper(
                config_path / dataset.sheet_file,
                build_sheet(config, dataset.sodar_uuid),
                do_write=not args.dry_run,
                show_diff=True,
                show_diff_side_by_side=args.show_diff_side_by_side,
                answer_yes=args.yes,
            )

    return None
