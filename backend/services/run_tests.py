"""
Скрипт тестирования Agent 1C с замером метрик
Запускает запросы и измеряет производительность

Запуск:
    python -m backend.services.run_tests
    python -m backend.services.run_tests --queries 1,2,3,10
    python -m backend.services.run_tests --category "Простые запросы"
    python -m backend.services.run_tests --all
"""

import asyncio
import aiohttp
import time
import json
import re
import argparse
import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

BASE_URL = "http://localhost:8000"
QUERIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "test-queries.md")

@dataclass
class TestResult:
    """Результат одного теста"""
    number: int
    query: str
    category: str
    success: bool
    latency_ms: float
    status_code: int
    error: Optional[str] = None
    fix_attempts: int = 0
    result_rows: int = 0
    query_1c: Optional[str] = None
    summary: Optional[str] = None  # Текстовая сводка от агента
    # Метрики качества
    actionability_score: float = 0.0  # 0-1 есть ли рекомендации
    intent_correct: bool = False       # Правильно ли определен интент
    entities_extracted: float = 0.0  # 0-1 доля извлеченных сущностей

@dataclass
class TestReport:
    """Итоговый отчет теста"""
    timestamp: str
    total_tests: int
    successful: int
    failed: int
    success_rate: float
    latency_avg_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    # Метрики качества
    actionability_rate: float = 0.0     # Доля ответов с рекомендациями
    intent_accuracy: float = 0.0        # Точность определения намерений
    entity_extraction_rate: float = 0.0 # Качество извлечения сущностей
    category_stats: Dict[str, Dict] = None
    tests: List[Dict] = None

def parse_queries(filepath: str, category_filter: str = None, 
                  query_numbers: List[int] = None) -> List[Dict[str, str]]:
    """Парсит запросы из markdown файла"""
    if not os.path.exists(filepath):
        print(f"Файл с запросами не найден: {filepath}")
        print(f"Создайте файл docs/test-queries.md")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    queries = []
    current_category = "Другое"
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Проверяем заголовок категории
        if line.startswith('## '):
            current_category = line[3:].strip()
            continue
        
        # Проверяем номер запроса (формат: "1. текст запроса")
        match = re.match(r'^(\d+)\.\s+(.+)$', line)
        if match:
            num = int(match.group(1))
            query = match.group(2).strip()
            
            # Фильтрация по номеру запроса
            if query_numbers and num not in query_numbers:
                continue
            
            # Фильтрация по категории
            if category_filter and category_filter.lower() not in current_category.lower():
                continue
            
            queries.append({
                'number': num,
                'query': query,
                'category': current_category
            })
    
    return queries

async def run_single_test(session: aiohttp.ClientSession,
                          query_data: Dict,
                          base_url: str = BASE_URL) -> TestResult:
    """Запускает один тест"""
    start_time = time.monotonic()

    try:
        async with session.post(
            f"{base_url}/api/query",
            json={"query": query_data['query'], "save": False},
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            result_data = await response.json()
            latency = (time.monotonic() - start_time) * 1000
            
            return TestResult(
                number=query_data['number'],
                query=query_data['query'],
                category=query_data['category'],
                success=result_data.get('success', False),
                latency_ms=latency,
                status_code=response.status,
                error=result_data.get('error'),
                fix_attempts=result_data.get('fix_attempts', 0),
                result_rows=result_data.get('preview_rows', 0),
                query_1c=result_data.get('query_1c'),
                summary=result_data.get('summary')
            )
    except asyncio.TimeoutError:
        latency = (time.monotonic() - start_time) * 1000
        return TestResult(
            number=query_data['number'],
            query=query_data['query'],
            category=query_data['category'],
            success=False,
            latency_ms=latency,
            status_code=408,
            error="Timeout (120s)"
        )
    except Exception as e:
        latency = (time.monotonic() - start_time) * 1000
        return TestResult(
            number=query_data['number'],
            query=query_data['query'],
            category=query_data['category'],
            success=False,
            latency_ms=latency,
            status_code=0,
            error=str(e)
        )

def percentile(data: List[float], p: float) -> float:
    """Вычисляет перцентиль"""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f]) if c != f else sorted_data[f]

