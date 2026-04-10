import os
import logging
import threading
import pythoncom
import win32com.client
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.config import COM_MAX_ROWS, COM_PORT
import concurrent.futures

logger = logging.getLogger(__name__)

# Глобальное соединение — инициализируется ОДИН РАЗ при старте
_connection = None
_connection_lock = threading.Lock()
_connection_initialized = False

class COMClient:
    def __init__(self):
        self.server = os.getenv("COM_SERVER")
        self.base = os.getenv("COM_BASE")
        self.user = os.getenv("COM_USER")
        self.password = os.getenv("COM_PASSWORD")
        self.is_connected = False
        self.query_timeout = int(os.getenv("COM_QUERY_TIMEOUT", "60")) 
        self.connect()

    def connect(self) -> bool:
        global _connection, _connection_initialized
        try:
            if not _connection_initialized:
                pythoncom.CoInitialize()
                _connection_initialized = True
                logger.info("COM инициализирован один раз")

            with _connection_lock:
                if _connection is None:
                    conn_string = f'Srvr="{self.server}:{COM_PORT}";Ref="{self.base}"'
                    if self.user:
                        conn_string += f';Usr="{self.user}"'
                    if self.password:
                        conn_string += f';Pwd="{self.password}"'

                    logger.info(f"Подключаюсь к 1С: {self.server}/{self.base}")
                    start_time = datetime.now()

                    connector = win32com.client.Dispatch("V83.COMConnector")
                    _connection = connector.Connect(conn_string)

                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Соединение с 1С установлено за {elapsed:.1f} сек")

                self.is_connected = True
                return True

        except Exception as e:
            logger.error(f"Ошибка подключения: {str(e)}")
            raise

    def disconnect(self):
        global _connection, _connection_initialized
        try:
            with _connection_lock:
                if _connection is not None:
                    del _connection
                    _connection = None
                
                if _connection_initialized:
                    try:
                        pythoncom.CoUninitialize()
                        logger.info("COM деинициализирован (CoUninitialize)")
                    except Exception as com_err:
                        logger.warning(f"CoUninitialize предупреждение: {com_err}")
                    _connection_initialized = False
                
                self.is_connected = False
                logger.info("Соединение с 1С закрыто")
        except Exception as e:
            logger.warning(f"Предупреждение при закрытии: {str(e)}")

    def execute_safe_query(self, query_text: str, date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self.is_connected:
            raise RuntimeError("COM-соединение не установлено")

        def _execute_with_timeout():
            pythoncom.CoInitialize()
            try:
                return self._execute_query_impl(query_text, date_range)
            finally:
                # Освобождаем COM-ресурсы потока
                pythoncom.CoUninitialize()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute_with_timeout)
                return future.result(timeout=self.query_timeout)
        except concurrent.futures.TimeoutError:
            logger.error(f"Таймаут запроса 1С ({self.query_timeout} сек)")
            raise RuntimeError(f"Запрос 1С превысил таймаут ({self.query_timeout} сек). Возможно, запрос слишком сложный или 1С заблокирована.")
        except Exception as e:
            raise RuntimeError(f"Ошибка выполнения запроса 1С: {str(e)}")

    def _execute_query_impl(self, query_text: str, date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Реализация выполнения запроса"""
        try:
            logger.info(f"Выполняю запрос 1С:\n{query_text[:200]}...")
            query = _connection.NewObject("Query", query_text)
            if date_range and "&нач" in query_text and "&кон" in query_text:
                start_date, end_date = date_range
                query.SetParameter("нач", start_date)
                query.SetParameter("кон", end_date)
                logger.debug(f"Установлены параметры дат: {start_date} - {end_date}")

            logger.info("Запрос отправлен в 1С...")
            result = query.Execute()
            logger.info("Запрос выполнен в 1С, получаю данные...")
            
            choice = result.Choose()
            columns = self._extract_columns(query_text)
            rows = []
            row_count = 0

            while choice.Next():
                row = {}
                for col in columns:
                    try:
                        value = getattr(choice, col, None)
                        if value and hasattr(value, 'Наименование'):
                            row[col] = str(value.Наименование)
                        elif value and hasattr(value, 'Имя'):
                            row[col] = str(value.Имя)
                        else:
                            row[col] = self._safe_str(value)
                    except Exception as col_err:
                        logger.warning(f"Ошибка чтения колонки {col}: {col_err}")
                        row[col] = ""
                rows.append(row)
                row_count += 1
                if row_count % 100 == 0:
                    logger.debug(f"Прочитано {row_count} строк...")
                if COM_MAX_ROWS > 0 and row_count >= COM_MAX_ROWS:
                    logger.info(f"Достигнут лимит строк: {COM_MAX_ROWS}")
                    break

            logger.info(f"Запрос завершен: {row_count} строк")
            return rows
        except Exception as e:
            raise RuntimeError(f"Ошибка выполнения запроса 1С: {str(e)}")

    def _extract_columns(self, query_text: str) -> List[str]:
        if "КОЛИЧЕСТВО(*)" in query_text.upper():
            return ["Количество"]
        if "СУММА(" in query_text.upper():
            return ["Итого"]

        select_match = re.search(r'ВЫБРАТЬ\s+(.*?)\s+ИЗ', query_text, re.DOTALL | re.IGNORECASE)
        if not select_match:
            raise ValueError("Не найдена секция ВЫБРАТЬ")

        select_block = select_match.group(1)
        aliases = re.findall(r'КАК\s+([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)', select_block, re.IGNORECASE)

        if not aliases:
            raise ValueError("Не найдено алиасов (КАК ...)")

        return aliases

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        try:
            if hasattr(value, 'strftime'):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            return str(value)
        except:
            return str(value)
