-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. USERS & RBAC TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    badge_number VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'INVESTIGATOR', 'ANALYST')),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. CASE MANAGEMENT TABLE
CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    investigating_officer_id UUID REFERENCES users(user_id),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED', 'ARCHIVED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. SUBSCRIBER DETAIL RECORDS (SDR)
CREATE TABLE IF NOT EXISTS sdr_subscribers (
    phone_number VARCHAR(15) PRIMARY KEY,
    subscriber_name VARCHAR(255) NOT NULL,
    guardian_name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    id_proof_type VARCHAR(50),
    id_proof_number VARCHAR(100),
    alternate_number VARCHAR(15),
    activation_date DATE,
    operator VARCHAR(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sdr_name ON sdr_subscribers(subscriber_name);
CREATE INDEX IF NOT EXISTS idx_sdr_id_proof ON sdr_subscribers(id_proof_number);

-- 4. CELL TOWER MASTER DIRECTORY (GIS ENABLED)
CREATE TABLE IF NOT EXISTS cell_towers (
    cell_id VARCHAR(64) PRIMARY KEY,
    operator VARCHAR(32) NOT NULL,
    circle VARCHAR(32),
    site_address TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    azimuth INT CHECK (azimuth BETWEEN 0 AND 360),
    geom GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_cell_towers_geom ON cell_towers USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_cell_towers_operator ON cell_towers(operator);

-- 5. AUDIT LOGS FOR COURT COMPLIANCE
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    query_text TEXT,
    ip_address VARCHAR(45) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status_flag VARCHAR(20) DEFAULT 'SUCCESS'
);