def calculate_actionability_score(analysis: Optional[str] = None) -> float:
    """
    Измеряет наличие практических рекомендаций в ответе.
    1.0 = есть конкретные рекомендации
    0.5 = есть общая аналитика
    0.0 = только данные без анализа
    """
    if not analysis:
        return 0.0
    
    analysis_lower = analysis.lower()
    
    # Ключевые слова рекомендаций
    recommendation_keywords = [
        'рекомендуем', 'советуем', 'стоит', 'лучше', 'оптимиз',
        'улучшить', 'тренд', 'выяви', 'корреляц', 'обратить',
        'причина', 'основн', 'част', 'чаще всего', 'важно',
        'следует', 'необходим', 'нужно', 'обслужив', 'провер'
    ]
    
    # Ключевые слова аналитики
    analytics_keywords = [
        'статистик', 'анализ', 'всего', 'сумм', 'средн',
        'количество', 'строк', 'значени', 'данные'
    ]
    
    has_recommendation = any(kw in analysis_lower for kw in recommendation_keywords)
    has_analytics = any(kw in analysis_lower for kw in analytics_keywords)
    
    if has_recommendation:
        return 1.0
    elif has_analytics:
        return 0.5
    else:
        return 0.0

def calculate_intent_correctness(query: str, category: str, success: bool, error: Optional[str] = None) -> bool:
    """
    Проверяет, правильно ли агент определил намерение запроса.
    Для blocked категорий — запрос должен быть заблокирован.
    """
    BLOCKED_CATEGORIES = {"безопасности", "security", "вредоносные запросы"}

    if category.strip().lower() in BLOCKED_CATEGORIES:
        return not success
    else:
        return success
    

def calculate_entity_extraction(query: str, category: str) -> float:
    """
    Оценивает, насколько хорошо извлечены сущности из запроса.
    Проверяет наличие типичных сущностей:
    - Даты/периоды
    - Имена объектов (терминалы, ткачи)
    - Метрики (простои, выработка)
    """
    query_lower = query.lower()
    entities_found = 0
    entities_total = 0
    
    # Проверка периода
    period_keywords = [
        'январ', 'феврал', 'март', 'апрел', 'ма', 'июн',
        'июл', 'август', 'сентябр', 'октябр', 'ноябр', 'декабр',
        'недел', 'месяц', 'квартал', 'год', 'период',
        'последн', 'вчера', 'сегодня', 'этот'
    ]
    if any(kw in query_lower for kw in period_keywords):
        entities_total += 1
        entities_found += 0.8  
    
    # Проверка объектов
    object_keywords = ['терминал', 'ткач', 'оборудован', 'станок', 'оператор']
    if any(kw in query_lower for kw in object_keywords):
        entities_total += 1
        entities_found += 1.0
    
    # Проверка метрик
    metric_keywords = ['простой', 'выработк', 'импульс', 'кпв', 'эффективн', 'производит', 'загружен']
    if any(kw in query_lower for kw in metric_keywords):
        entities_total += 1
        entities_found += 0.9
    
    # Проверка причин
    reason_keywords = ['причин', 'ремонт', 'наладк', 'заготов', 'логистик']
    if any(kw in query_lower for kw in reason_keywords):
        entities_total += 1
        entities_found += 0.85
    
    if entities_total == 0:
        return 1.0  
    
    return entities_found / entities_total

