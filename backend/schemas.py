from pydantic import BaseModel
from typing import Optional, List

class QueryRequest(BaseModel):
    query: str
    save: bool = False

class QueryResponse(BaseModel):
    success: bool
    query_1c: Optional[str] = None
    result_table: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    fix_attempts: int = 0
    anonymized: bool = True
    file_info: Optional[dict] = None
    preview_rows: int = 0

class HealthResponse(BaseModel):
    status: str
    com_connected: bool
    llm_connected: bool
    agent_ready: bool
    anonymization_enabled: bool
    admin_access: bool = False

class MetricsResponse(BaseModel):
    total_queries: int
    success_rate: float
    zero_fix_rate: float
    pii_detection_rate: float
    pii_leakage_rate: float
    query_safety_rate: float
    latency: dict
    cumulative: dict

class FileListResponse(BaseModel):
    files: List[dict]
    total: int

class InsightRequest(BaseModel):
    file_id: str
    prompt: Optional[str] = None

class InsightResponse(BaseModel):
    success: bool
    insight: Optional[str] = None
    error: Optional[str] = None
    rows_analyzed: int = 0
    columns: List[str] = []
