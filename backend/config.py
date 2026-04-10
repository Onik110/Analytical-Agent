import os
from dotenv import load_dotenv

load_dotenv()

# 1С COM Connection 
COM_SERVER = os.getenv("COM_SERVER")
COM_BASE = os.getenv("COM_BASE")
COM_PORT = int(os.getenv("COM_PORT"))
COM_USER = os.getenv("COM_USER")
COM_PASSWORD = os.getenv("COM_PASSWORD")
COM_MAX_ROWS = int(os.getenv("COM_MAX_ROWS", "1000"))
COM_QUERY_TIMEOUT = int(os.getenv("COM_QUERY_TIMEOUT", "60"))  

# Mistral API 
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL")

# FastAPI Server
FASTAPI_HOST = os.getenv("FASTAPI_HOST")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT"))
DEBUG_MODE = os.getenv("DEBUG_MODE") == "True"

# Security & Anonymization
ANONYMIZE_FIO = os.getenv("ANONYMIZE_FIO") == "True"
ANONYMIZE_TERMINALS = os.getenv("ANONYMIZE_TERMINALS") == "True"
ANONYMIZE_VRC = os.getenv("ANONYMIZE_VRC") == "True"
ANONYMIZE_REASONS = os.getenv("ANONYMIZE_REASONS") == "True"
ENABLE_QUERY_VALIDATION = os.getenv("ENABLE_QUERY_VALIDATION") == "True"
MAX_FIX_ATTEMPTS = int(os.getenv("MAX_FIX_ATTEMPTS"))
LOG_QUERIES = os.getenv("LOG_QUERIES") == "True"

DATA_DIR = os.getenv("DATA_DIR", "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
ANONYMIZED_DATA_DIR = os.path.join(DATA_DIR, "anonymized")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PANDASAI_MAX_ROWS = int(os.getenv("PANDASAI_MAX_ROWS", "1000"))
FILE_TTL_DAYS = int(os.getenv("FILE_TTL_DAYS", "30"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# System Prompt
SYSTEM_PROMPT = """
Ты — эксперт по языку запросов 1С:Предприятие 8.3. 
            Твоя задача — сгенерировать **строго корректный** и **рабочий** запрос на языке 1С, 
            который можно сразу выполнить через COM-объект 1С без ошибок.\n\n

            КОНТЕКСТ БАЗЫ ДАННЫХ\n
            1. ...
            2. ...

            СТРОГИЕ ПРАВИЛА \n
            1. ...
            2. ...

            Примеры полностью рабочих запросов\n
            1. ...
            2. ...

"""