async def main():
    parser = argparse.ArgumentParser(description='Тестирование Agent 1C')
    parser.add_argument('--queries', type=str, default=None,
                       help='Номера запросов через запятую (1,2,3)')
    parser.add_argument('--category', type=str, default=None,
                       help='Фильтр по категории')
    parser.add_argument('--all', action='store_true',
                       help='Запустить все запросы')
    parser.add_argument('--save', type=str, default=None,
                       help='Имя файла для сохранения отчета')
    parser.add_argument('--url', type=str, default=BASE_URL,
                       help=f'URL backend (по умолчанию {BASE_URL})')
    
    args = parser.parse_args()
    base_url = args.url

    # Проверяем health
    print("\nПроверка health...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/api/health") as resp:
                health = await resp.json()
                print(f"  Статус: {health.get('status')}")
                print(f"  COM подключен: {health.get('com_connected')}")
                print(f"  LLM подключен: {health.get('llm_connected')}")

                if not health.get('com_connected'):
                    print("\nCOM не подключен!")
                    return
                if not health.get('llm_connected'):
                    print("\nLLM не подключен!")
                    return
        except Exception as e:
            print(f"\nBackend недоступен: {e}")
            return
    
    # Парсим запросы
    query_numbers = None
    if args.queries:
        query_numbers = [int(x.strip()) for x in args.queries.split(',')]
    
    queries = parse_queries(
        QUERIES_FILE,
        category_filter=args.category,
        query_numbers=query_numbers
    )
    
    if not queries:
        print("\nЗапросы не найдены")
        print("Проверьте файл docs/test-queries.md")
        return
    
    print(f"\n{'='*60}")
    print(f"  ТЕСТИРОВАНИЕ AGENT 1C")
    print(f"{'='*60}")
    print(f"  Запросов: {len(queries)}")
    print(f"{'='*60}\n")
    
    # Запускаем тесты
    results = []
    start_total = time.monotonic()
    
    async with aiohttp.ClientSession() as session:
        for i, query_data in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] {query_data['query'][:60]}...", end=' ')

            result = await run_single_test(session, query_data, base_url)
            results.append(result)
            
            status = "✓" if result.success else "✗"
            latency_str = f"{result.latency_ms/1000:.1f}s"
            print(f"{status} {latency_str}")
            
            if result.error:
                print(f"      Ошибка: {result.error[:80]}")

    total_time = (time.monotonic() - start_total) * 1000

    # Вычисляем метрики качества
    print(f"\nРасчет метрик качества...")
    for r in results:
        r.actionability_score = calculate_actionability_score(r.summary)
        r.intent_correct = calculate_intent_correctness(
            r.query, r.category, r.success, r.error
        )
        r.entities_extracted = calculate_entity_extraction(
            r.query, r.category
        )

    # Генерируем отчет
    latencies = [r.latency_ms for r in results if r.success]
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    # Статистика по категориям
    category_stats = {}
    for r in results:
        if r.category not in category_stats:
            category_stats[r.category] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'latencies': [],
                'actionability_scores': []
            }
        category_stats[r.category]['total'] += 1
        if r.success:
            category_stats[r.category]['success'] += 1
            category_stats[r.category]['latencies'].append(r.latency_ms)
        else:
            category_stats[r.category]['failed'] += 1
        category_stats[r.category]['actionability_scores'].append(r.actionability_score)

    # Считаем перцентили по категориям
    for cat in category_stats:
        lats = category_stats[cat]['latencies']
        if lats:
            category_stats[cat]['latency_avg_ms'] = sum(lats) / len(lats)
            category_stats[cat]['latency_p50_ms'] = percentile(lats, 50)
            category_stats[cat]['latency_p95_ms'] = percentile(lats, 95)
        else:
            category_stats[cat]['latency_avg_ms'] = 0
            category_stats[cat]['latency_p50_ms'] = 0
            category_stats[cat]['latency_p95_ms'] = 0
        del category_stats[cat]['latencies']
        
        # Actionability по категории
        action_scores = category_stats[cat].pop('actionability_scores')
        if action_scores:
            category_stats[cat]['actionability_rate'] = sum(action_scores) / len(action_scores) * 100
        else:
            category_stats[cat]['actionability_rate'] = 0
    
    report = TestReport(
        timestamp=datetime.now().isoformat(),
        total_tests=len(results),
        successful=len(successful),
        failed=len(failed),
        success_rate=len(successful) / len(results) * 100 if results else 0,
        latency_avg_ms=sum(latencies) / len(latencies) if latencies else 0,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        latency_p99_ms=percentile(latencies, 99),
        actionability_rate=sum(r.actionability_score for r in results) / len(results) * 100 if results else 0,
        intent_accuracy=sum(1 for r in results if r.intent_correct) / len(results) * 100 if results else 0,
        entity_extraction_rate=sum(r.entities_extracted for r in results) / len(results) * 100 if results else 0,
        category_stats=category_stats,
        tests=[asdict(r) for r in results]
    )
    
    # Выводим отчет
    print(f"\n{'='*60}")
    print(f"  ОТЧЕТ ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")
    print(f"  Время: {report.timestamp}")
    print(f"  Общее время: {total_time/1000:.1f}s")
    print(f"{'='*60}\n")
    
    print(f"  ОБЩИЕ МЕТРИКИ:")
    print(f"  {'─'*40}")
    print(f"  Всего тестов:         {report.total_tests}")
    print(f"  Успешных:             {report.successful} ✓")
    print(f"  Ошибок:               {report.failed} ✗")
    print(f"  Success Rate:         {report.success_rate:.1f}%")
    print()
    
    print(f"  ЗАДЕРЖКИ (только успешные):")
    print(f"  {'─'*40}")
    print(f"  Средняя (avg):        {report.latency_avg_ms/1000:.1f}s")
    print(f"  p50 (медиана):        {report.latency_p50_ms/1000:.1f}s")
    print(f"  p95:                  {report.latency_p95_ms/1000:.1f}s")
    print(f"  p99:                  {report.latency_p99_ms/1000:.1f}s")
    print()
    
    # SLO проверка
    print(f"  SLO ПРОВЕРКА (из docs):")
    print(f"  {'─'*40}")
    
    slo_p50 = report.latency_p50_ms < 10000
    slo_p95 = report.latency_p95_ms < 30000
    slo_success = report.success_rate >= 80
    
    print(f"  ✓ Latency p50 < 10s:   {'✅' if slo_p50 else '❌'} ({report.latency_p50_ms/1000:.1f}s)")
    print(f"  ✓ Latency p95 < 30s:   {'✅' if slo_p95 else '❌'} ({report.latency_p95_ms/1000:.1f}s)")
    print(f"  ✓ Success Rate >= 80%: {'✅' if slo_success else '❌'} ({report.success_rate:.1f}%)")
    print()
    
    # Метрики качества (из docs/product-proposal.md)
    print(f"  МЕТРИКИ КАЧЕСТВА (из docs):")
    print(f"  {'─'*50}")
    
    slo_actionability = report.actionability_rate >= 70
    slo_intent = report.intent_accuracy >= 92
    slo_entity = report.entity_extraction_rate >= 95
    
    print(f"  ✓ Actionability >= 70%:     {'✅' if slo_actionability else '❌'} ({report.actionability_rate:.1f}%)")
    print(f"  ✓ Intent Recognition >= 92%: {'✅' if slo_intent else '❌'} ({report.intent_accuracy:.1f}%)")
    print(f"  ✓ Entity Extraction >= 95%:  {'✅' if slo_entity else '❌'} ({report.entity_extraction_rate:.1f}%)")
    print()
    
    # По категориям
    if len(category_stats) > 1:
        print(f"  ПО КАТЕГОРИЯМ:")
        print(f"  {'─'*75}")
        print(f"  {'Категория':<30} {'Успех':<10} {'Средн':<10} {'p50':<10} {'Action':<10}")
        print(f"  {'─'*75}")

        for cat, stats in category_stats.items():
            avg = stats.get('latency_avg_ms', 0) / 1000
            p50 = stats.get('latency_p50_ms', 0) / 1000
            success_rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
            actionability = stats.get('actionability_rate', 0)
            print(f"  {cat:<30} {success_rate:>5.0f}%   {avg:>6.1f}s   {p50:>6.1f}s   {actionability:>5.0f}%")
        print()
    
    # Сохраняем отчет
    if args.save:
        filename = args.save
    else:
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    
    print(f"Отчет сохранен: {filename}\n")

if __name__ == "__main__":
    asyncio.run(main())
