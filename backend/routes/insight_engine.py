from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List

from backend.services.file_storage import storage
from backend.services.simple_insight_engine import insight_engine
from backend.config import ADMIN_API_KEY

router = APIRouter(prefix="/api/insights", tags=["Insights"])

class InsightRequest(BaseModel):
    file_id: str
    prompt: Optional[str] = None

class InsightResponse(BaseModel):
    success: bool
    insight: Optional[str] = None
    error: Optional[str] = None
    rows_analyzed: int = 0
    columns: List[str] = []

class FileListResponse(BaseModel):
    files: List[dict]
    total: int

@router.get("/files", response_model=FileListResponse)
async def list_files():
    """Список файлов — ТОЛЬКО анонимизированные (по умолчанию)"""
    files = storage.list_files(anonymized_only=True)
    return FileListResponse(files=files, total=len(files))

@router.post("/analyze", response_model=InsightResponse)
async def analyze_file(request: InsightRequest):
    """
    Анализ файла через LLM.
    БЕЗОПАСНОСТЬ: Используются ТОЛЬКО анонимизированные данные.
    Сырые данные НЕ отправляются в LLM.
    """
    file_path = storage.get_file_path(request.file_id, anonymized_only=True)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Файл {request.file_id} не найден")
    result = insight_engine.analyze_file(str(file_path), request.prompt)
    if not result["success"]:
        return InsightResponse(success=False, error=result["error"], rows_analyzed=0, columns=[])
    return InsightResponse(success=True, insight=result["insight"], rows_analyzed=result["rows_analyzed"], columns=result["columns"])

@router.get("/files/raw", response_model=FileListResponse)
async def list_raw_files(x_admin_key: str = Header(None)):
    """Список файлов включая сырые (admin only) — ТОЛЬКО для просмотра, НЕ для анализа"""
    if x_admin_key != ADMIN_API_KEY or not ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Требуется ключ администратора")
    files = storage.list_files(anonymized_only=False)
    return FileListResponse(files=files, total=len(files))

@router.post("/cleanup")
async def cleanup_files(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_API_KEY or not ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Требуется ключ администратора")
    deleted = storage.cleanup_old_files()
    return {"deleted": deleted, "status": "ok"}