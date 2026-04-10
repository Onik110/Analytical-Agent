from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import re

def detect_date_range(user_query: str) -> Tuple[datetime, datetime]:
    query = user_query.strip().lower()
    now = datetime.now()

    # 1. Сегодня
    if re.search(r"\bсегодня\b", query):
        return now.replace(hour=0, minute=0, second=0), now.replace(hour=23, minute=59, second=59)

    # 2. Вчера
    if re.search(r"\bвчера\b", query):
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=0, minute=0, second=0), yesterday.replace(hour=23, minute=59, second=59)

    # 3. Месяц и год (например: "сентябрь 2024", "октябрь'24", "сентябрь-2024")
    month_map = {
        "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6,
        "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12
    }
    for root, num in month_map.items():
        pattern = rf"\b{root}[ья]?\s*['\-/]*\s*(20\d{{2}})\b"
        match = re.search(pattern, query)
        if match:
            year = int(match.group(1))
            start = datetime(year, num, 1)
            end = start + relativedelta(months=1) - timedelta(seconds=1)
            return start, end

    # 4. Только месяц без года → предполагаем текущий год (или следующий, если месяц уже прошёл)
    for root, num in month_map.items():
        if re.search(rf"\b{root}[ья]?\b", query):
            year = now.year
            if num < now.month and now.month > 6: 
                year += 1
            start = datetime(year, num, 1)
            end = start + relativedelta(months=1) - timedelta(seconds=1)
            return start, end

    # 5. Год целиком (например: "2024")
    year_match = re.search(r"\b(20\d{2})\b", query)
    if year_match and not re.search(r"\b\d{1,2}\s+[а-я]+\s+20\d{2}", query):  
        year = int(year_match.group(1))
        start = datetime(year, 1, 1)
        end = datetime(year, 12, 31, 23, 59, 59)
        return start, end

    # 6. Последние N дней
    last_n = re.search(r"последни[ея]\s+(\d+)\s+дн[еяй]", query)
    if last_n:
        days = int(last_n.group(1))
        end = now.replace(hour=23, minute=59, second=59)
        start = (end - timedelta(days=days-1)).replace(hour=0, minute=0, second=0)
        return start, end

    # По умолчанию — текущий месяц
    start = now.replace(day=1, hour=0, minute=0, second=0)
    end = (start + relativedelta(months=1)) - timedelta(seconds=1)
    return start, end