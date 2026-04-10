import json, pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from backend.services.llm_client import MistralAPIClient
from backend.config import PANDASAI_MAX_ROWS, ANONYMIZED_DATA_DIR

logger = logging.getLogger(__name__)

class SimpleInsightEngine:
    """
    Анализ данных через существующий Mistral-клиент
    """

    def __init__(self):
        self.llm = MistralAPIClient()
        self._anonymized_dir = Path(ANONYMIZED_DATA_DIR)
        logger.info("SimpleInsightEngine инициализирован (только анонимизированные данные)")

    def _validate_anonymized_file(self, file_path: str) -> bool:
        try:
            resolved = Path(file_path).resolve()
            anonymized_resolved = self._anonymized_dir.resolve()
            return str(resolved).startswith(str(anonymized_resolved))
        except Exception:
            return False

    def _df_to_context(self, df: pd.DataFrame, max_rows: int = 50) -> str:
        context = f"Данные: {len(df)} строк, {len(df.columns)} колонок.\n"
        context += f"Колонки: {', '.join(df.columns.tolist())}\n\n"
        context += f"Пример данных (первые 10 строк):\n"
        sample = df.head(10)
        context += " | ".join([str(col) for col in sample.columns]) + "\n"
        context += "-|-".join(["---" for _ in sample.columns]) + "\n"
        for _, row in sample.iterrows():
            context += " | ".join([str(val)[:50] for val in row.values]) + "\n"
        context += "\n"
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) > 0:
            context += "Статистика по числовым полям:\n"
            for col in numeric_cols:
                context += f"- {col}: мин={df[col].min():.2f}, макс={df[col].max():.2f}, среднее={df[col].mean():.2f}\n"
            context += "\n"
        categorical_cols = df.select_dtypes(include='object').columns
        if len(categorical_cols) > 0:
            context += "Уникальные значения в текстовых полях (топ-5):\n"
            for col in categorical_cols[:5]:
                unique_vals = df[col].dropna().unique()[:5]
                context += f"- {col}: {', '.join([str(v)[:30] for v in unique_vals])}\n"
        return context[:8000]

    def analyze_file(self, file_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self._validate_anonymized_file(file_path):
            logger.error(f"ОТКАЗ: Попытка анализа НЕанонимизированного файла: {file_path}")
            return {
                "success": False,
                "error": "Отказано в доступе: анализ разрешён только для анонимизированных данных",
                "rows_analyzed": 0,
                "columns": []
            }

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    df = pd.DataFrame(data.get('data', data) if isinstance(data, dict) else data)
            else:
                raise ValueError(f"Неподдерживаемый формат: {file_path}")

            if len(df) > PANDASAI_MAX_ROWS:
                df = df.head(PANDASAI_MAX_ROWS)

            context = self._df_to_context(df)
            if not prompt:
                prompt = "Проанализируй данные и представь ключевые факты и аномалии."

            full_prompt = f"Данные:\n{context}\n\nЗадача:\n{prompt}\n\nОтвет:"
            messages = [{"role": "user", "content": full_prompt}]
            insight = self.llm.chat_with_history(messages, temperature=0.3)

            logger.info(f"Анализ выполнен: {len(df)} строк из анонимизированного файла")
            return {"success": True, "insight": insight, "rows_analyzed": len(df), "columns": df.columns.tolist()}
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}", exc_info=True)
            return {"success": False, "error": f"Ошибка: {str(e)[:300]}", "rows_analyzed": 0, "columns": []}

# Глобальный инстанс
insight_engine = SimpleInsightEngine()
