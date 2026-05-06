# Implementation Plan: NeoWs Backfill Script

## Overview

Implement a standalone Python backfill script (`scripts/backfill_neows.py`) that fetches 12 months of historical NEO data from NASA's NeoWs API in 7-day windows and inserts records into `raw.neo_feeds`. The script is self-contained, resilient to HTTP errors, and respects rate limits. Tests are placed in `scripts/tests/test_backfill_neows.py` using pytest and Hypothesis.

## Tasks

- [x] 1. Create script file with configuration and DB setup
  - [x] 1.1 Create `scripts/backfill_neows.py` with top-level configuration constants
    - Define `DATABASE_URL` (from `os.environ["DATABASE_URL"]`), `NASA_API_KEY` (with `DEMO_KEY` fallback), `NEOWS_URL`, `REQUEST_TIMEOUT=30`, `WINDOW_DAYS=7`, `BACKFILL_DAYS=365`, `RATE_LIMIT_DELAY=1.0`
    - Set up logging with `logging.basicConfig`
    - Validate `DATABASE_URL` is set, exit with error message if missing
    - Set up SQLAlchemy `create_engine` + `sessionmaker` within the script (standalone, no imports from collector)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 9.1_

  - [x] 1.2 Implement `generate_windows(start_date, end_date, step_days=7)` function
    - Pure function returning `list[tuple[date, date]]`
    - Each window: `window_end = window_start + timedelta(days=step_days - 1)`
    - Last window clamped to `end_date` if remaining days < step_days
    - Advance by `step_days` each iteration (next start = previous end + 1 day)
    - _Requirements: 1.1, 1.2, 1.3_

  - [x]* 1.3 Write property test for window generation
    - **Property 1: Window generation covers full date range with valid spans**
    - **Validates: Requirements 1.2, 1.3**
    - Create `scripts/tests/__init__.py` and `scripts/tests/test_backfill_neows.py`
    - Use Hypothesis to generate arbitrary start_date, end_date pairs
    - Assert: windows are contiguous, first starts on start_date, last ends on/before end_date, every date covered exactly once, each window spans at most step_days days inclusive

  - [x]* 1.4 Write property test for date formatting round-trip
    - **Property 2: Date formatting round-trip**
    - **Validates: Requirements 2.2**
    - Use Hypothesis date strategy to generate arbitrary dates
    - Assert: `date.fromisoformat(d.isoformat()) == d` for all generated dates

- [x] 2. Implement record extraction and API interaction
  - [x] 2.1 Implement `extract_records(response_json)` function
    - Pure function transforming NeoWs API response dict into flat list of record dicts
    - Each record: `{"neo_id": obj["id"], "name": obj["name"], "raw_data": json.dumps(obj), "feed_date": date_key}`
    - Iterate over `response_json["near_earth_objects"]` dict keyed by date strings
    - _Requirements: 3.1_

  - [x]* 2.2 Write property test for record extraction
    - **Property 3: NEO record extraction preserves data**
    - **Validates: Requirements 3.1**
    - Use Hypothesis to generate synthetic NeoWs response structures with arbitrary date keys and NEO objects
    - Assert: output count equals total NEO objects across all dates, each record has correct neo_id, name, raw_data, and feed_date

  - [x] 2.3 Implement `process_window(session, client, window_start, window_end)` function
    - Make HTTP GET to NeoWs API with `start_date`, `end_date`, `api_key` params and `timeout=30`
    - Call `extract_records` on response JSON
    - Execute INSERT ON CONFLICT DO NOTHING for each record
    - Track and return `(inserted_count, skipped_count)`
    - Commit transaction after all records for the window
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3_

  - [x]* 2.4 Write unit tests for `process_window`
    - Mock httpx client to return sample NeoWs response
    - Verify correct API params (start_date, end_date, api_key, timeout)
    - Verify INSERT SQL is executed with correct parameters
    - Verify session.commit() is called
    - _Requirements: 2.1, 2.4, 3.1, 3.3_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement main orchestrator with error handling and rate limiting
  - [x] 4.1 Implement `run_backfill()` function
    - Calculate `start_date = date.today() - timedelta(days=365)` and `end_date = date.today()`
    - Log total date range being processed
    - Call `generate_windows(start_date, end_date)`
    - Loop over windows: call `process_window`, catch `httpx.HTTPError` and general exceptions, log errors with window dates, continue to next window
    - Sleep `RATE_LIMIT_DELAY` seconds between requests
    - Log per-window progress (dates, inserted, skipped)
    - Log final summary (total inserted, total skipped, total errors)
    - _Requirements: 1.1, 1.2, 4.1, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3_

  - [x] 4.2 Add `if __name__ == "__main__"` entry point
    - Call `run_backfill()` when script is executed directly
    - _Requirements: 8.1_

  - [x]* 4.3 Write property test for resilience (all windows attempted)
    - **Property 4: All windows attempted regardless of failures**
    - **Validates: Requirements 7.2, 7.3**
    - Use Hypothesis to generate a list of windows and a random subset that should fail
    - Mock `process_window` to raise `httpx.HTTPError` for the failing subset
    - Assert: total attempted windows equals total generated windows

  - [x]* 4.4 Write unit tests for `run_backfill` orchestration
    - Test that DEMO_KEY fallback is used when NASA_API_KEY is unset
    - Test that script exits with error when DATABASE_URL is missing
    - Test that `time.sleep(1)` is called between windows
    - Test logging output contains expected window info and summary
    - _Requirements: 4.1, 5.1, 5.2, 5.3, 6.3, 6.4, 7.1_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The script replicates the INSERT pattern from `collector/nasa_neows.py` but is fully standalone
- Property tests use Hypothesis (already available in the project)
- All code examples use Python, matching the design document
- The critical constraint (window_end = window_start + timedelta(days=6)) is enforced in task 1.2
