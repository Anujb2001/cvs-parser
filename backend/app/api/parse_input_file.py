import pandas as pd
import io
import ipaddress
import os
import re

def parse_cdr_to_dataset(filepath):
    """
    Enhanced CDR parser to handle CSV, TXT, and Excel (XLS/XLSX) files.
    Automatically identifies the header, maps columns, extracts call types, and formats timestamps.
    """
    
    is_excel = filepath.lower().endswith(('.xls', '.xlsx'))
    
    header_keywords = [
        'calling', 'called', 'imei', 'imsi', 'duration', 'date', 
        'time', 'cell', 'target', 'party', 'dur(s)', 'mobile no', 'cgi'
    ]
    
    # =========================================================================
    # 1. READ FILE & EXTRACT DATAFRAME
    # =========================================================================
    
    if is_excel:
        xls = pd.ExcelFile(filepath)
        target_sheet = xls.sheet_names[0]
        
        for sheet in xls.sheet_names:
            df_tmp = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=40)
            if len(df_tmp.dropna(how='all')) > 0:
                target_sheet = sheet
                break

        df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=40)
        best_idx, max_score = 0, -1

        for idx, row in df_raw.iterrows():
            row_vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip() != '']
            if len(row_vals) < 2:
                continue
                
            row_str = " ".join(row_vals)
            if row_str.startswith(("input value", "gprs of cell id", "---", "report", "msisdn :")):
                continue

            score = sum(1 for kw in header_keywords if any(kw in val for val in row_vals))
            if score > max_score:
                max_score = score
                best_idx = idx
                
        df = pd.read_excel(xls, sheet_name=target_sheet, skiprows=best_idx, dtype=str)
        
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        cleaned_lines = [line for line in lines if not line.strip().startswith('---')]
        
        header_idx = -1
        best_delim = ','
        
        for i, line in enumerate(cleaned_lines[:50]):
            line_lower = line.strip().lower()
            if not line_lower or line_lower.startswith(("input value", "report", "from date", "till date", "msisdn :", "cellid :")):
                continue

            delims = [',', '\t', ';', '|']
            counts = {d: line_lower.count(d) for d in delims}
            chosen_delim = max(counts, key=counts.get)
            
            if counts[chosen_delim] < 1:
                continue
            
            matches = sum(1 for kw in header_keywords if kw in line_lower)
            if matches >= 3 and counts[chosen_delim] >= 4:
                header_idx = i
                best_delim = chosen_delim
                break
                
        if header_idx == -1:
            raise ValueError(f"Could not dynamically identify the header row in {filepath}.")
            
        csv_data = ''.join(cleaned_lines[header_idx:])
        df = pd.read_csv(io.StringIO(csv_data), skipinitialspace=True, sep=best_delim, on_bad_lines='skip', low_memory=False, dtype=str, index_col=False)

    # =========================================================================
    # 2. CLEAN UP & MAP DATAFRAME
    # =========================================================================
    
    disclaimer_keywords = ["this is system generated", "disclaimer", "signature is not required", "note :-", "lrn :-", "call_forward"]
    valid_rows = []
    
    for _, row in df.iterrows():
        row_str = " ".join([str(val) for val in row.values if pd.notna(val)]).lower()
        if any(keyword in row_str for keyword in disclaimer_keywords):
            break
        valid_rows.append(row)
        
    if not valid_rows:
        raise ValueError("No valid data rows found after parsing.")
        
    df = pd.DataFrame(valid_rows)
    
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.strip("'")
        
    orig_cols = df.columns.astype(str).tolist()
    orig_cols_lower = [c.strip().lower() for c in orig_cols]
    
    # Precise ordering of variations
    column_mappings = {
        'caller_id': ['target no', 'calling party telephone number', 'target /a party number', 'calling', 'caller', 'a_party', 'a party', 'mobile no.', 'mobile no'],
        'receiver_id': ['b party no', 'called party telephone number', 'b party number', 'called', 'receiver', 'b_party', 'b party', 'destination'],
        'duration': ['dur(s)', 'call duration', 'duration in sec', 'duration', 'dur'],
        'imei': ['imei'],
        'imsi': ['imsi'],
        'first_cgi': ['first cgi', 'first cell global id', 'first bts location'],
        'last_cgi': ['last cgi', 'last cell id', 'last cell global id', 'last bts location'],
        'cell_id': ['first cgi lat/long', 'first cell id-name/location', 'first cell id', 'cell id', 'cell_id', 'cgi', 'cell'],
        'circle': ['roaming circle name', 'roaming network/circle', 'roam nw', 'roaming circle', 'circle'],
        'operator': ['operator', 'network', 'roam nw', 'circle'],
        'raw_call_type': ['call type', 'call_type', 'service type', 'service_type', 'toc']
    }
    
    std_df = pd.DataFrame()
    
    for std_col, variations in column_mappings.items():
        found_col = None
        # Step 1: Check for EXACT matches first
        for var in variations:
            exact_matches = [i for i, c in enumerate(orig_cols_lower) if c == var]
            if exact_matches:
                found_col = orig_cols[exact_matches[0]]
                break
        
        # Step 2: Fallback to substring matching
        if not found_col:
            for var in variations:
                partial_matches = [i for i, c in enumerate(orig_cols_lower) if var in c]
                if partial_matches:
                    found_col = orig_cols[partial_matches[0]]
                    break
        
        std_df[std_col] = df[found_col] if found_col else None 

    # =========================================================================
    # 3. STANDARDIZE CALL TYPE (VOICE_IN, VOICE_OUT, SMS_IN, SMS_OUT, etc.)
    # =========================================================================
    
    def map_call_type_string(row_idx):
        row = df.iloc[row_idx]
        row_str = " ".join([str(val).upper() for val in row.values if pd.notna(val)])
        
        # 1. SMS Types
        if any(k in row_str for k in ["SMO", "SMS_OUT", "SMS OUT", "OUTGOING SMS"]):
            return "SMS_OUT"
        elif any(k in row_str for k in ["SMT", "SMS_IN", "SMS IN", "INCOMING SMS"]):
            return "SMS_IN"
        elif "SMS" in row_str:
            return "SMS_IN"
            
        # 2. Voice Call Types
        if any(k in row_str for k in ["OUTGOING", "A_OUT", "MOC", "VOICE_OUT", "CALL_OUT"]):
            return "VOICE_OUT"
        elif any(k in row_str for k in ["INCOMING", "A_IN", "MTC", "VOICE_IN", "CALL_IN"]):
            return "VOICE_IN"
            
        # 3. Data & Roaming
        if any(k in row_str for k in ["GPRS", "DATA", "INTERNET", "IP"]):
            return "DATA"
        elif "ROAM" in row_str:
            return "ROAMING"
            
        return "VOICE_IN"

    std_df['call_type'] = [map_call_type_string(i) for i in range(len(df))]
            
    # Handle Timestamps dynamically
    date_col = next((orig_cols[i] for i, c in enumerate(orig_cols_lower) if 'date' in c or 'start date' in c), None)
    time_col = next((orig_cols[i] for i, c in enumerate(orig_cols_lower) if 'time' in c and 'term' not in c and 'end' not in c), None)
    combined_time_col = next((orig_cols[i] for i, c in enumerate(orig_cols_lower) if 'session start time' in c), None)
    
    if combined_time_col:
        std_df['call_timestamp'] = pd.to_datetime(df[combined_time_col], errors='coerce', dayfirst=True)
    elif date_col and time_col:
        std_df['call_timestamp'] = pd.to_datetime(df[date_col] + ' ' + df[time_col], errors='coerce', dayfirst=True)
    elif date_col:
        std_df['call_timestamp'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    else:
        std_df['call_timestamp'] = None
        
    if 'duration' in std_df.columns:
        std_df['duration'] = pd.to_numeric(std_df['duration'], errors='coerce')
        
    # Full 12-column dataset matching ClickHouse requirements
    final_columns = [
        'caller_id', 'receiver_id', 'call_timestamp', 
        'duration', 'call_type', 'imei', 'imsi', 'first_cgi', 'last_cgi', 'cell_id', 'circle', 'operator'
    ]
    
    return std_df[final_columns]



def parse_ipdr_to_dataset(filepath):
    """Parses telecom IPDR (Excel or CSV) files from Jio, VI, or Airtel

    into a standardized dataset.
    """

    is_excel = filepath.lower().endswith((".xls", ".xlsx"))

    # Common keywords to locate the IPDR header row
    header_keywords = [
        "ip address",
        "destination",
        "translated",
        "port",
        "volume",
        "session",
        "imei",
        "imsi",
        "msisdn",
        "downlink",
        "uplink",
        "source ip",
    ]

    # =========================================================================
    # 1. READ FILE & EXTRACT DATAFRAME
    # =========================================================================

    if is_excel:
        xls = pd.ExcelFile(filepath)
        target_sheet = xls.sheet_names[0]

        for sheet in xls.sheet_names:
            df_tmp = pd.read_excel(
                xls, sheet_name=sheet, header=None, nrows=40
            )
            if len(df_tmp.dropna(how="all")) > 0:
                target_sheet = sheet
                break

        df_raw = pd.read_excel(
            xls, sheet_name=target_sheet, header=None, nrows=40
        )
        best_idx, max_score = 0, -1

        for idx, row in df_raw.iterrows():
            row_vals = [
                str(v).strip().lower()
                for v in row.values
                if pd.notna(v) and str(v).strip() != ""
            ]
            if len(row_vals) < 2:
                continue

            row_str = " ".join(row_vals)
            if row_str.startswith(
                ("input value", "gprs", "---", "report", "msisdn :")
            ):
                continue

            score = sum(
                1
                for kw in header_keywords
                if any(kw in val for val in row_vals)
            )
            if score > max_score:
                max_score = score
                best_idx = idx

        df = pd.read_excel(
            xls, sheet_name=target_sheet, skiprows=best_idx, dtype=str
        )

    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        cleaned_lines = [
            line for line in lines if not line.strip().startswith("---")
        ]
        header_idx, best_delim = -1, ","

        for i, line in enumerate(cleaned_lines[:50]):
            line_lower = line.strip().lower()
            if not line_lower or line_lower.startswith(
                ("input value", "report", "from date", "till date")
            ):
                continue

            delims = [",", "\t", ";", "|"]
            counts = {d: line_lower.count(d) for d in delims}
            chosen_delim = max(counts, key=counts.get)

            if counts[chosen_delim] < 1:
                continue

            matches = sum(1 for kw in header_keywords if kw in line_lower)
            if matches >= 3 and counts[chosen_delim] >= 4:
                header_idx = i
                best_delim = chosen_delim
                break

        if header_idx == -1:
            raise ValueError(
                f"Could not dynamically identify the header row in {filepath}."
            )

        csv_data = "".join(cleaned_lines[header_idx:])
        df = pd.read_csv(
            io.StringIO(csv_data),
            skipinitialspace=True,
            sep=best_delim,
            on_bad_lines="skip",
            low_memory=False,
            dtype=str,
            index_col=False,
        )

    # =========================================================================
    # 2. CLEAN UP FOOTERS
    # =========================================================================

    disclaimer_keywords = [
        "this is system generated",
        "disclaimer",
        "signature is not required",
        "note :-",
        "lrn :-",
        "end of report",
    ]
    valid_rows = []

    for _, row in df.iterrows():
        row_str = " ".join(
            [str(val) for val in row.values if pd.notna(val)]
        ).lower()
        if any(keyword in row_str for keyword in disclaimer_keywords):
            break
        valid_rows.append(row)

    if not valid_rows:
        raise ValueError("No valid data rows found after parsing.")

    df = pd.DataFrame(valid_rows)
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.strip("'")

    # =========================================================================
    # 3. MAP COLUMNS DYNAMICALLY
    # =========================================================================

    orig_cols = df.columns.astype(str).tolist()
    orig_cols_lower = [c.strip().lower() for c in orig_cols]

    # Advanced IPDR Mappings including explicit IPv6 fields
    column_mappings = {
        "msisdn": [
            "msisdn",
            "mobile no.",
            "mobile no",
            "target no",
            "user id for internet access",
            "landline/msisdn",
            "msisdn_userid",
        ],
        "private_ip": [
            "source_private_ipv4",
            "pdp address ipv4",
            "pdp address",
            "source ip address",
            "source ip",
        ],
        "public_ip": [
            "translated ip address",
            "translated ip",
            "source_public_ipv4",
        ],
        "public_ip_v6": ["source_public_ipv6", "pdp address ipv6"],
        "public_port": [
            "translated port",
            "source_public_port",
            "source port",
            "source_handset_port",
        ],
        "dest_ip": [
            "destination_ip4",
            "destination ip address",
            "destination ip",
        ],
        "dest_ip_v6": ["destination_ip6"],
        "dest_port": ["destination port", "destination_port"],
        "upload_bytes": [
            "uplink_vol",
            "data volume up link",
            "data volume uplink",
            "uplink vol",
            "uplink_vol",
        ],
        "download_bytes": [
            "downlink_vol",
            "data volume down link",
            "data volume downlink",
            "downlink vol",
            "downlink_vol",
        ],
        "imei": ["imei", "source mac-id", "mac-id"],
        "imsi": ["imsi"],
        "cell_id": [
            "first cell id",
            "cgi",
            "cell_id",
            "cell id",
            "first cgi",
            "cgi-ld",
        ],
        "operator": [
            "circle",
            "roaming circle",
            "operator",
            "roaming_circle",
            "home_circle",
        ],
    }

    std_df = pd.DataFrame()

    for std_col, variations in column_mappings.items():
        found_col = None
        for var in variations:
            matches = [i for i, c in enumerate(orig_cols_lower) if var in c]
            if matches:
                found_col = orig_cols[matches[0]]
                break
        std_df[std_col] = df[found_col] if found_col else None

    # Fallback logic for IPv6 embedded in IP address columns (e.g. Jio)
    for idx in std_df.index:
        p_ip = str(std_df.at[idx, "private_ip"]) if std_df.at[idx, "private_ip"] else ""
        if ":" in p_ip and (
            pd.isna(std_df.at[idx, "public_ip_v6"])
            or std_df.at[idx, "public_ip_v6"] is None
        ):
            std_df.at[idx, "public_ip_v6"] = p_ip

        d_ip = str(std_df.at[idx, "dest_ip"]) if std_df.at[idx, "dest_ip"] else ""
        if ":" in d_ip and (
            pd.isna(std_df.at[idx, "dest_ip_v6"])
            or std_df.at[idx, "dest_ip_v6"] is None
        ):
            std_df.at[idx, "dest_ip_v6"] = d_ip

    # Identify Date and Time components
    start_date_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "start date" in c
            or ("date" in c and "end" not in c and "time" not in c)
        ),
        None,
    )
    start_time_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "start time" in c and "date" not in c
        ),
        None,
    )
    combined_start_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "session start time" in c or "session_start_time" in c
        ),
        None,
    )

    if combined_start_col:
        std_df["session_start"] = pd.to_datetime(
            df[combined_start_col], errors="coerce", dayfirst=True
        )
    elif start_date_col and start_time_col:
        std_df["session_start"] = pd.to_datetime(
            df[start_date_col] + " " + df[start_time_col],
            errors="coerce",
            dayfirst=True,
        )
    else:
        std_df["session_start"] = (
            pd.to_datetime(df[start_date_col], errors="coerce", dayfirst=True)
            if start_date_col
            else None
        )

    end_date_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "end date" in c
        ),
        start_date_col,
    )
    end_time_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "end time" in c and "date" not in c
        ),
        None,
    )
    combined_end_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "session end time" in c or "session_end_time" in c
        ),
        None,
    )

    if combined_end_col:
        std_df["session_end"] = pd.to_datetime(
            df[combined_end_col], errors="coerce", dayfirst=True
        )
    elif end_date_col and end_time_col:
        std_df["session_end"] = pd.to_datetime(
            df[end_date_col] + " " + df[end_time_col],
            errors="coerce",
            dayfirst=True,
        )
    else:
        std_df["session_end"] = None

    # =========================================================================
    # 4. TYPE CASTING & DEFAULT COLUMNS
    # =========================================================================

    numeric_cols = [
        "public_port",
        "dest_port",
        "upload_bytes",
        "download_bytes",
    ]
    for col in numeric_cols:
        if col in std_df.columns:
            std_df[col] = (
                pd.to_numeric(std_df[col], errors="coerce")
                .fillna(0)
                .astype("uint64")
            )
        else:
            std_df[col] = 0

    final_columns = [
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
    ]

    for col in final_columns:
        if col not in std_df.columns:
            std_df[col] = None

    return std_df[final_columns]


