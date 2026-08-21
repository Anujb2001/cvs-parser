This document provides the complete **System Requirement Specification (SRS)** for the **Analytic Intelligence Platform** (the *i9 CDR & IPDR Analyzer Clone*).

This platform serves as a complete blueprint for an **air-gapped, offline digital analytic platform** tailored for System, CBR incident Wings, and Special Intelligence Branches.

---

## 1. Core Purpose & Operational Objectives

The primary purpose of this application is to automate and accelerate telecom data analytic for false/fake investigations. Investigators regularly receive huge, unstructured dump files from telecom service providers (Airtel, Jio, Vi, BSNL) containing millions of raw communication logs.

This system must:

1. **Ingest & Normalize** raw telecom dumps rapidly without freezing the application.
2. **Execute Deep Analytical Queries** (matrix analysis, link analysis, IMEI tracking, IP-to-Mobile mapping) across hundreds of millions of records.
3. **Provide an Air-Gapped AI Agent** that translates non-technical natural language queries from investigators into safe multi-step database execution plans.
4. **Operate 100% Offline** inside containerized hardware on local police station servers or field laptops, guaranteeing strict data sovereignty and chain-of-custody compliance.

---

## 2. Functional Requirements Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM FUNCTIONAL MODULES                              │
├───────────────────┬───────────────────┬───────────────────┬─────────────────────┤
│  1. Ingestion     │  2. analytic     │  3. Local AI      │  4. Visualization   │
│     & Parser      │     Analytics     │     Agent         │     & Reporting     │
│  - Multi-operator │  - Matrix (Overlap)│  - Text-to-SQL    │  - Virtual DataGrid │
│  - Auto Column Map│  - Link Analysis  │  - Multi-step Plan│  - Cytoscape Node   │
│  - Micro-batching │  - IMEI Swaps     │  - sqlglot AST    │  - Leaflet GIS Maps │
│  - 15-Day TTL     │  - IPDR Mapping   │    Sanitizer      │  - PDF/Excel Export │
└───────────────────┴───────────────────┴───────────────────┴─────────────────────┘

