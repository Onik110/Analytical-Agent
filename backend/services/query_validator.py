import re
from typing import List, Tuple

class QueryValidator:
    """
    Валидатор запросов 1С.
    """

    def __init__(self):
        self.dangerous_keywords = [
            r'\bВСТАВИТЬ\b', r'\bУДАЛИТЬ\b', r'\bИЗМЕНИТЬ\b', r'\bОБНОВИТЬ\b',
            r'\bЗАПИСАТЬ\b', r'\bEXEC\b', r'\bDROP\b', r'\bTRUNCATE\b',
            r'\bALTER\b', r'\bКонфигурация\b', r'\bМетаданные\b',
        ]
        # Запрещённые функции и параметры — вместо них &нач и &кон
        self.banned_functions = [
            r'\bДОБАВИТЬКДАТЕ\b', r'\bНАЧАЛОПЕРИОДА\b', r'\bКОНЕЦПЕРИОДА\b',
            r'\bТЕКУЩАЯДАТА\b', r'\bВЫРАЗИТЬ\b',
        ]
        self.banned_params = [
            r'&текущаяДата', r'&дата', r'&начало', r'&конец',
        ]

    def validate(self, query_text: str) -> Tuple[bool, List[str], List[str]]:
        errors = []
        warnings = []

        if len(query_text) > 10000:
            errors.append("Запрос слишком длинный")
            return False, errors, warnings

        query_upper = query_text.upper()
        for pattern in self.dangerous_keywords:
            if re.search(pattern, query_text, re.IGNORECASE):
                keyword = re.search(pattern, query_text, re.IGNORECASE).group(0)
                errors.append(f"Обнаружено запрещённое ключевое слово: {keyword}")

        if not query_upper.strip().startswith("ВЫБРАТЬ"):
            errors.append("Разрешены только запросы типа ВЫБРАТЬ")

        return len(errors) == 0, errors, warnings

    def sanitize_query(self, query_text: str) -> str:
        return query_text.strip()
