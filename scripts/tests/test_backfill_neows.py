"""
Tests for scripts/backfill_neows.py

Includes property-based tests (Hypothesis) and unit tests (pytest).
"""

import json
import sys
import os
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Property Test 1: Window generation covers full date range with valid spans
# Feature: neows-backfill, Property 1: Window generation covers full date range
# **Validates: Requirements 1.2, 1.3**
# ---------------------------------------------------------------------------


@given(
    start_date=st.dates(min_value=date(2000, 1, 1), max_value=date(2030, 12, 31)),
    duration_days=st.integers(min_value=1, max_value=730),
    step_days=st.integers(min_value=1, max_value=30),
)
@settings(max_examples=200, deadline=None)
def test_property_window_generation_covers_full_range(
    start_date, duration_days, step_days
):
    """
    Property 1: Window generation covers full date range with valid spans.

    For any valid start_date and end_date where start_date < end_date:
    - Windows are contiguous (each starts day after previous ends)
    - First window starts on start_date
    - Last window ends on or before end_date
    - Every date in [start_date, end_date] is covered exactly once
    - Each window spans at most step_days calendar days (inclusive)
    """
    from backfill_neows import generate_windows

    end_date = start_date + timedelta(days=duration_days)
    # Clamp to avoid overflow
    assume(end_date <= date(2031, 12, 31))

    windows = generate_windows(start_date, end_date, step_days)

    assert len(windows) > 0, "Should generate at least one window"

    # First window starts on start_date
    assert windows[0][0] == start_date

    # Last window ends on or before end_date
    assert windows[-1][1] <= end_date

    # Windows are contiguous
    for i in range(1, len(windows)):
        prev_end = windows[i - 1][1]
        curr_start = windows[i][0]
        assert curr_start == prev_end + timedelta(days=1), (
            f"Gap between window {i-1} end ({prev_end}) and window {i} start ({curr_start})"
        )

    # Each window spans at most step_days days (inclusive)
    for w_start, w_end in windows:
        span = (w_end - w_start).days + 1
        assert span <= step_days, (
            f"Window [{w_start}, {w_end}] spans {span} days, max is {step_days}"
        )
        assert span >= 1, "Window must span at least 1 day"

    # Every date in [start_date, end_date] is covered exactly once
    covered_dates = set()
    for w_start, w_end in windows:
        d = w_start
        while d <= w_end:
            assert d not in covered_dates, f"Date {d} covered more than once"
            covered_dates.add(d)
            d += timedelta(days=1)

    # All dates in range are covered
    expected_dates = set()
    d = start_date
    while d <= end_date:
        expected_dates.add(d)
        d += timedelta(days=1)

    assert covered_dates == expected_dates, "Not all dates in range are covered"


# ---------------------------------------------------------------------------
# Property Test 2: Date formatting round-trip
# Feature: neows-backfill, Property 2: Date formatting round-trip
# **Validates: Requirements 2.2**
# ---------------------------------------------------------------------------


@given(d=st.dates())
@settings(max_examples=200, deadline=None)
def test_property_date_formatting_round_trip(d):
    """
    Property 2: Date formatting round-trip.

    For any valid date object, formatting as ISO 8601 and parsing back
    SHALL produce the original date value.
    """
    assert date.fromisoformat(d.isoformat()) == d


# ---------------------------------------------------------------------------
# Property Test 3: NEO record extraction preserves data
# Feature: neows-backfill, Property 3: NEO record extraction preserves data
# **Validates: Requirements 3.1**
# ---------------------------------------------------------------------------

# Strategy for generating a single NEO object
neo_object_strategy = st.fixed_dictionaries(
    {
        "id": st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Nd", "Lu", "Ll"))),
        "name": st.text(min_size=1, max_size=50),
    }
).flatmap(
    lambda base: st.fixed_dictionaries(
        {
            "id": st.just(base["id"]),
            "name": st.just(base["name"]),
            "extra_field": st.text(max_size=20),
        }
    )
)

# Strategy for generating a NeoWs API response
neows_response_strategy = st.fixed_dictionaries(
    {
        "near_earth_objects": st.dictionaries(
            keys=st.dates(
                min_value=date(2020, 1, 1), max_value=date(2025, 12, 31)
            ).map(lambda d: d.isoformat()),
            values=st.lists(neo_object_strategy, min_size=0, max_size=5),
            min_size=0,
            max_size=7,
        )
    }
)


