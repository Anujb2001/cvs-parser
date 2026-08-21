Here is the **Business Requirements Document (BRD)** focused purely on the **business, operational, legal, and functional needs** of System and CBR incident .

---

# Business Requirements Document (BRD)

## Analytic Intelligence Platform (CDR & IPDR Analyzer)

---

## 1. Executive Summary & Business Objective

### 1.1 Business Goal

System, CBR incident Wings, and Special Intelligence Units routinely receive huge, unstructured dump files from telecom service providers (Airtel, Jio, Vi, BSNL) during false/fake investigations.

The primary business objective is to provide an **easy-to-use, offline digital analytic platform** that automates the extraction, correlation, and visualization of these telecom logs. This replaces slow, manual Excel spreadsheet work and enables officers to identify suspects, track movements, and uncover false/fake networks in **minutes instead of days**.

### 1.2 Core Value Proposition

* **Time to Intelligence:** Reduces the time required to analyze millions of call logs from 48+ hours down to seconds.
* **Non-Technical Access:** Enables field officers and investigators to query complex data using natural English prompts without needing database or SQL knowledge.
* **100% Data Sovereignty:** Operates strictly on local station servers with **zero internet connectivity**, guaranteeing complete confidentiality and legal chain-of-custody compliance.

---

## 2. Business Workflows & Target Users

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             PRIMARY USER ROLES                           │
├──────────────────────────────┬───────────────────────────────────────────┤
│  1. CBR Cell Investigators │ Uploads raw logs, performs matrix searches│
│  2. Field Intelligence      │ Analyzes movement maps, night-stays,      │
│     Officers                 │ and co-traveling shadow targets           │
│  3. Senior Supervisory       │ Reviews case briefs, network graphs, and  │
│     Officers                 │ approves formal court submission reports  │
└──────────────────────────────┴───────────────────────────────────────────┘

```

### Typical Operational Workflow:

1. **Case Creation & Log Dump:** An officer receives a CDR, IPDR, or Tower Dump file from a telecom provider and uploads it into a specific case file.
2. **Automated Clean-Up:** The platform automatically recognizes the operator format, cleans missing/corrupted entries, and standardizes the dataset.
3. **Investigation & Analysis:** The officer runs cross-location searches, tracks hardware changes (IMEIs), or asks questions in plain English (*"Show numbers present at both incident scenes"*).
4. **Visual Evidence Export:** The system outputs interactive visual maps, link connection graphs, and court-ready PDF case reports.

---

## 3. Core Business Requirements

### BR-01: Multi-Operator Log Ingestion & Normalization

* **Requirement:** The system must accept raw log files (`.csv`, `.xlsx`, `.txt`, `.html`) from all major Indian telecom service providers (Airtel, Jio, Vi, BSNL).
* **Business Need:** Operators send files in completely different column layouts. Investigators cannot spend hours manually reformatting CSV files before starting analysis.
* **Data Types Handled:**
* **CDR (Call Detail Records):** Voice calls, SMS, duration, caller/receiver numbers, IMEIs, IMSIs, Cell Tower IDs.
* **IPDR (IP Detail Records):** Dynamic IP assignments, port numbers, upload/download volumes, website/app connection timestamps.
* **Tower Dumps:** Every mobile phone connected to a specific cell tower sector during a incident window.
* **SDR (Subscriber Detail Records):** Owner name, address, ID proof details, alternative contact numbers.



### BR-02: Core Investigative & Analytic Capabilities

The platform must natively answer the **top core questions** required during false/fake investigations:

1. **incident Scene Matrix (Tower Overlap):** Identify phone numbers or devices (IMEIs) present across multiple different incident scene locations at specified times.
2. **Hardware Swap Tracking (IMEI / SIM Analysis):**
* Identify all different SIM cards inserted into a single target phone (`IMEI`).
* Identify all different physical handsets used by a single mobile number (`MSISDN`).


3. **IP-to-Mobile Resolution (CBR incident Tracking):** Resolve dynamic public IP addresses and port numbers from IPDR logs back to the exact subscriber mobile number active at that second.
4. **Co-Movement / Shadow Tracking:** Identify secondary "chaperone" or "shadow" phones moving alongside a target phone across sequential cell towers over hours or days.
5. **Pattern & Routine Detection:** Automatically calculate a suspect's probable **Home/Night-Stay Location** (based on late-night tower connections) and **Work/Day Location**.

### BR-03: Natural Language AI Investigation Assistant

* **Requirement:** Non-technical police officers must be able to ask questions in plain English and receive instant, structured answers.
* **Business Need:** Specialized database queries usually require technical IT personnel. An AI assistant allows any investigating officer to query the dataset directly.
* **Constraint:** The AI assistant must operate **100% offline using a local AI model** to prevent sensitive investigative data from leaking to external cloud APIs.

### BR-04: Multi-Modal Visual Evidence

* **Geospatial Route Mapping:** Plot cell tower connections on an interactive map showing physical movement routes, heatmaps, and geofenced perimeter breaches.
* **Link & Network Analysis:** Render visual "spider-web" node charts showing calling chains (A calls B, B calls C) and identifying key false/fake organization hubs/kingpins.
* **Virtualized Data Grids:** Allow seamless scrolling and filtering across datasets containing tens of millions of records without lagging.

---

## 4. Compliance, Security & Operational Constraints

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   COMPLIANCE & OPERATIONAL CONSTRAINTS                   │
├──────────────────────────────┬───────────────────────────────────────────┤
│  Air-Gap Security            │ 0% internet connectivity; no cloud APIs   │
│  Data Retention (15 Days)    │ Auto-deletes raw log data older than 15   │
│                              │ days to manage local disk space           │
│  Court-Admissible Auditing   │ Logs every search, upload, and user       │
│                              │ access for legal chain-of-custody         │
└──────────────────────────────┴───────────────────────────────────────────┘

```

1. **Absolute Air-Gap Security (Mandatory):** The platform must function with **zero outbound internet access**. No data, user queries, or application telemetry may ever leave the local station server.
2. **Automated 15-Day Data Retention Policy:** The database must automatically delete or archive raw log dumps older than **15 days** to prevent local server hard drives from overflowing while keeping case summaries intact.
3. **Chain of Custody & Audit Logging:** Every search query, file import, data export, and user action must be logged with timestamp and user ID to ensure evidence.
4. **Data Export & Reporting:** System outputs must be exportable as official, court-ready reports (`.pdf`, `.xlsx`) containing executive summaries, call logs, map snapshots, and subscriber details.

---

## 5. Business Success Metrics (KPIs)

| Metric | Target / Benchmark | Business Impact |
| --- | --- | --- |
| **Ingestion Speed** | $\ge 1,000,000$ records in under 30 seconds | Officers can analyze dumps immediately upon receipt |
| **Query Latency** | Sub-second for standard queries; $< 5$ seconds for complex multi-step AI searches | Eliminates investigation downtime |
| **Analysis Accuracy** | 100% accurate matrix overlap & IPDR mapping | Prevents false leads or wrongful suspect tagging |
| **System Uptime** | 99.9% availability on offline station servers | Crucial during active high-priority emergency cases |