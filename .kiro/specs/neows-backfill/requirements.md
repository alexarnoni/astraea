# Requirements Document

## Introduction

Script standalone de backfill (`scripts/backfill_neows.py`) que reutiliza a lógica do coletor NeoWs existente para preencher 12 meses de dados históricos de Near-Earth Objects (NEOs) na tabela `raw.neo_feeds`. O script itera semana a semana, respeita rate limits da NASA API e é resiliente a falhas de rede.

## Glossary

- **Backfill_Script**: O script Python localizado em `scripts/backfill_neows.py` que executa o preenchimento histórico de dados NEO.
- **NeoWs_API**: A API NASA Near Earth Object Web Service disponível em `https://api.nasa.gov/neo/rest/v1/feed`.
- **Week_Window**: Um intervalo de 7 dias definido por start_date e end_date usado para consultar a NeoWs_API.
- **NEO_Record**: Um registro de Near-Earth Object contendo neo_id, name, raw_data (JSON) e feed_date.
- **Database_Connection**: Conexão PostgreSQL configurada via SQLAlchemy usando create_engine e sessionmaker.

## Requirements

### Requirement 1: Date Range Iteration

**User Story:** As a data engineer, I want the script to iterate over 12 months of history in 7-day windows, so that all historical NEO data is fetched systematically.

#### Acceptance Criteria

1. WHEN executed, THE Backfill_Script SHALL calculate the start date as today minus 365 days and the end date as today.
2. WHEN iterating, THE Backfill_Script SHALL advance in 7-day increments from the calculated start date until reaching today.
3. IF the remaining days until today are fewer than 7, THEN THE Backfill_Script SHALL use today as the end_date for the final Week_Window.

### Requirement 2: NeoWs API Calls

**User Story:** As a data engineer, I want each week window to query the NeoWs API with exact start_date and end_date, so that I receive the correct NEO data for each period.

#### Acceptance Criteria

1. WHEN processing a Week_Window, THE Backfill_Script SHALL call the NeoWs_API with params start_date, end_date, and api_key.
2. THE Backfill_Script SHALL format start_date and end_date as ISO 8601 date strings (YYYY-MM-DD) in the API request.
3. THE Backfill_Script SHALL use httpx as the HTTP client library for all API requests.
4. THE Backfill_Script SHALL set a request timeout of 30 seconds for each API call.

### Requirement 3: Data Insertion

**User Story:** As a data engineer, I want NEO records inserted using the same upsert logic as the existing collector, so that duplicates are handled gracefully.

#### Acceptance Criteria

1. WHEN the NeoWs_API returns data for a Week_Window, THE Backfill_Script SHALL insert each NEO_Record into `raw.neo_feeds` using the SQL statement: `INSERT INTO raw.neo_feeds (neo_id, name, raw_data, feed_date) VALUES (:neo_id, :name, cast(:raw_data as jsonb), :feed_date) ON CONFLICT (neo_id, feed_date) DO NOTHING`.
2. WHEN a NEO_Record conflicts with an existing record on (neo_id, feed_date), THE Backfill_Script SHALL skip the insert without raising an error.
3. WHEN all NEO_Records for a Week_Window are processed, THE Backfill_Script SHALL commit the transaction for that window.

### Requirement 4: Rate Limiting

**User Story:** As a data engineer, I want the script to respect NASA API rate limits, so that requests are not throttled or blocked.

#### Acceptance Criteria

1. WHEN a Week_Window request completes, THE Backfill_Script SHALL wait 1 second before initiating the next API request.

### Requirement 5: Progress Logging

**User Story:** As a data engineer, I want to see progress logs for each window, so that I can monitor the backfill execution.

#### Acceptance Criteria

1. WHEN a Week_Window is processed successfully, THE Backfill_Script SHALL log the window dates (start_date and end_date), the count of inserted records, and the count of skipped records.
2. WHEN the backfill starts, THE Backfill_Script SHALL log the total date range being processed.
3. WHEN the backfill completes, THE Backfill_Script SHALL log a summary with total inserted and total skipped counts.

### Requirement 6: Environment Configuration

**User Story:** As a data engineer, I want the script to read configuration from environment variables, so that it works in different environments without code changes.

#### Acceptance Criteria

1. THE Backfill_Script SHALL read the database connection string from the DATABASE_URL environment variable.
2. THE Backfill_Script SHALL read the NASA API key from the NASA_API_KEY environment variable.
3. IF the NASA_API_KEY environment variable is not set, THEN THE Backfill_Script SHALL use "DEMO_KEY" as the fallback value.
4. IF the DATABASE_URL environment variable is not set, THEN THE Backfill_Script SHALL exit with a descriptive error message.

### Requirement 7: Error Resilience

**User Story:** As a data engineer, I want the script to continue processing remaining windows when one fails, so that a single HTTP error does not abort the entire backfill.

#### Acceptance Criteria

1. IF an HTTP error occurs for a Week_Window request, THEN THE Backfill_Script SHALL log the error with the window dates and the error details.
2. IF an HTTP error occurs for a Week_Window request, THEN THE Backfill_Script SHALL continue processing the next Week_Window.
3. THE Backfill_Script SHALL complete iteration over all Week_Windows regardless of individual window failures.

### Requirement 8: Standalone Execution

**User Story:** As a data engineer, I want to run the script directly from the command line, so that I can execute backfills without complex setup.

#### Acceptance Criteria

1. THE Backfill_Script SHALL be executable via `python scripts/backfill_neows.py` without requiring imports from the collector module.
2. THE Backfill_Script SHALL replicate the Database_Connection pattern (create_engine + sessionmaker) directly within the script file.
3. THE Backfill_Script SHALL use SQLAlchemy for database operations and httpx for HTTP requests, both already available in the project environment.

### Requirement 9: Script Location

**User Story:** As a data engineer, I want the script placed in the scripts directory, so that it follows the project's organizational conventions.

#### Acceptance Criteria

1. THE Backfill_Script SHALL be located at the path `scripts/backfill_neows.py` within the project repository.
