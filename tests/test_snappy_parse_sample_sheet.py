"""Tests for ``cubi_tk.snappy.parse_sample_sheet``."""

import pathlib

from biomedsheets.io_tsv import read_germline_tsv_sheet
from biomedsheets.naming import NAMING_ONLY_SECONDARY_ID

from cubi_tk.snappy.parse_sample_sheet import ParseSampleSheet


def test_yield_ngs_library_names():
    """Tests ParseSampleSheet.yield_ngs_library_names()"""
    # Instantiate
    parser = ParseSampleSheet()

    # Define expected
    expected_batch_one = [f"P00{i}-N1-DNA1-WGS1" for i in (1, 2, 3)]
    expected_batch_two = [f"P00{i}-N1-DNA1-WGS1" for i in (4, 5, 6)]
    expected_batch_three = ["P007-N1-DNA1-WGS1"]

    # Define input
    sheet_path = pathlib.Path(__file__).resolve().parent / "data" / "germline_sheet.tsv"
    with open(sheet_path, "rt") as f_sheet:
        sheet = read_germline_tsv_sheet(f=f_sheet, naming_scheme=NAMING_ONLY_SECONDARY_ID)

    # Test max batch = 1
    actual = parser.yield_ngs_library_names(sheet=sheet, max_batch=1)
    for name_ in actual:
        assert name_ in expected_batch_one

    # Test min batch = 2
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=2)
    for name_ in actual:
        expected_list = expected_batch_two + expected_batch_three
        assert name_ in expected_list

    # Test min batch = 3
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=3)
    for name_ in actual:
        assert name_ in expected_batch_three


def test_yield_ngs_library_names_multi_batch():
    """Tests ParseSampleSheet.yield_ngs_library_names() - multiple batches in sample sheet"""
    # Instantiate
    parser = ParseSampleSheet()

    # Define expected
    expected_batch_one = ["P001-N1-DNA1-WGS1", "P002-N1-DNA1-WGS1", "P003-N1-DNA1-WGS1"]
    expected_batch_two = ["P004-N1-DNA1-WGS1", "P005-N1-DNA1-WGS1", "P006-N1-DNA1-WGS1"]
    expected_batch_three = ["P007-N1-DNA1-WGS1", "P008-N1-DNA1-WGS1", "P009-N1-DNA1-WGS1"]
    expected_batch_four = ["P010-N1-DNA1-WGS1", "P011-N1-DNA1-WGS1", "P012-N1-DNA1-WGS1"]
    expected_batch_five = ["P013-N1-DNA1-WGS1", "P014-N1-DNA1-WGS1"]
    expected_batch_six = ["P015-N1-DNA1-WGS1"]

    # Define input
    sheet_path = pathlib.Path(__file__).resolve().parent / "data" / "germline_sheet_multi_batch.tsv"
    with open(sheet_path, "rt") as f_sheet:
        sheet = read_germline_tsv_sheet(f=f_sheet, naming_scheme=NAMING_ONLY_SECONDARY_ID)

    # Sanity test - no constraints
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=None, max_batch=None)
    expected_list = (
        expected_batch_one
        + expected_batch_two
        + expected_batch_three
        + expected_batch_four
        + expected_batch_five
        + expected_batch_six
    )
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 2, max batch = None
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=2, max_batch=None)
    expected_list = (
        expected_batch_two
        + expected_batch_three
        + expected_batch_four
        + expected_batch_five
        + expected_batch_six
    )
    for name_ in actual:
        assert name_ in expected_list
    # Test min batch = 2, max batch = 3
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=2, max_batch=3)
    expected_list = expected_batch_two + expected_batch_three
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 3, max batch = 5
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=3, max_batch=5)
    expected_list = expected_batch_three + expected_batch_four + expected_batch_five
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 5, max batch = 5
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=5, max_batch=5)
    expected_list = expected_batch_five
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 6, max batch = 6
    actual = parser.yield_ngs_library_names(sheet=sheet, min_batch=6, max_batch=6)
    expected_list = expected_batch_six
    for name_ in actual:
        assert name_ in expected_list


