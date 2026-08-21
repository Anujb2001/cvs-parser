# CLAUDE.md - Analytic Intelligence Platform Constitution

## 1. System Overview & Architecture
An air-gapped, offline-first digital analytic platform designed for System. The full application stack—React SPA, FastAPI Backend, ClickHouse, PostGIS, and Local LLM—runs 100% containerized inside WSL 2 (Ubuntu Engine).

- **Architecture**: Modular Monolith encapsulated in Multi-Container Docker
- **Host Environment**: WSL 2 (Ubuntu) + Docker Desktop (WSL 2 Backend Engine)
- **Deployment**: `docker compose up --build` on local station servers or field laptops
- **Data Footprint & Retention**: ~10 Crore (100M) records/day with a 15-day native ClickHouse TTL

---

## 2. Containerized Tech Stack Specification

### Container 1: Frontend (`frontend` service)
- **Framework**: React 18+ (TypeScript) + Vite + Tailwind CSS
- **Container Build**: Multi-stage (`node:20-alpine` builder → `nginx:alpine` runtime)
- **Visualizations**: `Cytoscape.js` (Graph Analysis), `Leaflet.js` (Offline GIS Maps), `TanStack Table` (Virtualized Data Grids)

### Container 2: Backend API & Ingestion Engine (`backend` service)
- **Core Framework**: Python 3.11+ (FastAPI with `uvicorn`)
- **Container Build**: Lightweight Python (`python:3.11-slim`) mounted via WSL volume
- **Parsing & Streaming**: `Polars`, `DuckDB` (Micro-batch loading into ClickHouse)
- **Security & AI Orchestration**: `sqlglot` (AST Query Sanitizer) & `LangGraph` (Agent State Orchestrator)

### Container 3: OLAP Database (`clickhouse` service)
- **Image**: `clickhouse/clickhouse-server:24.3-alpine`
- **Role**: High-speed telecom log storage (CDR, IPDR, Tower Dumps) with native 15-day TTL
- **Storage**: Docker Named Volume bound to WSL 2 ext4 filesystem (`ch_data`)

### Container 4: Spatial & Relational Database (`postgres` service)
- **Image**: `postgis/postgis:16-3.4-alpine`
- **Role**: Cases, SDR subscriber lookups, cell tower spatial mapping, and audit logging
- **Storage**: Docker Named Volume bound to WSL 2 ext4 filesystem (`pg_data`)

### Container 5: Air-Gapped Local LLM (`ollama` service)
- **Image**: `ollama/ollama:latest`
- **WSL 2 Hardware Integration**: NVIDIA Container Toolkit enabled for GPU Passthrough
- **Default Models**: `qwen2.5-coder:14b` or `llama3.1:8b`

---

## 3. Mandatory Security & Performance Rules

### Rule 1: 100% Air-Gap Isolation (Absolute Constraint)
- **Zero Internet Connections**: No outbound HTTP/HTTPS requests from inside containers or frontend client runtime.
- **Bundled Static Assets**: All JS packages, CSS, Google Fonts, icons, and OpenStreetMap vector map tiles MUST be bundled locally into static assets inside container images or volumes.

### Rule 2: WSL 2 File System Performance Optimization
- **Native Linux Paths Only**: All source code, Docker volumes, and database mounts MUST reside directly on the native Linux ext4 file system (e.g., `/home/user/projects/cdr-analyzer`).
- **Forbidden Mounting**: NEVER mount projects or volumes from Windows mounts (`/mnt/c/`), which causes a severe 10x–20x I/O degradation on ClickHouse and Polars operations.

### Rule 3: Read-Only Database Safeguards for Local AI Agent
- **Credential Restriction**: The AI Agent container MUST connect using database users (`analyst_readonly`) restricted strictly to `SELECT` privileges.
- **AST Security Guardrails**: ALL LLM-generated SQL MUST pass `sqlglot` AST parsing in the backend before execution to block mutations, filesystem calls, and catalog access.

---

## 4. Directory & Repository Structure

```text
/Analytic-platform
├── docker-compose.yml        # Orchestrates WSL 2 containers, networks, and volumes
├── CLAUDE.md                 # Project Constitution & Technical Guidelines
├── SPEC.md                   # Detailed feature specifications
├── config/                   # Database and proxy initialization scripts
│   ├── clickhouse/           # config.xml, users.xml
│   ├── postgres/             # init.sql (PostGIS setup)
│   └── nginx/                # nginx.conf
├── backend/                  # FastAPI app source code
│   ├── Dockerfile
│   ├── main.py
│   ├── database.py
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   ├── agent/            # LangGraph Text-to-SQL logic
│   │   ├── parsers/          # Polars/DuckDB telecom parsers
│   │   └── security/         # sqlglot query sanitizer
│   └── tests/
└── frontend/                 # React + TypeScript SPA source code
    ├── Dockerfile
    ├── nginx.conf
    └── src/

```

---

## 5. Container Management & Local Operations

### Environment Operations

* **Build & Launch Complete Suite**:
`docker compose up -d --build`
* **View Live Backend Logs**:
`docker compose logs -f backend`
* **Stop All Containers**:
`docker compose down`

### Testing & Validation

* **Run Backend Unit & Security Tests**:
`docker compose exec backend pytest`
* **Execute ClickHouse Interactive Shell**:
`docker compose exec clickhouse clickhouse-client`
* **Pull LLM Weights into Ollama Container**:
`docker compose exec ollama ollama pull qwen2.5-coder:14b`

---

## 6. Development & Coding Standards

* **Python**: Follow PEP 8 (`black`, `ruff`). Use async drivers for ClickHouse/PostgreSQL where high concurrency is required.
* **TypeScript/React**: Enable `strict` type checking (`src/types/`), functional components, and scannable UI layout components.
* **Git Strategy**: 100% local version control on the station server drive; no external remote repo pushes allowed during air-gapped operations.