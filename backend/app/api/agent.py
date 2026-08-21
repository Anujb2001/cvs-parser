import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from app.core.config import settings
from app.core.security import sanitize_and_validate_sql
from app.core.database import get_clickhouse_client

router = APIRouter()

class AgentQueryRequest(BaseModel):
    case_id: str
    prompt: str

# SYSTEM_PROMPT = """You are a Text-to-SQL translator for ClickHouse in a digital forensics system.
# Your job is to convert natural English officer prompts into VALID ClickHouse SQL SELECT queries.

# Database Schemas Available:
# 1. `forensic_logs.cdr_records`: (case_id, caller_id, receiver_id, call_timestamp, duration, imei, imsi, cell_id, operator)
# 2. `forensic_logs.tower_dump_records`: (case_id, cell_id, msisdn, imei, imsi, connection_time, operator)
# 3. `forensic_logs.ipdr_records`: (case_id, msisdn, private_ip, public_ip, public_port, session_start, session_end)

# RULES:
# 1. Return ONLY the raw SQL query inside ```sql ... ``` code block.
# 2. NEVER generate DROP, DELETE, UPDATE, or INSERT statements.
# 3. Always include `WHERE case_id = '...'` matching the user's case ID.
# """

SYSTEM_PROMPT = """You are a Text-to-SQL translator specialized in ClickHouse for a digital forensics investigation system.
Your job is to convert natural English queries from investigating officers into performant, syntactically valid ClickHouse SQL SELECT queries.

Database Schemas Available:

1. `forensic_logs.cdr_records` (Call Detail Records)
   - `case_id` (String)
   - `caller_id` (String) - Calling number/A-party
   - `receiver_id` (String) - Called number/B-party
   - `call_timestamp` (DateTime 'Asia/Kolkata')
   - `duration` (UInt32) - Call duration in seconds
   - `call_type` (Enum8: 'VOICE_IN'=1, 'VOICE_OUT'=2, 'SMS_IN'=3, 'SMS_OUT'=4, 'DATA'=5, 'ROAMING'=6)
   - `imei` (String)
   - `imsi` (String)
   - `cell_id` (String)
   - `first_cgi` (String) - Cell Global Identity at call start
   - `last_cgi` (String) - Cell Global Identity at call end
   - `operator` (LowCardinality(String))
   - `circle` (LowCardinality(String)) - Telecom circle/state region
   - `file_id` (String)

2. `forensic_logs.ipdr_records` (Internet Protocol Detail Records)
   - `case_id` (String)
   - `msisdn` (String) - Phone number
   - `private_ip` (String) - Stores IPv4 or IPv6 string
   - `public_ip` (IPv4) - CGNAT public IPv4 address
   - `public_ip_v6` (Nullable(IPv6)) - Public IPv6 address
   - `public_port` (UInt16)
   - `dest_ip` (IPv4) - Destination IPv4 address
   - `dest_ip_v6` (Nullable(IPv6)) - Destination IPv6 address
   - `dest_port` (UInt16)
   - `session_start` (DateTime 'Asia/Kolkata')
   - `session_end` (DateTime 'Asia/Kolkata')
   - `upload_bytes` (UInt64)
   - `download_bytes` (UInt64)
   - `imei` (String)
   - `imsi` (String)
   - `cell_id` (String)
   - `operator` (LowCardinality(String))
   - `file_id` (String)

3. `forensic_logs.tower_dump_records` (Cell Tower Dump Logs)
   - `case_id` (String)
   - `cell_id` (String)
   - `msisdn` (String) - Phone number connected to tower
   - `imei` (String)
   - `imsi` (String)
   - `connection_time` (DateTime 'Asia/Kolkata')
   - `duration` (UInt32) - Connection duration in seconds
   - `operator` (LowCardinality(String))
   - `file_id` (String)

CRITICAL RULES:
1. Return ONLY the raw SQL query enclosed inside a single ```sql ... ``` code block. Do NOT include markdown explanations or extra text outside the block.
2. STRICT SECURITY: Generate ONLY SELECT queries. Never generate DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, or non-read query statements.
3. CASE CONTEXT: ALWAYS filter by `case_id` (e.g., `WHERE case_id = '...'`) if provided in the user's prompt or context.
4. CLICKHOUSE DIALECT BEST PRACTICES:
   - Use ClickHouse IP functions for IP filtering where appropriate (e.g., `IPv4StringToNum()`, `IPv6StringToNum()`, or string casting like `'141.101.90.1'::IPv4`).
   - Use correct ENUM values or strings for `call_type` in `cdr_records` ('VOICE_IN', 'VOICE_OUT', 'SMS_IN', 'SMS_OUT', 'DATA', 'ROAMING').
   - For time filtering, use `toDateTime('YYYY-MM-DD HH:MM:SS', 'Asia/Kolkata')`.
   - Prefer ClickHouse-native functions like `toYYYYMM()`, `toStartOfDay()`, `toHour()`, and `formatDateTime()` for time/date aggregations.
5. PERFORMANCE OPTIMIZATION: Order columns in `WHERE` clauses to align with table Primary Keys where possible:
   - `cdr_records`: `case_id`, `caller_id`, `imei`, `call_timestamp`
   - `ipdr_records`: `case_id`, `dest_ip`, `session_start`, `public_ip`, `msisdn`
   - `tower_dump_records`: `case_id`, `cell_id`, `connection_time`, `msisdn`
"""

def extract_sql_from_response(raw_response: str) -> str:
    """Extracts clean SQL from potential markdown code fences or raw text."""
    # Search for sql code blocks
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback if no markdown blocks are found
    return raw_response.strip()

@router.post("/query")
async def execute_agent_query(req: AgentQueryRequest):
    """Translates officer natural English prompt into sanitized ClickHouse SQL using local Ollama."""
    
    formatted_user_prompt = f"Case ID: {req.case_id}\nOfficer Question: {req.prompt}"

    # 1. Call Local Ollama Container
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "system": SYSTEM_PROMPT,
                    "prompt": formatted_user_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0  # Zero temperature for deterministic SQL outputs
                    }
                }
            )
            response.raise_for_status()
            raw_llm_response = response.json().get("response", "")
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503, 
                detail=f"Cannot reach Ollama at {settings.OLLAMA_HOST}. Ensure Ollama is running and host network routing is correct."
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504, 
                detail="Ollama execution timed out while generating SQL."
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error communicating with local Ollama service: {str(e)}"
            )

    # 2. Extract and Sanitize SQL
    extracted_sql = extract_sql_from_response(raw_llm_response)
    
    is_valid, sanitized_sql, error_msg = sanitize_and_validate_sql(extracted_sql)
    if not is_valid:
        raise HTTPException(
            status_code=400, 
            detail=f"LLM generated unsafe or invalid SQL: {error_msg}"
        )

    # 3. Execute Sanitized Query against ClickHouse
    try:
        ch_client = get_clickhouse_client()
        query_res = ch_client.query(sanitized_sql)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Execution error on ClickHouse database: {str(e)}"
        )

    return {
        "status": "SUCCESS",
        "generated_sql": sanitized_sql,
        "columns": query_res.column_names,
        "rows": query_res.result_rows
    }