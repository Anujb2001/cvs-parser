import sqlglot
import sqlglot.expressions as exp
from typing import Tuple, Optional

ALLOWED_TABLES = {"cdr_records", "ipdr_records", "tower_dump_records", "cell_towers", "sdr_subscribers"}
FORBIDDEN_FUNCTIONS = {"file", "url", "s3", "remote", "eval"}

def sanitize_and_validate_sql(raw_sql: str) -> Tuple[bool, str, Optional[str]]:
    cleaned_sql = raw_sql.strip().strip("```sql").strip("```").strip()
    
    try:
        ast = sqlglot.parse_one(cleaned_sql, read="clickhouse")
    except Exception as e:
        return False, "", f"SQL Syntax Error: {str(e)}"
        
    if not isinstance(ast, (exp.Select, exp.Union)):
        return False, "", "Security Violation: Only SELECT queries are permitted."
        
    for node in ast.walk():
        if isinstance(node, exp.Table):
            table_name = node.name.lower()
            if table_name not in ALLOWED_TABLES:
                return False, "", f"Access to table '{table_name}' is forbidden."
        elif isinstance(node, (exp.Func, exp.Anonymous)):
            func_name = node.key.lower() if isinstance(node, exp.Func) else node.name.lower()
            if func_name in FORBIDDEN_FUNCTIONS:
                return False, "", f"Forbidden function call detected: '{func_name}()'."
                
    if not ast.args.get("limit"):
        ast = ast.limit(5000)
        
    return True, ast.sql(dialect="clickhouse", pretty=True), None   