from typing import TypedDict, List, Optional, Dict

class AgentState(TypedDict):
    """Схема состояния для LangGraph агента"""
    user_query: str
    sanitized_query: str
    chat_history: List[Dict]
    generated_query: Optional[str]
    validation_passed: bool
    validation_errors: List[str]
    execution_result: Optional[List]
    error: Optional[str]
    anonymized_data: Optional[List]
    html_table: Optional[str]
    analysis: Optional[str]
    fix_attempts: int
    max_attempts: int
    date_range: Optional[tuple]
    seen_errors: List[str]
    success: bool
    # Метрики (внутренние, не влияют на workflow)
    _fio_detected: bool         
    _validation_blocked: bool    
