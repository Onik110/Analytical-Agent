import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.agents.query_agent import OneCAgent
from backend.services.com_client import COMClient
from backend.schemas import QueryRequest, QueryResponse, HealthResponse, MetricsResponse
from backend.config import FASTAPI_HOST, FASTAPI_PORT, DEBUG_MODE
from backend.routes.insight_engine import router as insights_router
from backend.services.metrics import metrics_collector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

agent: OneCAgent = None
com_client: COMClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, com_client
    logger.info("Инициализация FastAPI приложения...")

    from backend.services.file_storage import storage
    deleted = storage.cleanup_old_files()
    logger.info(f"Удалено {deleted} старых файлов")

    try:
        com_client = COMClient()
        logger.info("COM-клиент подключен к 1С")
    except Exception as e:
        logger.warning(f"Не удалось подключить COM-клиент: {e}")
        logger.warning("Сервер запущен БЕЗ доступа к 1С (проверьте версию клиента 1С)")
        com_client = None

    def warmup():
        import pythoncom
        pythoncom.CoInitialize()

        global agent, com_client
        try:
            agent = OneCAgent(com_client=com_client)
            logger.info("LangGraph агент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации агента: {e}")
            return

        if com_client and com_client.is_connected:
            try:
                logger.info("Разогрев соединения с 1С...")
                logger.info(f"Соединение разогрето. Получено {len(result)} строк")
            except Exception as e:
                logger.warning(f"Разогрев пропущен: {e}")

    threading.Thread(target=warmup, daemon=True).start()
    yield

    logger.info("Завершение работы агента...")
    if com_client and com_client.is_connected:
        try:
            com_client.disconnect()
        except Exception as e:
            logger.warning(f"Предупреждение при отключении: {e}")
    logger.info("Приложение остановлено")

app = FastAPI(
    title="1С Ассистент API",
    version="1.0.0",
    description="API для анализа данных 1С с защитой персональных данных",
    lifespan=lifespan
)

app.include_router(insights_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    global agent, com_client
    com_status = com_client.is_connected if com_client else False
    llm_status = agent.llm.client is not None if agent and agent.llm else False

    if com_status and llm_status:
        status = "healthy"
    elif llm_status:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        com_connected=com_status,
        llm_connected=llm_status,
        agent_ready=agent is not None,
        anonymization_enabled=True,
        admin_access=False
    )

@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Получить сводку метрик безопасности и качества"""
    summary = metrics_collector.get_summary()
    return MetricsResponse(**summary)

@app.delete("/api/metrics")
async def reset_metrics():
    """Сбросить все метрики (только для администраторов)"""
    metrics_collector.reset()
    return {"message": "Метрики сброшены"}

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    global agent

    query_stripped = request.query.strip() if request.query else ""
    if not query_stripped:
        return QueryResponse(
            success=False,
            error="Запрос не может быть пустым. Введите ваш вопрос.",
            summary="Пустой запрос",
            fix_attempts=0,
            anonymized=False,
            file_info=None,
            preview_rows=0
        )
    if len(query_stripped) < 3:
        return QueryResponse(
            success=False,
            error="Запрос слишком короток. Опишите, что вы хотите узнать.",
            summary="Слишком короткий запрос",
            fix_attempts=0,
            anonymized=False,
            file_info=None,
            preview_rows=0
        )

    if not agent:
        return QueryResponse(
            success=False,
            error="Агент ещё инициализируется. Попробуйте через 30 секунд.",
            summary="Инициализация системы...",
            fix_attempts=0,
            anonymized=False,
            file_info=None,
            preview_rows=0
        )

    try:
        result = agent.process_query(request.query, save_to_files=request.save)
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {str(e)}", exc_info=True)
        return QueryResponse(
            success=False,
            error=f"Внутренняя ошибка: {str(e)[:200]}",
            summary="Ошибка сервера",
            fix_attempts=0,
            anonymized=False,
            file_info=None,
            preview_rows=0
        )

@app.get("/")
async def root():
    return {
        "message": "1С Ассистент API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "query": "POST /api/query",
            "health": "GET /api/health",
            "files": "GET /api/insights/files"
        }
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Глобальная ошибка: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"Внутренняя ошибка сервера: {str(exc)[:200]}",
            "query_1c": None,
            "result_table": None,
            "summary": "Ошибка обработки запроса к 1С",
            "fix_attempts": 0,
            "anonymized": False,
            "file_info": None,
            "preview_rows": 0
        }
    )

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Запуск сервера на {FASTAPI_HOST}:{FASTAPI_PORT}")
    logger.info(f"Документация: http://{FASTAPI_HOST}:{FASTAPI_PORT}/docs")
    uvicorn.run(
        "backend.main:app",
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        reload=DEBUG_MODE,
        log_level="info"
    )
