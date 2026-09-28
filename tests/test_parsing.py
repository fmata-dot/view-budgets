import pytest

from budget_sync.parsing import (
    build_preview,
    is_blank_row,
    parse_census_row,
    parse_labor_row,
)

VALID_LABOR = {
    "ID": "",
    "Org": "CSNHC",
    "FacilityID": "56",
    "FacilityCode": "",
    "PositionID": "1021",
    "PositionName": "RN",
    "Type": "HPPD",
    "Input": "3.2",
    "WageAmount": "38.50",
    "WeekendWork": "N",
    "StartDate": "2026-10-01",
    "EndDate": "2026-10-31",
    "AltPPDInput": "",
}

VALID_CENSUS = {
    "ID": "",
    "Org": "CSNHC",
    "FacilityID": "56",
    "FacilityCode": "",
    "PayerType": "Independent Living Days",
    "Input": "32",
    "StartDate": "2026-10-01",
    "EndDate": "2026-10-31",
}


def test_parse_labor_row_valid():
    row = parse_labor_row(VALID_LABOR)
    assert row["facility_id"] == "56"
    assert row["type"] == "HPPD"
    assert row["id"] is None  # blank ID -> insert


def test_parse_labor_row_existing_id_is_update():
    record = dict(VALID_LABOR, ID="108965")
    row = parse_labor_row(record)
    assert row["id"] == "108965"


def test_parse_labor_row_missing_required_field():
    record = dict(VALID_LABOR, FacilityID="")
    with pytest.raises(ValueError, match="FacilityID"):
        parse_labor_row(record)


def test_parse_labor_row_invalid_type():
    record = dict(VALID_LABOR, Type="Hourly")
    with pytest.raises(ValueError, match="Type"):
        parse_labor_row(record)


def test_parse_labor_row_non_numeric_input():
    record = dict(VALID_LABOR, Input="three point two")
    with pytest.raises(ValueError, match="Input must be numeric"):
        parse_labor_row(record)


def test_parse_census_row_valid():
    row = parse_census_row(VALID_CENSUS)
    assert row["payer_type"] == "Independent Living Days"
    assert row["input"] == "32"


def test_parse_census_row_missing_required_field():
    record = dict(VALID_CENSUS, PayerType="")
    with pytest.raises(ValueError, match="PayerType"):
        parse_census_row(record)


def test_parse_census_row_non_numeric_input():
    record = dict(VALID_CENSUS, Input="lots")
    with pytest.raises(ValueError, match="Input must be numeric"):
        parse_census_row(record)


def test_is_blank_row_true_for_all_empty():
    assert is_blank_row(["", "  ", None, ""])


def test_is_blank_row_false_if_any_cell_has_content():
    assert not is_blank_row(["", "CSNHC", ""])


def test_build_preview_labor_shows_insert_and_update():
    rows = [parse_labor_row(VALID_LABOR), parse_labor_row(dict(VALID_LABOR, ID="108965"))]
    preview = build_preview("labor", rows)
    assert "INSERT" in preview
    assert "UPDATE" in preview
    assert "FacilityID=56" in preview


def test_build_preview_census():
    rows = [parse_census_row(VALID_CENSUS)]
    preview = build_preview("census", rows)
    assert "PayerType=Independent Living Days" in preview
