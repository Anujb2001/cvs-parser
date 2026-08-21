from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_postgres_pool
from app.api import ingestion, analytics, agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize async database connection pools on startup
    await init_postgres_pool()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(ingestion.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingestion"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["Analytics"])
app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["AI Agent"])

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "air_gap_mode": True}