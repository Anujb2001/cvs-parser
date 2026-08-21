CREATE DATABASE IF NOT EXISTS forensic_logs;

-- 1. CDR RECORDS (With 15-Day Native TTL Auto-Deletion)
CREATE TABLE IF NOT EXISTS forensic_logs.cdr_records (
    case_id String,
    caller_id String,
    receiver_id String,
    call_timestamp DateTime('Asia/Kolkata'),
    duration UInt32,
    call_type Enum8('VOICE_IN'=1, 'VOICE_OUT'=2, 'SMS_IN'=3, 'SMS_OUT'=4, 'DATA'=5, 'ROAMING'=6),
    imei String,
    imsi String,
    cell_id String,
    first_cgi String,
    last_cgi String,
    operator LowCardinality(String),
    circle LowCardinality(String),
    file_id String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(call_timestamp)
PRIMARY KEY (case_id, caller_id, imei, call_timestamp)
ORDER BY (case_id, caller_id, imei, call_timestamp)
TTL call_timestamp + INTERVAL 15 DAY DELETE;

-- 2. IPDR RECORDS (With 15-Day Native TTL Auto-Deletion)
USE forensic_logs;

CREATE TABLE IF NOT EXISTS forensic_logsipdr_records (
    case_id String,
    msisdn String,
    
    -- IPv4 & IPv6 Dual-Stack Support
    private_ip String,              -- Stores both IPv4 and IPv6 strings
    public_ip IPv4,                 -- Public IPv4 for CGNAT mapping
    public_ip_v6 Nullable(IPv6),    -- Public IPv6
    public_port UInt16,
    
    dest_ip IPv4,                   -- Target Destination IPv4 (e.g., 141.101.90.1)
    dest_ip_v6 Nullable(IPv6),      -- Target Destination IPv6
    dest_port UInt16,
    
    session_start DateTime('Asia/Kolkata'),
    session_end DateTime('Asia/Kolkata'),
    upload_bytes UInt64,
    download_bytes UInt64,
    
    imei String,
    imsi String,
    cell_id String,
    operator LowCardinality(String),
    file_id String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(session_start)
PRIMARY KEY (case_id, dest_ip, session_start)
ORDER BY (case_id, dest_ip, session_start, public_ip, msisdn)
TTL session_start + INTERVAL 15 DAY DELETE;

-- 3. GPRS / MOBILE DATA RECORDS (With 15-Day Native TTL Auto-Deletion)
CREATE TABLE IF NOT EXISTS forensic_logs.gprs_records (
    case_id String,
    msisdn String,
    
    -- IP Allocation (IPv4 & IPv6 Dual-Stack)
    ipv4 Nullable(IPv4),             -- Local IPv4 (e.g., 100.81.113.225)
    ipv6 Nullable(IPv6),             -- Local IPv6 (e.g., 2401:4900:5f13:1026::)
    translated_ip Nullable(IPv4),    -- CGNAT Public IPv4
    translated_port UInt16,          -- NAT Public Port
    destination_ip Nullable(IPv4),   -- External Target IPv4
    destination_port UInt16,         -- Target Port
    
    -- Session Metrics
    session_start DateTime('Asia/Kolkata'),
    session_end DateTime('Asia/Kolkata'),
    download_bytes UInt64,
    upload_bytes UInt64,
    total_bytes UInt64,
    
    -- Device & Network Metadata
    imei String,
    imsi String,
    cgi String,                      -- Cell Global Identifier / Cell ID
    roaming_circle LowCardinality(String),
    operator LowCardinality(String), -- Airtel, Jio, VI
    network_type LowCardinality(String), -- 2G, 3G, 4G, 5G
    file_id String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(session_start)
PRIMARY KEY (case_id, msisdn, session_start)
ORDER BY (case_id, msisdn, session_start, imei)
TTL session_start + INTERVAL 15 DAY DELETE;

-- 3. TOWER DUMP RECORDS (With 15-Day Native TTL Auto-Deletion)
CREATE TABLE IF NOT EXISTS forensic_logs.tower_dump_records (
    case_id String,
    cell_id String,
    msisdn String,
    imei String,
    imsi String,
    connection_time DateTime('Asia/Kolkata'),
    duration UInt32,
    operator LowCardinality(String),
    file_id String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(connection_time)
PRIMARY KEY (case_id, cell_id, connection_time)
ORDER BY (case_id, cell_id, connection_time, msisdn)
TTL connection_time + INTERVAL 15 DAY DELETE;