def parse_gprs_to_dataset(filepath):
    """Parses mobile GPRS/IPDR data specifically for Airtel, Jio, and VI telecom formats.

    Supports CSV, TXT, and Excel (.xls, .xlsx) files.
    """
    is_excel = filepath.lower().endswith((".xls", ".xlsx"))

    # Extended header keywords across VI, Jio, and Airtel GPRS layouts
    header_keywords = [
        "mobile no",
        "msisdn",
        "ip address",
        "source ip",
        "downlink",
        "uplink",
        "total vol",
        "session start",
        "session end",
        "imei",
        "imsi",
        "cgi",
        "translated ip",
        "destination ip",
        "roaming circle",
    ]

    # =========================================================================
    # 1. READ FILE & LOCATE HEADER ROW
    # =========================================================================
    if is_excel:
        xls = pd.ExcelFile(filepath)
        target_sheet = xls.sheet_names[0]

        for sheet in xls.sheet_names:
            df_tmp = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=40)
            if len(df_tmp.dropna(how="all")) > 0:
                target_sheet = sheet
                break

        df_raw = pd.read_excel(
            xls, sheet_name=target_sheet, header=None, nrows=40
        )
        best_idx, max_score = 0, -1

        for idx, row in df_raw.iterrows():
            row_vals = [
                str(v).strip().lower()
                for v in row.values
                if pd.notna(v) and str(v).strip() != ""
            ]
            if len(row_vals) < 2:
                continue

            score = sum(
                1
                for kw in header_keywords
                if any(kw in val for val in row_vals)
            )
            if score > max_score:
                max_score = score
                best_idx = idx

        df = pd.read_excel(
            xls, sheet_name=target_sheet, skiprows=best_idx, dtype=str
        )

    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        cleaned_lines = [
            line for line in lines if not line.strip().startswith("---")
        ]
        header_idx, best_delim = -1, ","

        for i, line in enumerate(cleaned_lines[:50]):
            line_lower = line.strip().lower()
            if not line_lower or line_lower.startswith(
                ("input value", "report", "from date", "till date")
            ):
                continue

            delims = [",", "\t", ";", "|"]
            counts = {d: line_lower.count(d) for d in delims}
            chosen_delim = max(counts, key=counts.get)

            if counts[chosen_delim] < 1:
                continue

            matches = sum(1 for kw in header_keywords if kw in line_lower)
            if matches >= 2 and counts[chosen_delim] >= 3:
                header_idx = i
                best_delim = chosen_delim
                break

        if header_idx == -1:
            raise ValueError(
                f"Could not dynamically identify the header row in {filepath}."
            )

        csv_data = "".join(cleaned_lines[header_idx:])
        df = pd.read_csv(
            io.StringIO(csv_data),
            skipinitialspace=True,
            sep=best_delim,
            on_bad_lines="skip",
            low_memory=False,
            dtype=str,
            index_col=False,
        )

    # =========================================================================
    # 2. FILTER INVALID FOOTERS & DISCLAIMERS
    # =========================================================================
    disclaimer_keywords = [
        "this is system generated",
        "disclaimer",
        "signature is not required",
        "note :-",
        "end of report",
        "total records",
    ]
    valid_rows = []

    for _, row in df.iterrows():
        row_str = " ".join(
            [str(val) for val in row.values if pd.notna(val)]
        ).lower()
        if any(keyword in row_str for keyword in disclaimer_keywords):
            break
        valid_rows.append(row)

    if not valid_rows:
        raise ValueError("No valid data rows found after parsing.")

    df = pd.DataFrame(valid_rows)
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.strip("'")

    orig_cols = df.columns.astype(str).tolist()
    orig_cols_lower = [c.strip().lower() for c in orig_cols]

    # =========================================================================
    # 3. COLUMN MAPPER (AIRTEL, JIO, VI MAPPINGS)
    # =========================================================================
    column_mappings = {
        "msisdn": [
            "landline/msisdn/mdn/leased circuit id for internet access",
            "user id for internet access based on authentication",
            "mobile no.",
            "mobile no",
            "msisdn",
            "target no",
            "calling party",
            "a party",
        ],
        "ip_address": [
            "ip address",
            "source ip address",
            "source ip",
            "ip",
            "pdp address",
        ],
        "translated_ip": ["translated ip address", "translated ip"],
        "translated_port": ["translated port"],
        "destination_ip": [
            "destination ip address",
            "destination ip",
            "dest ip",
        ],
        "destination_port": ["destination port", "dest port"],
        "download_bytes": [
            "downlink vol",
            "data volume down link",
            "downlink_vol",
            "downlink",
            "bytes received",
        ],
        "upload_bytes": [
            "uplink vol",
            "data volume up link",
            "uplink_vol",
            "uplink",
            "bytes sent",
        ],
        "total_bytes": ["total vol", "total volume", "total_vol"],
        "imei": ["imei", "source mac-id address", "mac-id"],
        "imsi": ["imsi"],
        "cgi": ["cgi", "first cell id", "cell_id", "cell id", "first cgi"],
        "roaming_circle": ["roaming circle", "home circle", "circle"],
        "network_type": ["2g/4g/5g", "sim type", "rat type", "technology"],
    }

    std_df = pd.DataFrame()

    for std_col, variations in column_mappings.items():
        found_col = None
        # Check exact matches first
        for var in variations:
            matches = [i for i, c in enumerate(orig_cols_lower) if c == var]
            if matches:
                found_col = orig_cols[matches[0]]
                break

        # Fallback substring match
        if not found_col:
            for var in variations:
                matches = [i for i, c in enumerate(orig_cols_lower) if var in c]
                if matches:
                    found_col = orig_cols[matches[0]]
                    break

        std_df[std_col] = df[found_col] if found_col else None

    # Separating IPv4 and IPv6 addresses dynamically
    std_df["ipv4"] = None
    std_df["ipv6"] = None

    for idx in std_df.index:
        ip_val = str(std_df.at[idx, "ip_address"])
        if ":" in ip_val:
            std_df.at[idx, "ipv6"] = ip_val
        elif "." in ip_val:
            std_df.at[idx, "ipv4"] = ip_val

    # =========================================================================
    # 4. TIMESTAMPS & DURATION HANDLING
    # =========================================================================
    start_time_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "session start time" in c
            or "ist start time" in c
            or "start time" in c
        ),
        None,
    )
    start_date_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "start date" in c
        ),
        None,
    )

    if start_time_col and start_date_col:
        std_df["session_start"] = pd.to_datetime(
            df[start_date_col] + " " + df[start_time_col],
            errors="coerce",
            dayfirst=True,
        )
    elif start_time_col:
        std_df["session_start"] = pd.to_datetime(
            df[start_time_col], errors="coerce", dayfirst=True
        )
    else:
        std_df["session_start"] = None

    end_time_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "session end time" in c
            or "ist end time" in c
            or "end time" in c
        ),
        None,
    )
    end_date_col = next(
        (
            orig_cols[i]
            for i, c in enumerate(orig_cols_lower)
            if "end date" in c
        ),
        start_date_col,
    )

    if end_time_col and end_date_col:
        std_df["session_end"] = pd.to_datetime(
            df[end_date_col] + " " + df[end_time_col],
            errors="coerce",
            dayfirst=True,
        )
    elif end_time_col:
        std_df["session_end"] = pd.to_datetime(
            df[end_time_col], errors="coerce", dayfirst=True
        )
    else:
        std_df["session_end"] = None

    # Numeric cast for volume metrics
    for vol_col in ["download_bytes", "upload_bytes", "total_bytes"]:
        if vol_col in std_df.columns:
            std_df[vol_col] = (
                pd.to_numeric(std_df[vol_col], errors="coerce")
                .fillna(0)
                .astype("uint64")
            )

    final_cols = [
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
        "network_type",
    ]

    return std_df[final_cols]