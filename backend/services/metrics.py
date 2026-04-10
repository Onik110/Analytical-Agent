"""
Модуль сбора и расчёта метрик безопасности и качества Agent 1C.

Метрики:
- Success Rate: доля успешных запросов (без ошибок)
- Zero-Fix Rate: доля запросов, выполненных с первой попытки (без исправлений)
- PII Leakage Rate: доля запросов, где ФИО попало в лог после санитизации
- Query Safety Rate: доля запросов, прошедших валидацию без блокировок
- End-to-End Latency: p50, p95, p99 времени выполнения запроса
"""

import math
import time
import logging
from typing import Dict, List
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Метрики одного запроса"""
    success: bool = False
    fix_attempts: int = 0
    had_fio_in_query: bool = False
    fio_leaked_after_sanitize: bool = False
    validation_blocked: bool = False
    latency_ms: float = 0.0
    result_rows: int = 0


class MetricsCollector:
    """
    Коллектор метрик с кольцевым буфером.
    
    Хранит последние N записей для расчёта скользящих метрик.
    Потокобезопасен (использует deque с lock).
    """

    def __init__(self, max_history: int = 1000):
        self._max_history = max_history
        self._history: deque = deque(maxlen=max_history)
        self._lock = __import__('threading').Lock()
        
        self._total_queries = 0
        self._total_success = 0
        self._total_zero_fix = 0
        self._total_pii_detected = 0
        self._total_pii_leaked = 0
        self._total_validation_blocked = 0
        self._total_latency_ms = 0.0

    def record(self, metrics: QueryMetrics) -> None:
        """Записать метрики одного запроса"""
        with self._lock:
            self._history.append(metrics)
            self._total_queries += 1
            
            if metrics.success:
                self._total_success += 1
            if metrics.fix_attempts == 0 and metrics.success:
                self._total_zero_fix += 1
            if metrics.had_fio_in_query:
                self._total_pii_detected += 1
            if metrics.fio_leaked_after_sanitize:
                self._total_pii_leaked += 1
            if metrics.validation_blocked:
                self._total_validation_blocked += 1
            self._total_latency_ms += metrics.latency_ms

    def get_summary(self) -> Dict:
        """
        Получить сводку всех метрик.
        """
        with self._lock:
            total = self._total_queries
            if total == 0:
                return self._empty_summary()

            history = list(self._history)
            n = len(history)
            
            success_count = sum(1 for m in history if m.success)
            zero_fix_count = sum(1 for m in history if m.fix_attempts == 0 and m.success)
            pii_detected_count = sum(1 for m in history if m.had_fio_in_query)
            pii_leaked_count = sum(1 for m in history if m.fio_leaked_after_sanitize)
            validation_blocked_count = sum(1 for m in history if m.validation_blocked)
            
            latencies = sorted([m.latency_ms for m in history])
            
            return {
                "total_queries": total,
                "success_rate": round(success_count / n, 4),
                "zero_fix_rate": round(zero_fix_count / max(success_count, 1), 4),
                "pii_detection_rate": round(pii_detected_count / n, 4),
                "pii_leakage_rate": round(pii_leaked_count / max(pii_detected_count, 1), 4),
                "query_safety_rate": round(1 - (validation_blocked_count / n), 4),
                "latency": {
                    "p50_ms": round(self._percentile(latencies, 50), 1),
                    "p95_ms": round(self._percentile(latencies, 95), 1),
                    "p99_ms": round(self._percentile(latencies, 99), 1),
                    "avg_ms": round(sum(latencies) / n, 1),
                    "min_ms": round(min(latencies), 1),
                    "max_ms": round(max(latencies), 1),
                },
                "cumulative": {
                    "total": self._total_queries,
                    "success": self._total_success,
                    "zero_fix": self._total_zero_fix,
                    "pii_detected": self._total_pii_detected,
                    "pii_leaked": self._total_pii_leaked,
                    "validation_blocked": self._total_validation_blocked,
                }
            }

    def reset(self) -> None:
        """Сбросить все метрики"""
        with self._lock:
            self._history.clear()
            self._total_queries = 0
            self._total_success = 0
            self._total_zero_fix = 0
            self._total_pii_detected = 0
            self._total_pii_leaked = 0
            self._total_validation_blocked = 0
            self._total_latency_ms = 0.0
            logger.info("Метрики сброшены")

    def _percentile(self, sorted_data: List[float], p: float) -> float:
        """Вычислить перцентиль из отсортированных данных"""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1

    def _empty_summary(self) -> Dict:
        return {
            "total_queries": 0,
            "success_rate": 0.0,
            "zero_fix_rate": 0.0,
            "pii_detection_rate": 0.0,
            "pii_leakage_rate": 0.0,
            "query_safety_rate": 0.0,
            "latency": {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
            },
            "cumulative": {
                "total": 0,
                "success": 0,
                "zero_fix": 0,
                "pii_detected": 0,
                "pii_leaked": 0,
                "validation_blocked": 0,
            }
        }


# Глобальный экземпляр
metrics_collector = MetricsCollector(max_history=1000)


class QueryTimer:
    """Контекстный менеджер для замера времени выполнения запроса"""
    
    def __init__(self):
        self.start_time = None
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.monotonic() - self.start_time) * 1000
