from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd
import polars as pl
import io
import ipaddress
from datetime import datetime
from app.core.database import get_clickhouse_client

router = APIRouter()

# -------------------------------------------------------------------------
# Comprehensive Field Aliases for VIL, Bharti Airtel, Jio, and standard CDRs
# -------------------------------------------------------------------------
HEADER_MAPPINGS = {
    "msisdn": [
        "msisdn", "target /a party number", "calling party telephone number", 
        "msisdn_userid", "dsl_user_id", "landline/msisdn/mdn/leased circuit id for internet access",
        "mobile no.", "contact no.", "a_party", "calling_number", "mobile no", "target_number",
        "msisdn_user_id", "landline/msisdn/mdn/leased circuit id", "target no", 
        "calling number", "a number", "calling party number", "a_number", "served_msisdn"
    ],
    "caller_id": [
        "target /a party number", "calling party telephone number", "msisdn", 
        "mobile no.", "contact no.", "a_party", "calling_number", "mobile no", "target no",
        "calling number", "a number", "calling party number", "a_number", "served_msisdn"
    ],
    "receiver_id": [
        "b party number", "called party telephone number", "b_party", "called_number", 
        "called party", "b party", "b party no", "called number", "b number", 
        "called party number", "b_number", "destination number", "other_party"
    ],
    "call_date": [
        "call date", "date of destination ip transaction (dd/mm/yyyy)", 
        "start date of public ip address allocation (dd/mm/yyyy)", "date",
        "start date", "call_date"
    ],
    "call_time": [
        "call initiation time", "call time", "ist time of destination ip transaction (hh:mm:ss)",
        "ist start time of public ip address allocation (hh:mm:ss)", "time",
        "start time", "call_time"
    ],
    "call_timestamp": [
        "session_start_time", "event_start_time", "session start date & time", 
        "time1 (dd/mm/yyyy hh:mm:ss)", "datetime", "timestamp", "session start time",
        "start_date_time", "call start time", "date_time", "date & time", "answer_time"
    ],
    "session_end": [
        "session_end_time", "session end date & time", "session end time", "call termination time",
        "end time", "end date & time", "release_time"
    ],
    "duration": [
        "call duration", "duration in sec", "session duration (seconds)", 
        "duration(seconds)", "dur", "duration", "dur(s)", "duration_sec", "call_duration"
    ],
    "call_type": [
        "call_type", "type", "call type", "service type", "call direction", "direction"
    ],
    "imei": [
        "imei", "imei_no", "source mac-id address/other device identification number", 
        "mac_address", "mac id", "peir_imei"
    ],
    "imsi": [
        "imsi", "imsi_no", "served_imsi"
    ],
    "cell_id": [
        "first cell id", "first cell global id", "cgi-ld", "cgi", 
        "first cell id-name/location", "cellid", "first cgi", "cell_id", "first_cell", "site_id"
    ],
    "private_ip": [
        "source ip", "source_private_ipv4", "source private ip address", 
        "pdp address ipv4", "source ip address", "ip address", "private_ip"
    ],
    "public_ip": [
        "translated ip", "source_public_ipv4", "source public ip address", 
        "translated ip address", "public_ip"
    ],
    "public_ip_v6": [
        "source_public_ipv6", "pdp address ipv6"
    ],
    "public_port": [
        "translated port", "source_public_port", "source port", "source_handset_port"
    ],
    "dest_ip": [
        "destination ip", "destination_ip4", "destination_ipv4", 
        "destination ip address", "server_ip"
    ],
    "dest_ip_v6": [
        "destination_ipv6", "destination_ip6"
    ],
    "dest_port": [
        "destination port", "destination_port", "server_port"
    ],
    "upload_bytes": [
        "uplink_vol", "data volume uplink", "data volume up link", "uplink vol", "upload_data"
    ],
    "download_bytes": [
        "downlink_vol", "data volume downlink", "data volume down link", "downlink vol", "download_data"
    ],
    "operator": [
        "operator", "roaming circle name", "roaming network/circle", 
        "home circle", "roaming circle", "roam nw", "circle", "network"
    ]
}

HEADER_SIGNATURES = [
    "calling party telephone number", "called party telephone number", "target /a party number", 
    "b party number", "msisdn_userid", "dsl_user_id", "landline/msisdn/mdn/leased circuit id",
    "first cell id-name/location", "first cell global id", "first cell id", "last cell id",
    "source_public_ipv4", "source_private_ipv4", "translated ip", "destination ip",
    "session start date & time", "event_start_time", "session_start_time", "call initiation time",
    "call duration", "duration in sec", "session duration (seconds)",
    "data volume uplink", "downlink_vol", "downlink vol", "sr.no.", "mobile no.", "target no", 
    "b party no", "calling number", "called number", "a_number", "b_number", "calling party number", 
    "called party number", "call start time", "date_time"
]