@given(response=neows_response_strategy)
@settings(max_examples=200, deadline=None)
def test_property_record_extraction_preserves_data(response):
    """
    Property 3: NEO record extraction preserves data.

    For any valid NeoWs API response:
    - Output count equals total NEO objects across all dates
    - Each record has correct neo_id, name, raw_data, and feed_date
    """
    from backfill_neows import extract_records

    records = extract_records(response)

    neo_by_date = response.get("near_earth_objects", {})
    total_objects = sum(len(objs) for objs in neo_by_date.values())

    assert len(records) == total_objects, (
        f"Expected {total_objects} records, got {len(records)}"
    )

    # Build a lookup of expected records
    expected = []
    for date_key, objects in neo_by_date.items():
        for obj in objects:
            expected.append((obj["id"], obj["name"], json.dumps(obj), date_key))

    for record in records:
        assert "neo_id" in record
        assert "name" in record
        assert "raw_data" in record
        assert "feed_date" in record

        # Verify raw_data is valid JSON and round-trips correctly
        parsed = json.loads(record["raw_data"])
        assert parsed["id"] == record["neo_id"]
        assert parsed["name"] == record["name"]

        # Verify feed_date is one of the date keys in the response
        assert record["feed_date"] in neo_by_date


# ---------------------------------------------------------------------------
# Property Test 4: All windows attempted regardless of failures
# Feature: neows-backfill, Property 4: All windows attempted regardless of failures
# **Validates: Requirements 7.2, 7.3**
# ---------------------------------------------------------------------------


@given(
    start_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 1, 1)),
    duration_days=st.integers(min_value=1, max_value=60),
    failing_indices=st.frozensets(st.integers(min_value=0, max_value=20)),
)
@settings(max_examples=100, deadline=None)
def test_property_all_windows_attempted_despite_failures(
    start_date, duration_days, failing_indices
):
    """
    Property 4: All windows attempted regardless of failures.

    For any sequence of windows and any subset that produce HTTP errors,
    the backfill SHALL attempt every window exactly once.
    """
    import httpx as httpx_mod
    from backfill_neows import generate_windows

    end_date = start_date + timedelta(days=duration_days)
    windows = generate_windows(start_date, end_date, 7)

    attempted = []

    def mock_process_window(session, client, w_start, w_end):
        idx = next(
            (i for i, (s, e) in enumerate(windows) if s == w_start and e == w_end),
            None,
        )
        attempted.append((w_start, w_end))
        if idx in failing_indices:
            raise httpx_mod.HTTPError("Simulated HTTP error")
        return (1, 0)

    with (
        patch("backfill_neows.generate_windows", return_value=windows),
        patch("backfill_neows.process_window", side_effect=mock_process_window),
        patch("backfill_neows.SessionLocal", return_value=MagicMock()),
        patch("backfill_neows.time.sleep"),
    ):
        from backfill_neows import run_backfill

        run_backfill()

    assert len(attempted) == len(windows), (
        f"Expected {len(windows)} attempts, got {len(attempted)}"
    )
    assert set(attempted) == set(windows), "Not all windows were attempted"


# ---------------------------------------------------------------------------
# Unit tests for generate_windows
# ---------------------------------------------------------------------------


def test_generate_windows_single_window():
    """A range shorter than step_days produces exactly one window."""
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 1, 5)
    windows = generate_windows(start, end, 7)
    assert windows == [(date(2024, 1, 1), date(2024, 1, 5))]


def test_generate_windows_exact_multiple():
    """A range that is an exact multiple of step_days produces correct windows."""
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 1, 14)  # 14 days = 2 windows of 7
    windows = generate_windows(start, end, 7)
    assert windows == [
        (date(2024, 1, 1), date(2024, 1, 7)),
        (date(2024, 1, 8), date(2024, 1, 14)),
    ]


def test_generate_windows_last_window_clamped():
    """Last window is clamped to end_date when remaining days < step_days."""
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 1, 10)  # 10 days: window1=[1-7], window2=[8-10]
    windows = generate_windows(start, end, 7)
    assert windows == [
        (date(2024, 1, 1), date(2024, 1, 7)),
        (date(2024, 1, 8), date(2024, 1, 10)),
    ]


def test_generate_windows_same_day():
    """start_date == end_date produces a single one-day window."""
    from backfill_neows import generate_windows

    d = date(2024, 6, 15)
    windows = generate_windows(d, d, 7)
    assert windows == [(d, d)]


def test_generate_windows_7day_window_end_is_start_plus_6():
    """Critical: 7-day window uses timedelta(days=6), not days=7."""
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 12, 31)
    windows = generate_windows(start, end, 7)
    # First window must end on Jan 7 (start + 6 days)
    assert windows[0][1] == date(2024, 1, 7)


# ---------------------------------------------------------------------------
# Unit tests for extract_records
# ---------------------------------------------------------------------------


def test_extract_records_empty_response():
    """Empty near_earth_objects returns empty list."""
    from backfill_neows import extract_records

    result = extract_records({"near_earth_objects": {}})
    assert result == []


def test_extract_records_missing_key():
    """Missing near_earth_objects key returns empty list."""
    from backfill_neows import extract_records

    result = extract_records({})
    assert result == []


def test_extract_records_single_date_single_object():
    """Single date with single object produces one record."""
    from backfill_neows import extract_records

    obj = {"id": "12345", "name": "Test NEO", "extra": "data"}
    response = {"near_earth_objects": {"2024-01-15": [obj]}}
    records = extract_records(response)

    assert len(records) == 1
    assert records[0]["neo_id"] == "12345"
    assert records[0]["name"] == "Test NEO"
    assert records[0]["feed_date"] == "2024-01-15"
    assert json.loads(records[0]["raw_data"]) == obj