def test_yield_sample_names():
    """Tests ParseSampleSheet.yield_sample_names()"""
    # Instantiate
    parser = ParseSampleSheet()

    # Define expected
    expected_batch_one = [f"P00{i}" for i in (1, 2, 3)]
    expected_batch_two = [f"P00{i}" for i in (4, 5, 6)]
    expected_batch_three = ["P007"]

    # Define input
    sheet_path = pathlib.Path(__file__).resolve().parent / "data" / "germline_sheet.tsv"
    with open(sheet_path, "rt") as f_sheet:
        sheet = read_germline_tsv_sheet(f=f_sheet, naming_scheme=NAMING_ONLY_SECONDARY_ID)

    # Test max batch = 1
    actual = parser.yield_sample_names(sheet=sheet, max_batch=1)
    for name_ in actual:
        assert name_ in expected_batch_one

    # Test min batch = 2
    actual = parser.yield_sample_names(sheet=sheet, min_batch=2)
    for name_ in actual:
        expected_list = expected_batch_two + expected_batch_three
        assert name_ in expected_list

    # Test min batch = 3
    actual = parser.yield_sample_names(sheet=sheet, min_batch=3)
    for name_ in actual:
        assert name_ in expected_batch_three


def test_yield_sample_names_multi_batch():
    """Tests ParseSampleSheet.yield_sample_names() - multiple batches in sample sheet"""
    # Instantiate
    parser = ParseSampleSheet()

    # Define expected
    expected_batch_one = [f"P00{i}" for i in (1, 2, 3)]
    expected_batch_two = [f"P00{i}" for i in (4, 5, 6)]
    expected_batch_three = [f"P00{i}" for i in (7, 8, 9)]
    expected_batch_four = [f"P0{i}" for i in (10, 11, 12)]
    expected_batch_five = [f"P0{i}" for i in (13, 14)]
    expected_batch_six = ["P015"]

    # Define input
    sheet_path = pathlib.Path(__file__).resolve().parent / "data" / "germline_sheet_multi_batch.tsv"
    with open(sheet_path, "rt") as f_sheet:
        sheet = read_germline_tsv_sheet(f=f_sheet, naming_scheme=NAMING_ONLY_SECONDARY_ID)

    # Sanity test - no constraints
    actual = parser.yield_sample_names(sheet=sheet, min_batch=None, max_batch=None)
    expected_list = (
        expected_batch_one
        + expected_batch_two
        + expected_batch_three
        + expected_batch_four
        + expected_batch_five
        + expected_batch_six
    )
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 2, max batch = None
    actual = parser.yield_sample_names(sheet=sheet, min_batch=2, max_batch=None)
    expected_list = (
        expected_batch_two
        + expected_batch_three
        + expected_batch_four
        + expected_batch_five
        + expected_batch_six
    )
    for name_ in actual:
        assert name_ in expected_list
    # Test min batch = 2, max batch = 3
    actual = parser.yield_sample_names(sheet=sheet, min_batch=2, max_batch=3)
    expected_list = expected_batch_two + expected_batch_three
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 3, max batch = 5
    actual = parser.yield_sample_names(sheet=sheet, min_batch=3, max_batch=5)
    expected_list = expected_batch_three + expected_batch_four + expected_batch_five
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 5, max batch = 5
    actual = parser.yield_sample_names(sheet=sheet, min_batch=5, max_batch=5)
    expected_list = expected_batch_five
    for name_ in actual:
        assert name_ in expected_list

    # Test min batch = 6, max batch = 6
    actual = parser.yield_sample_names(sheet=sheet, min_batch=6, max_batch=6)
    expected_list = expected_batch_six
    for name_ in actual:
        assert name_ in expected_list