DISCLAIMER_KEYWORDS = [
    "this is system generated", "call_forward", "lrn :-", "disclaimer :", 
    "signature is not required", "note :-", "auditid:", "end of report", 
    "system generated report", "generated by", "confidential", "total records :"
]


def clean_dataframe_footers(df: pd.DataFrame) -> pd.DataFrame:
    """Strips out footer notes, empty lines, and disclaimers from parsed DataFrame."""
    valid_rows = []
    for _, row in df.iterrows():
        # Stop processing if a disclaimer keyword is hit
        row_str = " ".join([str(val) for val in row.values if pd.notna(val)]).lower()
        if any(keyword in row_str for keyword in DISCLAIMER_KEYWORDS):
            break
        valid_rows.append(row)
        
    cleaned_df = pd.DataFrame(valid_rows)
    # Drop rows where more than 80% of the data is missing (common with parsed footers)
    if len(cleaned_df) > 0:
        cleaned_df = cleaned_df.dropna(thresh=len(cleaned_df.columns) * 0.2)
    return cleaned_df


def parse_excel_file(contents: bytes) -> pd.DataFrame:
    """Intelligently detects active sheet and true header row inside Excel files."""
    xls = pd.ExcelFile(io.BytesIO(contents))
    target_sheet = xls.sheet_names[0]
    
    for sheet in xls.sheet_names:
        df_tmp = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=40)
        if len(df_tmp.dropna(how='all')) > 0:
            target_sheet = sheet
            break

    df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=40)
    best_idx, max_score = 0, -1

    for idx, row in df_raw.iterrows():
        row_vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
        if len(row_vals) < 2:
            continue
            
        row_str = " ".join(row_vals).lower()
        if row_str.startswith(("input value", "gprs of cell id", "dynamic ipdr", "dsl ipdr", "---", "target /a party")):
            continue

        score = sum(1 for sig in HEADER_SIGNATURES if sig in row_str)
        for token in row_vals:
            if token.lower() in [k for k_list in HEADER_MAPPINGS.values() for k in k_list]:
                score += 1
                
        if score > max_score:
            max_score = score
            best_idx = idx

    df = pd.read_excel(xls, sheet_name=target_sheet, skiprows=best_idx)
    return clean_dataframe_footers(df)


def parse_csv_file(contents: bytes) -> pd.DataFrame:
    """Detects encoding, auto-delimiter (\\t vs , vs |), and skips metadata headers/footers."""
    try:
        text = contents.decode('utf-8', errors='replace')
    except Exception:
        text = contents.decode('latin-1', errors='replace')

    lines = text.splitlines()
    
    # Pre-filter lines that are purely decorative dashes or completely blank
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith("---"):
            continue
        cleaned_lines.append(line)
        
    best_idx, best_delim, max_score = 0, ",", -1

    for idx, line in enumerate(cleaned_lines[:50]):
        line_clean = line.strip()
        if not line_clean:
            continue
            
        line_lower = line_clean.lower()
        if line_lower.startswith(("input value", "gprs of cell id", "dynamic ipdr", "dsl ipdr")):
            continue

        delims = [',', '\t', ';', '|']
        counts = {d: line_clean.count(d) for d in delims}
        chosen_delim = max(counts, key=counts.get)
        
        # Only evaluate lines that actually contain a valid delimiter
        if counts[chosen_delim] < 1:
            continue

        score = sum(1 for sig in HEADER_SIGNATURES if sig in line_lower)
        tokens = [t.strip().strip("'\"").lower() for t in line_lower.split(chosen_delim)]
        
        # Check against mapped dictionary variations to dynamically catch new formats
        mapping_variations = [k for k_list in HEADER_MAPPINGS.values() for k in k_list]
        for token in tokens:
            if token in mapping_variations:
                score += 1

        if score > max_score:
            max_score = score
            best_idx = idx
            best_delim = chosen_delim

    # Parse specifically from the cleaned textual stream
    df = pd.read_csv(
        io.StringIO("\n".join(cleaned_lines)),
        skiprows=best_idx,
        sep=best_delim,
        on_bad_lines='skip',
        dtype=str
    )
    return clean_dataframe_footers(df)


def sanitize_ipv4(ip_str: str) -> str:
    """Ensures IP address string is a valid IPv4 address, defaulting to 0.0.0.0 otherwise."""
    if not ip_str or pd.isna(ip_str):
        return "0.0.0.0"
    ip_clean = str(ip_str).strip()
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if ip_obj.version == 4:
            return ip_clean
    except ValueError:
        pass
    return "0.0.0.0"


