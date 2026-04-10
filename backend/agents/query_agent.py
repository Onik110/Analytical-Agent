from typing import Dict, Any
from langgraph.graph import StateGraph, END
from backend.agents.state import AgentState
from backend.services.llm_client import MistralAPIClient
from backend.services.com_client import COMClient
from backend.services.anonymizer import DataAnonymizer
from backend.services.query_validator import QueryValidator
from backend.utils.query_utils import detect_date_range, format_result_as_html_table
from backend.config import SYSTEM_PROMPT, MAX_FIX_ATTEMPTS, ENABLE_QUERY_VALIDATION
import logging
import re
from backend.services.file_storage import storage
from backend.services.metrics import metrics_collector, QueryMetrics, QueryTimer

logger = logging.getLogger(__name__)

class OneCAgent:
    """LangGraph агент для обработки запросов к 1С"""

    def __init__(self, com_client: COMClient = None):
        self.llm = MistralAPIClient()
        self.com = com_client  
        self.anonymizer = DataAnonymizer()
        self.validator = QueryValidator()
        self.graph = self._create_graph()
        logger.info("LangGraph агент 1С создан")

    def _create_graph(self):
        """Создаёт граф состояний агента"""
        workflow = StateGraph(AgentState)

        # Добавляем ноды
        workflow.add_node("sanitize_query", self._sanitize_query_node)
        workflow.add_node("detect_date_range", self._detect_date_range_node)
        workflow.add_node("generate_query", self._generate_query_node)
        workflow.add_node("validate_query", self._validate_query_node)
        workflow.add_node("execute_query", self._execute_query_node)
        workflow.add_node("check_error", self._check_error_node)
        workflow.add_node("fix_query", self._fix_query_node)
        workflow.add_node("anonymize_data", self._anonymize_data_node)
        workflow.add_node("analyze_data", self._analyze_data_node)
        workflow.add_node("format_result", self._format_result_node)

        # Настраиваем поток выполнения
        workflow.set_entry_point("sanitize_query")
        workflow.add_edge("sanitize_query", "detect_date_range")
        workflow.add_edge("detect_date_range", "generate_query")
        workflow.add_edge("generate_query", "validate_query")

        # Условный переход после валидации:
        workflow.add_conditional_edges(
            "validate_query",
            self._should_execute_query,
            {
                "execute": "execute_query",
                "retry": "fix_query",
                "fail": END
            }
        )

        workflow.add_edge("execute_query", "check_error")

        # Условные переходы для обработки ошибок
        workflow.add_conditional_edges(
            "check_error",
            self._should_fix_query,
            {
                "fix": "fix_query",
                "success": "anonymize_data",
                "fail": END
            }
        )

        workflow.add_edge("fix_query", "generate_query")
        workflow.add_edge("anonymize_data", "analyze_data")
        workflow.add_edge("analyze_data", "format_result")
        workflow.add_edge("format_result", END)

        return workflow.compile()

    def _sanitize_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Очищает запрос от ФИО ДО отправки в LLM"""
        logger.info("Очистка запроса от ПнД...")

        sanitized_query, found_fio = self.anonymizer.sanitize_user_query(state["user_query"])

        if found_fio:
            logger.warning(f"Обнаружены ФИО в запросе: {found_fio}. Заменены на [ФИО_ТКАЧА]")

        return {
            "sanitized_query": sanitized_query,
            "fix_attempts": 0,
            "max_attempts": MAX_FIX_ATTEMPTS,
            "validation_passed": False,
            "validation_errors": [],
            "seen_errors": [],
            "success": False,
            "_fio_detected": len(found_fio) > 0,
            "_validation_blocked": False
        }

    def _detect_date_range_node(self, state: AgentState) -> Dict[str, Any]:
        """Определяет диапазон дат из запроса"""
        logger.info("Определение диапазона дат...")
        date_range = detect_date_range(state["sanitized_query"])
        logger.info(f"Диапазон: {date_range[0].date()} - {date_range[1].date()}")
        return {"date_range": date_range}

    def _generate_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Генерирует запрос 1С через LLM."""
        logger.info(f"Генерация запроса (попытка {state.get('fix_attempts', 0) + 1})")

        prompt = f"{SYSTEM_PROMPT}\n\nЗапрос пользователя: {state['sanitized_query']}"

        if state.get("error"):
            prompt += f"\n\nПредыдущая ошибка: {state['error']}\nИсправь запрос:"

        messages = [{"role": "user", "content": prompt}]
        query_1c = self.llm.chat_with_history(messages)

        logger.info(f"Сгенерирован запрос:\n{query_1c}")
        return {"generated_query": query_1c}

    def _validate_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Валидация запроса"""
        logger.info("Валидация запроса...")

        if not state.get("generated_query"):
            return {"validation_passed": False, "validation_errors": ["Нет сгенерированного запроса"], "_validation_blocked": True}

        passed, errors, _ = self.validator.validate(state["generated_query"])

        if not passed:
            logger.error(f"Запрос не прошёл валидацию: {errors}")
            return {"validation_passed": False, "validation_errors": errors, "_validation_blocked": True}

        logger.info("Запрос прошёл валидацию")
        return {"validation_passed": True, "validation_errors": [], "_validation_blocked": False}

    def _execute_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Выполнение запроса через COM"""
        logger.info("Выполнение запроса через COM...")

        if not self.com:
            return {"error": "COM-клиент не подключён. Проверьте версию клиента 1С."}

        if not state.get("generated_query") or not state.get("validation_passed"):
            return {"error": "Нет валидного запроса для выполнения"}

        try:
            result = self.com.execute_safe_query(
                state["generated_query"],
                date_range=state.get("date_range")
            )
            logger.info(f"Запрос выполнен: {len(result)} строк")
            return {"execution_result": result, "error": None}
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Ошибка выполнения: {error_msg[:100]}")
            return {"error": error_msg}

    def _check_error_node(self, state: AgentState) -> Dict[str, Any]:
        """Проверка наличия ошибки и подготовка к исправлению."""
        error = state.get("error")
        fix_attempts = state.get("fix_attempts", 0)
        seen_errors = state.get("seen_errors", [])

        if error:
            if error in seen_errors[-2:] and fix_attempts > 1:
                logger.error(f"Прерван цикл исправлений: повторяющаяся ошибка '{error[:50]}...'")
                return {"fix_attempts": fix_attempts, "seen_errors": seen_errors, "success": False}

            seen_errors.append(error)
            return {
                "fix_attempts": fix_attempts,
                "seen_errors": seen_errors[-5:],
                "success": False
            }

        return {"success": True}

    def _should_fix_query(self, state: AgentState) -> str:
        """Решение: завершить или исправлять"""
        if state.get("success"):
            return "success"

        fix_attempts = state.get("fix_attempts", 0)
        max_attempts = state.get("max_attempts", MAX_FIX_ATTEMPTS)

        if fix_attempts >= max_attempts:
            logger.error(f"Не удалось выполнить запрос после {max_attempts} попыток")
            return "fail"

        return "fix"

    def _should_execute_query(self, state: AgentState) -> str:
        """Решение: выполнить запрос или отправить на retry после валидации."""
        if state.get("validation_passed"):
            return "execute"

        max_attempts = state.get("max_attempts", MAX_FIX_ATTEMPTS)
        fix_attempts = state.get("fix_attempts", 0)

        if fix_attempts >= max_attempts:
            logger.error(f"Валидация не пройдена после {max_attempts} попыток")
            return "fail"

        return "retry"

    def _fix_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Подготовка к повторной генерации запроса."""
        fix_attempts = state.get("fix_attempts", 0)
        logger.info(f"Исправление запроса (попытка {fix_attempts}/{state.get('max_attempts', MAX_FIX_ATTEMPTS)})...")

        errors = state.get("validation_errors", [])
        error_msg = state.get("error", "")
        feedback = "; ".join(errors) if errors else error_msg

        return {
            "error": f"Валидация/выполнение не пройдено: {feedback}",
            "fix_attempts": fix_attempts + 1
        }

    def _anonymize_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Анонимизация данных ПЕРЕД отправкой пользователю"""
        logger.info("Анонимизация данных...")

        if not state.get("execution_result"):
            return {"anonymized_data": [], "html_table": "<p class='text-red-500'> Нет данных для анонимизации</p>"}

        anonymized = self.anonymizer.anonymize_data(state["execution_result"])
        logger.info(f"Данные анонимизированы ({len(anonymized)} строк)")
        return {"anonymized_data": anonymized}

    def _analyze_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Безопасная сводка без отправки данных в LLM"""
        logger.info("Генерация безопасной сводки (без LLM)...")

        anonymized_data = state.get("anonymized_data", [])
        if not anonymized_data:
            return {"analysis": "Нет данных для отображения"}

        rows = len(anonymized_data)
        columns = list(anonymized_data[0].keys()) if anonymized_data else []

        stats = []
        for col in columns[:3]:
            values = [str(row.get(col, '')) for row in anonymized_data if row.get(col)]
            unique = len(set(values))
            if unique > 0:
                stats.append(f"• {col}: {unique} уникальных значений")

        summary = f"Запрос выполнен: {rows} строк"
        if stats:
            summary += "\n\nКраткая статистика:\n" + "\n".join(stats)
        summary += "\n\nДля детального анализа выберите файл в правой панели и нажмите «Авто-анализ»"

        return {"analysis": summary}

    def _format_result_node(self, state: AgentState) -> Dict[str, Any]:
        """Форматирование результата в HTML таблицу"""
        logger.info("Форматирование результата...")

        anonymized_data = state.get("anonymized_data", [])
        if not anonymized_data:
            html_table = "<p class='text-gray-500'>Нет данных</p>"
        else:
            columns = list(anonymized_data[0].keys())
            html_table = format_result_as_html_table(anonymized_data, columns)

        logger.info("Результат отформатирован")
        return {
            "html_table": html_table,
            "success": True
        }

    def process_query(self, user_query: str, save_to_files: bool = False) -> Dict[str, Any]:
        """Основной метод обработки запроса пользователя"""
        logger.info(f"Новый запрос: {user_query}")

        initial_state: AgentState = {
            "user_query": user_query,
            "sanitized_query": "",
            "chat_history": [],
            "generated_query": None,
            "validation_passed": False,
            "validation_errors": [],
            "execution_result": None,
            "error": None,
            "anonymized_data": None,
            "html_table": None,
            "analysis": None,
            "fix_attempts": 0,
            "max_attempts": MAX_FIX_ATTEMPTS,
            "date_range": None,
            "seen_errors": [],
            "success": False,
            "_fio_detected": False,
            "_validation_blocked": False
        }

        with QueryTimer() as timer:
            try:
                final_state = self.graph.invoke(initial_state)

                file_info = None
                if save_to_files and final_state.get("success"):
                    try:
                        file_info = storage.save_result(
                            query=user_query,
                            data=final_state.get("execution_result", []),
                            anonymized_data=final_state.get("anonymized_data", [])
                        )
                        logger.info(f"Файл сохранён: {file_info['file_id']}")
                    except Exception as e:
                        logger.error(f"Ошибка сохранения файла: {e}")

                result = {
                    "success": final_state.get("success", False),
                    "query_1c": final_state.get("generated_query"),
                    "result_table": final_state.get("html_table"),
                    "summary": final_state.get("analysis", "Запрос выполнен"),
                    "error": final_state.get("error"),
                    "fix_attempts": final_state.get("fix_attempts", 0),
                    "anonymized": True,
                    "file_info": file_info,
                    "preview_rows": len(final_state.get("anonymized_data", [])[:10])
                }

            except Exception as e:
                logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
                result = {
                    "success": False,
                    "error": f"Ошибка обработки: {str(e)[:300]}",
                    "query_1c": None,
                    "fix_attempts": 0,
                    "anonymized": False
                }
                final_state = initial_state

        # Записываем метрики
        fio_leaked = False
        if final_state.get("_fio_detected"):
            sanitized = final_state.get("sanitized_query", "")
            fio_pattern = re.compile(r'[А-ЯЁ][а-яё]{2,}\s[А-ЯЁ][а-яё]{1,}\.\s*[А-ЯЁ]\.')
            if fio_pattern.search(sanitized):
                fio_leaked = True

        query_metrics = QueryMetrics(
            success=final_state.get("success", False),
            fix_attempts=final_state.get("fix_attempts", 0),
            had_fio_in_query=final_state.get("_fio_detected", False),
            fio_leaked_after_sanitize=fio_leaked,
            validation_blocked=final_state.get("_validation_blocked", False),
            latency_ms=timer.elapsed_ms,
            result_rows=len(final_state.get("execution_result", []) or [])
        )
        metrics_collector.record(query_metrics)

        logger.info(f"Метрики запроса: success={query_metrics.success}, "
                     f"latency={query_metrics.latency_ms:.0f}ms, "
                     f"fix_attempts={query_metrics.fix_attempts}, "
                     f"fio_detected={query_metrics.had_fio_in_query}")

        return result
