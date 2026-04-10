import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

from backend.config import RAW_DATA_DIR, ANONYMIZED_DATA_DIR, CHARTS_DIR, FILE_TTL_DAYS

logger = logging.getLogger(__name__)

class FileStorage:
    """Управление файлами данных с разделением raw/anonymized"""

    def __init__(self):
        self.raw_dir = Path(RAW_DATA_DIR)
        self.anon_dir = Path(ANONYMIZED_DATA_DIR)
        self.charts_dir = Path(CHARTS_DIR)

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.anon_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"FileStorage инициализирован: raw={self.raw_dir}, anon={self.anon_dir}")

    def save_result(self, query: str, data: List[Dict], anonymized_data: List[Dict]) -> Dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"query_{timestamp}"

        try:
            self._save_json(self.raw_dir / f"{file_id}.json", {
                "query": query, "timestamp": timestamp, "rows": len(data), "data": data
            })
            self._save_csv(self.raw_dir / f"{file_id}.csv", data)

            self._save_json(self.anon_dir / f"{file_id}.json", {
                "query": query, "timestamp": timestamp, "rows": len(anonymized_data), "data": anonymized_data
            })
            self._save_csv(self.anon_dir / f"{file_id}.csv", anonymized_data)

            logger.info(f"Файл сохранён: {file_id} ({len(data)} строк)")

            return {
                "file_id": file_id, "timestamp": timestamp,
                "raw_rows": len(data), "anonymized_rows": len(anonymized_data),
                "created_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            raise

    def list_files(self, anonymized_only: bool = True) -> List[Dict]:
        directory = self.anon_dir if anonymized_only else self.raw_dir
        files = []

        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    files.append({
                        "file_id": file_path.stem,
                        "timestamp": meta.get("timestamp", ""),
                        "query": meta.get("query", "")[:100],
                        "rows": meta.get("rows", 0),
                        "created_at": meta.get("created_at", datetime.fromtimestamp(file_path.stat().st_ctime).isoformat())
                    })
            except Exception as e:
                logger.warning(f"Не удалось прочитать файл {file_path}: {e}")

        files.sort(key=lambda x: x["created_at"], reverse=True)
        return files

    def get_file_path(self, file_id: str, anonymized_only: bool = True) -> Optional[Path]:
        directory = self.anon_dir if anonymized_only else self.raw_dir
        json_path = directory / f"{file_id}.json"
        csv_path = directory / f"{file_id}.csv"
        return json_path if json_path.exists() else (csv_path if csv_path.exists() else None)

    def cleanup_old_files(self, days: int = None) -> int:
        days = days or FILE_TTL_DAYS
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for directory in [self.raw_dir, self.anon_dir, self.charts_dir]:
            for file_path in directory.glob("*"):
                if file_path.is_file() and datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
                    file_path.unlink()
                    deleted += 1
                    logger.info(f"Удалён старый файл: {file_path.name}")
        return deleted

    def _save_json(self, path: Path, data: Dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_csv(self, path: Path, data: List[Dict]):
        if not data: return
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

# Глобальный инстанс
storage = FileStorage()
