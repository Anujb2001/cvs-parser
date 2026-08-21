from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.database import get_clickhouse_client

router = APIRouter()

class MatrixQueryRequest(BaseModel):
    case_id: str
    cell_ids: List[str]
    time_start: str
    time_end: str

@router.post("/matrix")
async def tower_dump_matrix_intersect(req: MatrixQueryRequest):
    """Finds common mobile numbers present across specified cell towers during crime window."""
    ch_client = get_clickhouse_client()
    
    query = """
        SELECT msisdn, COUNT(DISTINCT cell_id) as towers_matched, groupArray(cell_id) as tower_list
        FROM forensic_logs.tower_dump_records
        WHERE case_id = {case_id:String}
          AND cell_id IN {cell_ids:Array(String)}
          AND connection_time BETWEEN {time_start:DateTime} AND {time_end:DateTime}
        GROUP BY msisdn
        HAVING towers_matched = {required_towers:UInt32}
        ORDER BY towers_matched DESC
    """
    
    params = {
        "case_id": req.case_id,
        "cell_ids": req.cell_ids,
        "time_start": req.time_start,
        "time_end": req.time_end,
        "required_towers": len(req.cell_ids)
    }
    
    result = ch_client.query(query, parameters=params)
    
    return {
        "status": "SUCCESS",
        "matched_count": len(result.result_rows),
        "data": [
            {"msisdn": row[0], "towers_matched": row[1], "towers": row[2]}
            for row in result.result_rows
        ]
    }

@router.get("/imei-swap/{imei}")
async def get_sims_for_imei(imei: str, case_id: str):
    """BR-02: Hardware Swap - List all SIM cards inserted into a single target device IMEI."""
    ch_client = get_clickhouse_client()
    
    query = """
        SELECT caller_id as msisdn, imsi, operator, min(call_timestamp) as first_seen, max(call_timestamp) as last_seen, count(*) as call_count
        FROM forensic_logs.cdr_records
        WHERE case_id = {case_id:String} AND imei = {imei:String}
        GROUP BY caller_id, imsi, operator
        ORDER BY first_seen DESC
    """
    
    result = ch_client.query(query, parameters={"case_id": case_id, "imei": imei})
    
    return {
        "target_imei": imei,
        "sims_found": [
            {
                "msisdn": row[0], "imsi": row[1], "operator": row[2],
                "first_seen": str(row[3]), "last_seen": str(row[4]), "call_count": row[5]
            }
            for row in result.result_rows
        ]
    }