def test_extract_records_multiple_dates():
    """Multiple dates produce records for each object."""
    from backfill_neows import extract_records

    response = {
        "near_earth_objects": {
            "2024-01-15": [
                {"id": "1", "name": "NEO 1"},
                {"id": "2", "name": "NEO 2"},
            ],
            "2024-01-16": [
                {"id": "3", "name": "NEO 3"},
            ],
        }
    }
    records = extract_records(response)
    assert len(records) == 3
    feed_dates = {r["feed_date"] for r in records}
    assert feed_dates == {"2024-01-15", "2024-01-16"}


# ---------------------------------------------------------------------------
# Unit tests for process_window
# ---------------------------------------------------------------------------


def test_process_window_calls_api_with_correct_params():
    """process_window calls the API with correct start_date, end_date, api_key."""
    import httpx
    from backfill_neows import process_window

    mock_response = MagicMock()
    mock_response.json.return_value = {"near_earth_objects": {}}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    mock_session = MagicMock()
    mock_session.execute.return_value = MagicMock(rowcount=0)

    w_start = date(2024, 1, 1)
    w_end = date(2024, 1, 7)

    with patch("backfill_neows.NASA_API_KEY", "TEST_KEY"):
        process_window(mock_session, mock_client, w_start, w_end)

    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    # Check via the actual call
    _, kwargs = mock_client.get.call_args
    assert kwargs["params"]["start_date"] == "2024-01-01"
    assert kwargs["params"]["end_date"] == "2024-01-07"
    assert kwargs["timeout"] == 30


def test_process_window_commits_transaction():
    """process_window commits the session after inserting records."""
    from backfill_neows import process_window

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "near_earth_objects": {
            "2024-01-01": [{"id": "1", "name": "NEO 1"}]
        }
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    mock_session = MagicMock()
    mock_session.execute.return_value = MagicMock(rowcount=1)

    process_window(mock_session, mock_client, date(2024, 1, 1), date(2024, 1, 7))

    mock_session.commit.assert_called_once()


def test_process_window_returns_inserted_skipped_counts():
    """process_window returns correct (inserted, skipped) tuple."""
    from backfill_neows import process_window

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "near_earth_objects": {
            "2024-01-01": [
                {"id": "1", "name": "NEO 1"},
                {"id": "2", "name": "NEO 2"},
                {"id": "3", "name": "NEO 3"},
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    # First two inserted (rowcount=1), third skipped (rowcount=0)
    mock_session = MagicMock()
    mock_session.execute.side_effect = [
        MagicMock(rowcount=1),
        MagicMock(rowcount=1),
        MagicMock(rowcount=0),
    ]

    inserted, skipped = process_window(
        mock_session, mock_client, date(2024, 1, 1), date(2024, 1, 7)
    )

    assert inserted == 2
    assert skipped == 1


def test_process_window_propagates_http_error():
    """process_window lets httpx.HTTPError propagate to caller."""
    import httpx
    from backfill_neows import process_window

    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.HTTPError("Connection failed")

    mock_session = MagicMock()

    with pytest.raises(httpx.HTTPError):
        process_window(mock_session, mock_client, date(2024, 1, 1), date(2024, 1, 7))


# ---------------------------------------------------------------------------
# Unit tests for run_backfill
# ---------------------------------------------------------------------------


def test_run_backfill_sleeps_between_windows():
    """run_backfill calls time.sleep(RATE_LIMIT_DELAY) between windows."""
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 1, 14)
    windows = generate_windows(start, end, 7)  # 2 windows

    with (
        patch("backfill_neows.generate_windows", return_value=windows),
        patch("backfill_neows.process_window", return_value=(1, 0)),
        patch("backfill_neows.SessionLocal", return_value=MagicMock()),
        patch("backfill_neows.time.sleep") as mock_sleep,
    ):
        from backfill_neows import run_backfill

        run_backfill()

    assert mock_sleep.call_count == len(windows)


def test_run_backfill_logs_summary(caplog):
    """run_backfill logs a final summary with totals."""
    import logging
    from backfill_neows import generate_windows

    start = date(2024, 1, 1)
    end = date(2024, 1, 7)
    windows = generate_windows(start, end, 7)

    with (
        patch("backfill_neows.generate_windows", return_value=windows),
        patch("backfill_neows.process_window", return_value=(5, 2)),
        patch("backfill_neows.SessionLocal", return_value=MagicMock()),
        patch("backfill_neows.time.sleep"),
        caplog.at_level(logging.INFO, logger="backfill_neows"),
    ):
        from backfill_neows import run_backfill

        run_backfill()

    log_text = " ".join(caplog.messages)
    assert "inserted" in log_text.lower() or "complete" in log_text.lower()