```

### Module 1: Dynamic Data Ingestion & Normalization Engine

* **Multi-Format Support:** Ingest `.csv`, `.xlsx`, `.txt`, and `.html` files dynamically.
* **Header Auto-Mapping:** Automatically map varying telecom operator column headers to unified internal database schemas:
* *Voice/SMS CDR:* `caller_id` (A-Party), `receiver_id` (B-Party), `timestamp`, `duration`, `call_type`, `imei`, `imsi`, `cell_id`, `first_cgi`.
* *IPDR:* `msisdn`, `private_ip`, `private_port`, `public_ip`, `public_port`, `dest_ip`, `dest_port`, `start_time`, `end_time`, `upload_bytes`, `download_bytes`.
* *SDR (Subscriber Data):* `phone_number`, `subscriber_name`, `address`, `id_proof_number`, `activation_date`.
* *Tower Dumps:* `cell_id`, `operator`, `latitude`, `longitude`, `azimuth`.


* **High-Throughput Streaming:** Use **Polars** / **DuckDB** to process and micro-batch stream data into ClickHouse at $\ge 10,000$ records/sec without loading full files into system RAM.

### Module 2: Core Analytical & Intelligence Engine

The system must run high-speed ClickHouse / PostGIS queries to solve key investigative problems:

1. **Matrix / Overlap Analysis:** Find common phone numbers or IMEIs connected across 2 or more distinct cell towers during specified incident timeframes.
2. **IMEI / SIM Swap Tracking:**
* List all SIM cards (MSISDNs) used inside a single hardware device (`IMEI`) over time.
* List all devices (`IMEI`) used by a single mobile number.


3. **IPDR Session Resolution:** Map dynamic public IP addresses and port numbers back to specific subscriber mobile numbers (`MSISDN`) at precise timestamps.
4. **Behavioral & Location Profiling:**
* *Night Stay Location:* Detect frequent late-night cell tower connections (11 PM – 6 AM).
* *Co-Movement / Shadow Tracking:* Detect pairs of numbers traveling together across sequential cell towers.
* *Silent / New Activation:* Flag numbers or SIMs that suddenly activated at a incident scene.



### Module 3: Air-Gapped Natural Language Query Agent

* **Local LLM Execution:** Run a local open-source LLM (`Qwen2.5-Coder-14B` or `Llama-3.1-8B`) via **Ollama / vLLM**.
* **Plan-and-Solve Framework:** Use **LangGraph** to break complex officer prompts (*"Find common numbers in Tower A and B, then check if they used a VPN in IPDR and look up their SDR names"*) into sequential database execution plans.
* **AST Security Guardrails:** Validate all generated SQL using **`sqlglot`** before execution:
* Reject non-`SELECT` statements (`DROP`, `DELETE`, `INSERT`, `ALTER`).
* Block unauthorized filesystem access or system tables (`file()`, `url()`, `system.users`).
* Enforce read-only database user credentials.



### Module 4: Multi-Modal Visualization & Reporting

* **Interactive GIS Map (`Leaflet.js`):** Render cell tower locations, geofences, movement heatmaps, and suspect trails using locally cached offline map tiles.
* **Link Analysis Graph (`Cytoscape.js`):** Render caller-callee communication networks, multi-hop chains, and mediator contacts visually.
* **Virtualized Data Grid (`TanStack Table`):** Display up to 100,000+ filtered records smoothly without DOM performance degradation.
* **Court-Ready PDF/Excel Exports:** Generate formal case investigation summaries for legal evidence filing.

---

## 3. Non-Functional Requirements (NFRs)

| NFR Domain | Requirement Specification |
| --- | --- |
| **Air-Gap Security** | Zero external HTTP/HTTPS connections. All libraries, fonts, icons, and map tiles must be bundled inside local Docker containers. |
| **Data Retention** | Automated native ClickHouse TTL rule to drop raw log data older than 15 days (`TTL timestamp + INTERVAL 15 DAY`). |
| **Performance SLA** | Sub-second response times for standard single-tower searches; under 5 seconds for multi-step agent SQL queries across 10 Crore records. |
| **Hardware Target** | Local Workstation / Station Server (Intel i9 / Ryzen 9, 64 GB RAM, 2 TB NVMe SSD, NVIDIA RTX 4080/4090 16GB+ VRAM). |
| **Deployment Mode** | Multi-container environment running on **WSL 2 (Ubuntu) via Docker Compose**. |

---

## 4. Containerization & Deployment Requirement

The system must run seamlessly as a containerized stack inside WSL 2:

```
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

1. **`frontend` Container**: Multi-stage build (Node.js build $\rightarrow$ Nginx Alpine runtime) serving the React application and caching static map tiles.
2. **`backend` Container**: Python 3.11 Slim image hosting FastAPI, Polars ingestion pipelines, `sqlglot` security validators, and LangGraph agent logic.
3. **`clickhouse` Container**: Official ClickHouse OLAP database handling 10Cr daily records with 15-day native TTL partitions.
4. **`postgres` Container**: PostgreSQL 16 + PostGIS for spatial cell tower mapping, SDR lookup tables, and case metadata.
5. **`ollama` Container**: Official Ollama image integrated with WSL 2 NVIDIA Container Toolkit for direct host GPU passthrough.

---

## 5. Summary Matrix for Developers

* **Source of Truth Documents**: Use `CLAUDE.md` as the project constitution and `SPEC.md` for feature specifications.
* **Development Strategy**: Follow Spec-Driven Development (SDD)—define specifications and execution plans first, then implement code task by task locally.
* **Git Repository Requirement**: No remote repository hosting (GitHub/GitLab) is required; version control remains 100% local on the station server disk.