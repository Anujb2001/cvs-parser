from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Forensic Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    
    # ClickHouse Configuration
    CLICKHOUSE_HOST: str = "clickhouse_db"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "clickhouse_admin"
    CLICKHOUSE_PASSWORD: str = "LocalClickhousePassword123!"
    CLICKHOUSE_DB: str = "forensic_logs"
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "postgres_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "lea_admin"
    POSTGRES_PASSWORD: str = "LocalSecurePassword123!"
    POSTGRES_DB: str = "forensic_db"
    
    # Ollama Local LLM Configuration
    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"

settings = Settings()