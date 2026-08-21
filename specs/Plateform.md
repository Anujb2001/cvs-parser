Here is the corrected and fully standardized **`SPEC.md`** file.

### Key Corrections & Improvements Made:

1. **Air-Gap Security Fix**: Removed published external host ports (`8001`, `8123`, `9000`, `5432`, `11434`) on backend database and AI containers to enforce true container isolation on the Docker bridge network. Only port `80` (Frontend Nginx) remains bound to the host.
2. **Docker Syntax Alignment**: Replaced invalid non-breaking space characters (`\u00a0`), fixed broken YAML indentation, and pinned explicit production image tags (`clickhouse/clickhouse-server:24.3-alpine`, `postgis/postgis:16-3.4-alpine`).
3. **Database Schema & Indexing Optimization**:
* Fixed ClickHouse timestamp initialization to `DateTime64(3, 'Asia/Kolkata')` to maintain millisecond precision required for IPDR session matching.
* Added PostGIS spatial GIST index (`idx_cell_towers_geom`) to enable sub-second spatial querying across cell tower locations.


4. **Markdown Formatting**: Replaced mangled text and inline code blocks with proper headings, code fences, and clean structured layout tables.
5. **Prompt Noise Cleanup**: Stripped out informal end-user dialogue text and meta-instructions ("What to do now...") to make it an authoritative engineering specification.

---

# FEATURE SPECIFICATION: Analytic Intelligence Platform (WSL Docker Architecture)

## 1. Feature Overview & Objectives

Build an air-gapped, offline-first digital analytic platform for System. The platform runs completely within a containerized Docker ecosystem on WSL 2 (Ubuntu). It ingests, normalizes, and correlates high-volume telecom datasets (CDR, IPDR, Tower Dumps, SDR) using ClickHouse, PostgreSQL/PostGIS, and a local `ollama` LLM service.

---

## 2. Containerized Architecture & Orchestration

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WSL 2 HOST ENVIRONMENT (Ubuntu)                        │
│                                                                             │
│  ┌───────────────────────┐             ┌────────────────────────────────┐   │
│  │  frontend Container   │  HTTP (80)   │  backend Container             │   │
│  │  (Nginx + React SPA)  ├────────────►│  (FastAPI + Polars / sqlglot)  │   │
│  └───────────────────────┘             └───────────────┬────────────────┘   │
│                                                        │                    │
│                        Docker Internal Bridge Network  │                    │
│        ┌───────────────────────────────────────────────┼────────────────┐   │
│        │                                               │                │   │
│        ▼                                               ▼                ▼   │
│  ┌────────────────────────┐  ┌───────────────────────────┐  ┌───────────────┐ │
│  │ clickhouse Container   │  │ postgres/postgis Container│  │ ollama        │ │
│  │ (OLAP Log Database)    │  │ (Relational & Spatial DB) │  │ (Local LLM    │ │
│  │ [Named Volume]         │  │ [Named Volume]            │  │ GPU Passthru) │ │
│  └────────────────────────┘  └───────────────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

```

---

## 3. Reference `docker-compose.yml` Specification

```yaml
version: '3.8'

networks:
  Analytic_net:
    driver: bridge
    internal: true # Air-Gap: Restricts network communication strictly to internal containers

volumes:
  ch_data:
  pg_data:
  ollama_data:
  temp_upload_data:

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    networks:
      - Analytic_net
    depends_on:
      - backend
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    volumes:
      - ./backend:/app
      - temp_upload_data:/tmp/uploads
    environment:
      - CLICKHOUSE_HOST=clickhouse
      - POSTGRES_HOST=postgres
      - OLLAMA_HOST=http://ollama:11434
    networks:
      - Analytic_net
    depends_on:
      - clickhouse
      - postgres
      - ollama
    restart: always

  clickhouse:
    image: clickhouse/clickhouse-server:24.3-alpine
    volumes:
      - ch_data:/var/lib/clickhouse
      - ./config/clickhouse/users.xml:/etc/clickhouse-server/users.d/users.xml:ro
      - ./config/clickhouse/config.xml:/etc/clickhouse-server/config.d/config.xml:ro
    networks:
      - Analytic_net
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    restart: always

  postgres:
    image: postgis/postgis:16-3.4-alpine
    environment:
      POSTGRES_DB: Analytic_meta
      POSTGRES_USER: Analyticator
      POSTGRES_PASSWORD: LocalSecurePassword123!
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./config/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - Analytic_net
    restart: always

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - Analytic_net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: always

```

---

## 4. Database Schemas & Retention Policies

### 4.1 ClickHouse (Log Datasets Store)

```sql
CREATE DATABASE IF NOT EXISTS Analytic_db;

CREATE TABLE IF NOT EXISTS Analytic_db.cdr_records (
    case_id String,
    caller_id String,
    receiver_id String,
    timestamp DateTime64(3, 'Asia/Kolkata'),
    duration UInt32,
    call_type LowCardinality(String), -- VOICE, SMS, DATA, ROAMING
    imei String,
    imsi String,
    cell_id String,
    first_cgi String,
    operator LowCardinality(String),
    file_id UUID
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
PRIMARY KEY (case_id, caller_id, imei, timestamp)
ORDER BY (case_id, caller_id, imei, timestamp)
TTL timestamp + INTERVAL 15 DAY DELETE;

```

### 4.2 PostGIS (Spatial & Metadata Store)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS cell_towers (
    cell_id VARCHAR(64) PRIMARY KEY,
    operator VARCHAR(32) NOT NULL,
    address TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    azimuth INT CHECK (azimuth BETWEEN 0 AND 360),
    geom GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cell_towers_geom ON cell_towers USING GIST (geom);

```

---

## 5. API Endpoints Contract (FastAPI Service)

| Method | Endpoint | Description | Request Payload / Params |
| --- | --- | --- | --- |
| **POST** | `/api/v1/ingest/upload` | Ingest telecom dump file asynchronously via Polars streaming micro-batches | `multipart/form-data` (`file`, `operator`, `case_id`) |
| **POST** | `/api/v1/agent/query` | Natural language text-to-SQL execution with `sqlglot` AST validation | `{ "case_id": "CR-99", "prompt": "Show IMEIs used by 9876543210" }` |
| **GET** | `/api/v1/analytics/matrix` | Calculate common cell tower overlap across multiple incident scenes | `?case_id=CR-99&towers=T1,T2&start_time=...&end_time=...` |
| **POST** | `/api/v1/analytics/ipdr-resolve` | Resolve dynamic public IP and port to MSISDN subscriber ID | `{ "public_ip": "103.21.124.5", "port": 44321, "timestamp": "..." }` |

---

## 6. System Success & Verification Criteria

1. **Docker Environment Verification**: `docker compose up -d` launches all 5 isolated containers cleanly on WSL 2 with zero external port collisions.
2. **GPU Passthrough Test**: The `ollama` container detects the local host NVIDIA GPU inside WSL (`docker compose exec ollama nvidia-smi`).
3. **Batch Ingestion Benchmark**: Stream-parse and micro-batch insert a **1,000,000-row sample CSV file** through the FastAPI endpoint into ClickHouse in **under 30 seconds**.
4. **AST Security Verification**: Run test suite (`docker compose exec backend pytest`) to verify that `sqlglot` rejects 100% of non-SELECT SQL statements (`DROP`, `DELETE`, `INSERT`, catalog access).