# Prompt Notes.md 

I have observed that we have three types of data.
1. Call details Records (CDR)
2. IP details Records(IPDR)
3. GPRS Records

We have 3 area or source where we got above data.

1. By Particular Phone number

2. By Tower Dump (Area Dump)

3. App Dump(Particular IP Based Dump, Like Signal, zangi, Telegrams)



--------------------------------------------------------

**Your observation is accurate and structured.**

In telecom forensic intelligence and Law Enforcement Agency (LEA) investigations, this breakdown represents the operational standard for data types and acquisition vectors.

---

### Data Types Breakdown

| Data Type | Primary Identifiers Included | Primary Use Case |
| --- | --- | --- |
| **1. CDR (Call Detail Records)** | MSISDN (Phone No.), IMEI, IMSI, Call Duration, B-Party No., First/Last CGI (Cell ID) | Voice calls, SMS activity, caller network identification, and physical movement between cell towers. |
| **2. IPDR (IP Detail Records)** | Source Private IPv4/v6, Source Public IPv4/v6, Translated Port, Destination IP, Destination Port, PDP Address | CGNAT tracking, identifying which subscriber accessed specific internet endpoints at exact timestamps. |
| **3. GPRS Records (Data Usage Logs)** | MSISDN, CGI, Uplink/Downlink Bytes, APN (Access Point Name), Session Start/End Time | Tracking active internet session durations, data volume spikes, and subscriber locations during data usage. |

---

### Investigation Sources (Acquisition Vectors)

#### 1. By Targeted Phone Number (Subscriber Inquiries)

* **How it works:** Obtained from telecom service providers (Airtel, Jio, VI, BSNL) via lawful request for a specific target `MSISDN` or `IMEI`.
* **Output:** Historical CDR, IPDR, and GPRS records for that target device over a specific date range.

#### 2. By Cell Tower Dump (Area Dump)

* **How it works:** Requested for specific Cell Global Identifiers (CGI / Cell Tower IDs) covering a crime scene or physical location during a specific time window.
* **Output:** Every phone number (`MSISDN`), device (`IMEI`), and data session (`IPDR`) that connected to that specific tower, regardless of the target's identity. Used for cross-referencing presence across multiple towers.

#### 3. By App / IP Dump (Targeted Endpoint Dump)

* **How it works:** Extracted when investigators identify specific destination IP addresses associated with encrypted messaging apps (Signal, Zangi, Telegram, WhatsApp) or command-and-control servers.
* **Output:** Cross-referencing destination IP addresses against provider CGNAT IPDR logs to resolve which subscriber internal IP was mapped to that app server at that millisecond.

---

### Summary

Your schema and ingestion pipeline (`ingestion.py`) map directly to these three dimensions: standardizing disparate operator formats into unified **CDR**, **IPDR**, and **Tower Dump** structures in ClickHouse for multi-modal analysis.