def map_call_type_enum(val) -> int:
    """Maps call type strings to ClickHouse Enum8 numbers."""
    if pd.isna(val) or not str(val).strip():
        return 1
    val_upper = str(val).upper().strip()
    
    # 1: Incoming Voice, 2: Outgoing Voice, 3: Incoming SMS, 4: Outgoing SMS, 5: Data, 6: Roaming
    if any(k in val_upper for k in ["SMS_IN", "SMSIN", "INCOMING SMS", "SMT"]):
        return 3
    elif any(k in val_upper for k in ["SMS_OUT", "SMSOUT", "OUTGOING SMS", "SMO"]):
        return 4
    elif any(k in val_upper for k in ["IN", "VOICE_IN", "INCOMING", "MTC"]):
        return 1
    elif any(k in val_upper for k in ["OUT", "VOICE_OUT", "OUTGOING", "MOC"]):
        return 2
    elif any(k in val_upper for k in ["DATA", "GPRS", "INTERNET", "IP"]):
        return 5
    elif "ROAM" in val_upper:
        return 6
    return 1


@router.post("/upload")
async def upload_telecom_dump(
    case_id: str = Form(...),
    file_type: str = Form(...),  # Expected: 'CDR', 'IPDR', 'TOWER_DUMP', 'IP_DUMP'
    operator: str = Form("UNKNOWN"),
    file: UploadFile = File(...)
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_name = file.filename.lower()

    # 1. Parse raw dataset based on file extension
    try:
        if file_name.endswith(('.xlsx', '.xls')):
            df = parse_excel_file(contents)
        elif file_name.endswith(('.csv', '.txt', '.tsv')):
            df = parse_csv_file(contents)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    if df.empty or len(df.dropna(how='all')) == 0:
        raise HTTPException(status_code=400, detail="No valid data rows found in file.")

    pl_df = pl.from_pandas(df)

    # 2. Clean values (Strip whitespace & trailing/leading quotes)
    clean_exprs = []
    for col in pl_df.columns:
        clean_exprs.append(
            pl.col(col).cast(pl.Utf8).str.replace_all(r"^['\s]+|['\s]+$", "").alias(col)
        )
    pl_df = pl_df.with_columns(clean_exprs)

    # 3. Standardize and Map Columns
    col_rename_map = {}
    lower_cols = {str(c).lower().strip(): str(c) for c in pl_df.columns}

    for std_col, variations in HEADER_MAPPINGS.items():
        for var in variations:
            if var in lower_cols:
                col_rename_map[lower_cols[var]] = std_col
                break

    pl_df = pl_df.rename(col_rename_map)

    # Combine separate Date and Time columns into `call_timestamp` / `session_start`
    if "call_timestamp" not in pl_df.columns:
        if "call_date" in pl_df.columns and "call_time" in pl_df.columns:
            pl_df = pl_df.with_columns(
                (pl.col("call_date").fill_null("") + " " + pl.col("call_time").fill_null("")).alias("call_timestamp")
            )
        elif "call_date" in pl_df.columns:
            pl_df = pl_df.with_columns(pl.col("call_date").alias("call_timestamp"))

    # Append Metadata
    pl_df = pl_df.with_columns([
        pl.lit(case_id).alias("case_id"),
        pl.lit(file.filename).alias("file_id"),
        pl.lit(operator).alias("operator")
    ])

    # 4. Target Table Selection and Schema Normalization
    ft_upper = file_type.upper().strip()

    if ft_upper == "CDR":
        target_table = "forensic_logs.cdr_records"
        if "caller_id" not in pl_df.columns and "msisdn" in pl_df.columns:
            pl_df = pl_df.with_columns(pl.col("msisdn").alias("caller_id"))
            
        valid_columns = [
            "case_id", "caller_id", "receiver_id", "call_timestamp", 
            "duration", "call_type", "imei", "imsi", "cell_id", "first_cgi", "last_cgi", "operator", "circle", "file_id"
        ]

    elif ft_upper == "IPDR":
        target_table = "forensic_logs.ipdr_records"
        if "session_start" not in pl_df.columns and "call_timestamp" in pl_df.columns:
            pl_df = pl_df.with_columns(pl.col("call_timestamp").alias("session_start"))

        valid_columns = [
            "case_id", "msisdn", "private_ip", "public_ip", "public_ip_v6", "public_port",
            "dest_ip", "dest_ip_v6", "dest_port", "session_start", "session_end",
            "upload_bytes", "download_bytes", "imei", "imsi", "cell_id", "operator", "file_id"
        ]

    elif ft_upper in ["TOWER_DUMP", "IP_DUMP", "TOWER_DUMP_RECORDS"]:
        target_table = "forensic_logs.tower_dump_records"
        if "connection_time" not in pl_df.columns and "call_timestamp" in pl_df.columns:
            pl_df = pl_df.with_columns(pl.col("call_timestamp").alias("connection_time"))
        if "connection_time" not in pl_df.columns and "session_start" in pl_df.columns:
            pl_df = pl_df.with_columns(pl.col("session_start").alias("connection_time"))

        valid_columns = [
            "case_id", "cell_id", "msisdn", "imei", "imsi", "connection_time", 
            "duration", "operator", "file_id"
        ]

    else:
        raise HTTPException(status_code=400, detail=f"Invalid file_type provided: {file_type}")

    # Populating missing fields with default fallbacks
    existing_cols = pl_df.columns
    for col in valid_columns:
        if col not in existing_cols:
            pl_df = pl_df.with_columns(pl.lit("").alias(col))

    # Keep target columns in exact expected order
    pl_df = pl_df.select(valid_columns)

    # 5. Convert String Datetime column into native Datetime Datatype
    dt_target_col = "call_timestamp" if ft_upper == "CDR" else ("session_start" if ft_upper == "IPDR" else "connection_time")
    
    pl_df = pl_df.with_columns(
        pl.col(dt_target_col)
        .str.to_datetime(format="%d-%m-%Y %H:%M:%S", strict=False)
        .fill_null(pl.col(dt_target_col).str.to_datetime(format="%d/%m/%Y %H:%M:%S", strict=False))
        .fill_null(pl.col(dt_target_col).str.to_datetime(format="%Y-%m-%d %H:%M:%S", strict=False))
        .fill_null(pl.col(dt_target_col).str.to_datetime(format="%d-%b-%Y %H:%M:%S", strict=False))
        .fill_null(pl.col(dt_target_col).str.to_datetime(format="%m/%d/%Y %H:%M", strict=False))
        .fill_null(datetime.now())
        .alias(dt_target_col)
    )

    if ft_upper == "IPDR" and "session_end" in pl_df.columns:
        pl_df = pl_df.with_columns(
            pl.col("session_end")
            .str.to_datetime(format="%d-%m-%Y %H:%M:%S", strict=False)
            .fill_null(pl.col("session_end").str.to_datetime(format="%d/%m/%Y %H:%M:%S", strict=False))
            .fill_null(pl.col("session_end").str.to_datetime(format="%Y-%m-%d %H:%M:%S", strict=False))
            .fill_null(pl.col("session_end").str.to_datetime(format="%d-%b-%Y %H:%M:%S", strict=False))
            .fill_null(pl.col(dt_target_col))
            .alias("session_end")
        )

    # Convert to Pandas DataFrame for strict type coercions
    pandas_df = pl_df.to_pandas()

    # 6. Explicit Numerical Casting (Safe conversion of '' -> NaN -> 0 -> Uint)
    if "duration" in pandas_df.columns:
        pandas_df["duration"] = pd.to_numeric(pandas_df["duration"], errors="coerce").fillna(0).astype("uint32")

    if ft_upper == "CDR":
        pandas_df["call_type"] = pandas_df["call_type"].apply(map_call_type_enum).astype("int8")
        pandas_df["circle"] = pandas_df["circle"].fillna("").astype(str)

    elif ft_upper == "IPDR":
        pandas_df["public_ip"] = pandas_df["public_ip"].apply(sanitize_ipv4)
        pandas_df["dest_ip"] = pandas_df["dest_ip"].apply(sanitize_ipv4)
        pandas_df["public_port"] = pd.to_numeric(pandas_df["public_port"], errors="coerce").fillna(0).astype("uint16")
        pandas_df["dest_port"] = pd.to_numeric(pandas_df["dest_port"], errors="coerce").fillna(0).astype("uint16")
        pandas_df["upload_bytes"] = pd.to_numeric(pandas_df["upload_bytes"], errors="coerce").fillna(0).astype("uint64")
        pandas_df["download_bytes"] = pd.to_numeric(pandas_df["download_bytes"], errors="coerce").fillna(0).astype("uint64")
        pandas_df["public_ip_v6"] = None
        pandas_df["dest_ip_v6"] = None

    # Fill remaining text columns with empty strings
    for col in pandas_df.columns:
        if col not in [dt_target_col, "session_end"] and not pd.api.types.is_numeric_dtype(pandas_df[col]):
            pandas_df[col] = pandas_df[col].fillna("").astype(str)

    if len(pandas_df) == 0:
        raise HTTPException(status_code=400, detail="No valid data records remaining after parsing.")

    # 7. ClickHouse Batch Ingestion
    ch_client = get_clickhouse_client()

    try:
        ch_client.insert_df(
            table=target_table,
            df=pandas_df
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ClickHouse batch insert failed: {str(e)}")

    return {
        "status": "SUCCESS",
        "case_id": case_id,
        "file_type": ft_upper,
        "filename": file.filename,
        "rows_ingested": len(pandas_df)
    }