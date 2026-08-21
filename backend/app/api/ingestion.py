import io
import ipaddress
import os
import tempfile
from datetime import datetime

from app.api.parse_input_file import (
    parse_cdr_to_dataset,
    parse_gprs_to_dataset,
    parse_ipdr_to_dataset,
)
from app.core.database import get_clickhouse_client
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import numpy as np
import pandas as pd
import polars as pl

router = APIRouter()


def sanitize_ipv4(ip_str: str):
    """Ensures IP address string is a valid IPv4 address, returning None if invalid or missing."""
    if not ip_str or pd.isna(ip_str):
        return None
    ip_clean = str(ip_str).strip()
    if not ip_clean or ip_clean.lower() in ["none", "nan", "null", "0.0.0.0"]:
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if ip_obj.version == 4:
            return ip_clean
    except ValueError:
        pass
    return None


def sanitize_ipv6(ip_str: str):
    """Ensures IP address string is a valid IPv6 address, returning None if invalid or missing."""
    if not ip_str or pd.isna(ip_str):
        return None
    ip_clean = str(ip_str).strip()
    if not ip_clean or ip_clean.lower() in ["none", "nan", "null"]:
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if ip_obj.version == 6:
            return str(ip_obj)
    except ValueError:
        pass
    return None


def map_call_type_enum(val) -> int:
    """Maps call type strings to ClickHouse Enum8 numbers."""
    if pd.isna(val) or not str(val).strip():
        return 1
    val_upper = str(val).upper().strip()

    # 1: Incoming Voice, 2: Outgoing Voice, 3: Incoming SMS, 4: Outgoing SMS, 5: Data, 6: Roaming
    if any(k in val_upper for k in ["SMS_IN", "SMSIN", "INCOMING SMS", "SMT"]):
        return 3
    elif any(
        k in val_upper for k in ["SMS_OUT", "SMSOUT", "OUTGOING SMS", "SMO"]
    ):
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
    file_type: str = Form(...),  # Expected: 'CDR', 'IPDR', 'GPRS'
    operator: str = Form("UNKNOWN"),
    file: UploadFile = File(...),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=400, detail="Uploaded file is empty."
        )

    ft_upper = file_type.upper().strip()
    if ft_upper not in ["CDR", "IPDR", "GPRS"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file_type provided. Supported types: 'CDR', 'IPDR', 'GPRS'.",
        )

    # Save uploaded file temporarily so parse functions can read from path
    file_ext = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name

    # 1. Parse raw dataset using parse_input_file parser
    try:
        if ft_upper == "CDR":
            df = parse_cdr_to_dataset(tmp_path)
        elif ft_upper == "IPDR":
            df = parse_ipdr_to_dataset(tmp_path)
        elif ft_upper == "GPRS":
            df = parse_gprs_to_dataset(tmp_path)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse file: {str(e)}"
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if df is None or df.empty or len(df.dropna(how="all")) == 0:
        raise HTTPException(
            status_code=400, detail="No valid data rows found in file."
        )

    pl_df = pl.from_pandas(df)

    # 2. Clean values (Strip whitespace & trailing/leading quotes)
    clean_exprs = []
    for col in pl_df.columns:
        clean_exprs.append(
            pl.col(col)
            .cast(pl.Utf8)
            .str.replace_all(r"^['\s]+|['\s]+$", "")
            .alias(col)
        )
    pl_df = pl_df.with_columns(clean_exprs)

    # Append Metadata
    pl_df = pl_df.with_columns(
        [
            pl.lit(case_id).alias("case_id"),
            pl.lit(file.filename).alias("file_id"),
        ]
    )

    if "operator" not in pl_df.columns or pl_df["operator"].is_null().all():
        pl_df = pl_df.with_columns(pl.lit(operator).alias("operator"))

    # 3. Target Table Selection and Schema Normalization
    if ft_upper == "CDR":
        target_table = "forensic_logs.cdr_records"
        valid_columns = [
            "case_id",
            "caller_id",
            "receiver_id",
            "call_timestamp",
            "duration",
            "call_type",
            "imei",
            "imsi",
            "cell_id",
            "first_cgi",
            "last_cgi",
            "operator",
            "circle",
            "file_id",
        ]

    elif ft_upper == "IPDR":
        target_table = "forensic_logs.ipdr_records"
        valid_columns = [
            "case_id",
            "msisdn",
            "private_ip",
            "public_ip",
            "public_ip_v6",
            "public_port",
            "dest_ip",
            "dest_ip_v6",
            "dest_port",
            "session_start",
            "session_end",
            "upload_bytes",
            "download_bytes",
            "imei",
            "imsi",
            "cell_id",
            "operator",
            "file_id",
        ]

    elif ft_upper == "GPRS":
        target_table = "forensic_logs.gprs_records"
        valid_columns = [
            "case_id",
            "msisdn",
            "ipv4",
            "ipv6",
            "translated_ip",
            "translated_port",
            "destination_ip",
            "destination_port",
            "session_start",
            "session_end",
            "download_bytes",
            "upload_bytes",
            "total_bytes",
            "imei",
            "imsi",
            "cgi",
            "roaming_circle",
            "operator",
            "network_type",
            "file_id",
        ]

    # Populating missing fields with default fallbacks
    existing_cols = pl_df.columns
    for col in valid_columns:
        if col not in existing_cols:
            pl_df = pl_df.with_columns(pl.lit(None).alias(col))

    # Keep target columns in exact expected order
    pl_df = pl_df.select(valid_columns)

    # 4. Convert String Datetime column into native Datetime Datatype
    dt_target_col = "call_timestamp" if ft_upper == "CDR" else "session_start"

    pl_df = pl_df.with_columns(
        pl.col(dt_target_col)
        .str.to_datetime(format="%d-%m-%Y %H:%M:%S", strict=False)
        .fill_null(
            pl.col(dt_target_col).str.to_datetime(
                format="%d/%m/%Y %H:%M:%S", strict=False
            )
        )
        .fill_null(
            pl.col(dt_target_col).str.to_datetime(
                format="%Y-%m-%d %H:%M:%S", strict=False
            )
        )
        .fill_null(
            pl.col(dt_target_col).str.to_datetime(
                format="%d-%b-%Y %H:%M:%S", strict=False
            )
        )
        .fill_null(
            pl.col(dt_target_col).str.to_datetime(
                format="%d-%m-%y %H:%M", strict=False
            )
        )
        .fill_null(datetime.now())
        .alias(dt_target_col)
    )

    if ft_upper in ["IPDR", "GPRS"] and "session_end" in pl_df.columns:
        pl_df = pl_df.with_columns(
            pl.col("session_end")
            .str.to_datetime(format="%d-%m-%Y %H:%M:%S", strict=False)
            .fill_null(
                pl.col("session_end").str.to_datetime(
                    format="%d/%m/%Y %H:%M:%S", strict=False
                )
            )
            .fill_null(
                pl.col("session_end").str.to_datetime(
                    format="%Y-%m-%d %H:%M:%S", strict=False
                )
            )
            .fill_null(
                pl.col("session_end").str.to_datetime(
                    format="%d-%b-%Y %H:%M:%S", strict=False
                )
            )
            .fill_null(
                pl.col("session_end").str.to_datetime(
                    format="%d-%m-%y %H:%M", strict=False
                )
            )
            .fill_null(pl.col(dt_target_col))
            .alias("session_end")
        )

    # Convert to Pandas DataFrame for strict type coercions
    pandas_df = pl_df.to_pandas()

    # 5. Explicit Type Castings
    if "duration" in pandas_df.columns:
        pandas_df["duration"] = (
            pd.to_numeric(pandas_df["duration"], errors="coerce")
            .fillna(0)
            .astype("uint32")
        )

    if ft_upper == "CDR":
        pandas_df["call_type"] = (
            pandas_df["call_type"].apply(map_call_type_enum).astype("int8")
        )
        pandas_df["circle"] = pandas_df["circle"].fillna("").astype(str)

    elif ft_upper == "IPDR":
        pandas_df["public_ip"] = pandas_df["public_ip"].apply(sanitize_ipv4)
        pandas_df["dest_ip"] = pandas_df["dest_ip"].apply(sanitize_ipv4)
        pandas_df["public_ip_v6"] = pandas_df["public_ip_v6"].apply(
            sanitize_ipv6
        )
        pandas_df["dest_ip_v6"] = pandas_df["dest_ip_v6"].apply(sanitize_ipv6)

        pandas_df["public_port"] = (
            pd.to_numeric(pandas_df["public_port"], errors="coerce")
            .fillna(0)
            .astype("uint16")
        )
        pandas_df["dest_port"] = (
            pd.to_numeric(pandas_df["dest_port"], errors="coerce")
            .fillna(0)
            .astype("uint16")
        )
        pandas_df["upload_bytes"] = (
            pd.to_numeric(pandas_df["upload_bytes"], errors="coerce")
            .fillna(0)
            .astype("uint64")
        )
        pandas_df["download_bytes"] = (
            pd.to_numeric(pandas_df["download_bytes"], errors="coerce")
            .fillna(0)
            .astype("uint64")
        )

    elif ft_upper == "GPRS":
        pandas_df["ipv4"] = pandas_df["ipv4"].apply(sanitize_ipv4)
        pandas_df["translated_ip"] = pandas_df["translated_ip"].apply(
            sanitize_ipv4
        )
        pandas_df["destination_ip"] = pandas_df["destination_ip"].apply(
            sanitize_ipv4
        )
        pandas_df["ipv6"] = pandas_df["ipv6"].apply(sanitize_ipv6)

        pandas_df["translated_port"] = (
            pd.to_numeric(pandas_df["translated_port"], errors="coerce")
            .fillna(0)
            .astype("uint16")
        )
        pandas_df["destination_port"] = (
            pd.to_numeric(pandas_df["destination_port"], errors="coerce")
            .fillna(0)
            .astype("uint16")
        )

        pandas_df["download_bytes"] = (
            pd.to_numeric(pandas_df["download_bytes"], errors="coerce")
            .fillna(0)
            .astype("uint64")
        )
        pandas_df["upload_bytes"] = (
            pd.to_numeric(pandas_df["upload_bytes"], errors="coerce")
            .fillna(0)
            .astype("uint64")
        )
        pandas_df["total_bytes"] = (
            pd.to_numeric(pandas_df["total_bytes"], errors="coerce")
            .fillna(0)
            .astype("uint64")
        )

    # EXCLUDE all IPv4 / IPv6 / Datetime columns from string conversion
    # so ClickHouse driver correctly passes NULLs instead of ""
    excluded_cols = [
        dt_target_col,
        "session_end",
        "ipv4",
        "ipv6",
        "translated_ip",
        "destination_ip",
        "public_ip",
        "public_ip_v6",
        "dest_ip",
        "dest_ip_v6",
        "private_ip",
    ]

    for col in pandas_df.columns:
        if (
            col not in excluded_cols
            and not pd.api.types.is_numeric_dtype(pandas_df[col])
        ):
            pandas_df[col] = pandas_df[col].fillna("").astype(str)

    if len(pandas_df) == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid data records remaining after parsing.",
        )

    # 6. ClickHouse Batch Ingestion
    ch_client = get_clickhouse_client()

    try:
        ch_client.insert_df(table=target_table, df=pandas_df)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"ClickHouse batch insert failed: {str(e)}"
        )

    return {
        "status": "SUCCESS",
        "case_id": case_id,
        "file_type": ft_upper,
        "filename": file.filename,
        "rows_ingested": len(pandas_df),
    }