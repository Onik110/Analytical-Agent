import re
from typing import List, Dict, Tuple

class DataAnonymizer:
    """Анонимизация персональных данных для защиты ПнД"""

    def __init__(self):
        self.fio_map = {}
        self.term_map = {}
        self.vrc_map = {}
        self.reason_map = {}
        self.equip_map = {}
        self.machine_map = {}

        self.fio_counter = 1
        self.term_counter = 1
        self.vrc_counter = 1
        self.reason_counter = 1
        self.equip_counter = 1
        self.machine_counter = 1

    def anonymize_row(self, row: Dict[str, str]) -> Dict[str, str]:
        anon_row = row.copy()

        if 'Ткач' in anon_row and anon_row['Ткач']:
            fio = anon_row['Ткач'].strip()
            if fio and fio not in self.fio_map:
                self.fio_map[fio] = f"Ткач #{self.fio_counter}"
                self.fio_counter += 1
            anon_row['Ткач'] = self.fio_map[fio]

        for key in ['Терминал']:
            if key in anon_row and anon_row[key]:
                term = anon_row[key].strip()
                if term and term not in self.term_map:
                    self.term_map[term] = f"Терминал #{self.term_counter}"
                    self.term_counter += 1
                anon_row[key] = self.term_map[term]

        if 'ВРЦ' in anon_row and anon_row['ВРЦ']:
            vrc = anon_row['ВРЦ'].strip()
            if vrc and vrc not in self.vrc_map:
                self.vrc_map[vrc] = f"ВРЦ #{self.vrc_counter}"
                self.vrc_counter += 1
            anon_row['ВРЦ'] = self.vrc_map[vrc]

        for key in ['ПричинаПростоя']:
            if key in anon_row and anon_row[key]:
                reason = anon_row[key].strip()
                if reason and reason not in self.reason_map:
                    self.reason_map[reason] = f"Причина #{self.reason_counter}"
                    self.reason_counter += 1
                anon_row[key] = self.reason_map[reason]

        for key in ['Оборудование']:
            if key in anon_row and anon_row[key]:
                equip = anon_row[key].strip()
                if equip and equip not in self.equip_map:
                    self.equip_map[equip] = f"Оборудование #{self.equip_counter}"
                    self.equip_counter += 1
                anon_row[key] = self.equip_map[equip]

        for key in ['Станок']:
            if key in anon_row and anon_row[key]:
                machine = anon_row[key].strip()
                if machine and machine not in self.machine_map:
                    self.machine_map[machine] = f"Станок #{self.machine_counter}"
                    self.machine_counter += 1
                anon_row[key] = self.machine_map[machine]

        return anon_row

    def anonymize_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return [self.anonymize_row(row) for row in data]

    def sanitize_user_query(self, query: str) -> Tuple[str, List[str]]:
        fio_pattern = r'\b([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})\b'
        matches = re.findall(fio_pattern, query)

        cleaned_query = query
        found_fio = []

        for fio in matches:
            if len(fio.split()) in [2, 3]:
                found_fio.append(fio)
                cleaned_query = cleaned_query.replace(fio, "[ФИО_ТКАЧА]")

        equip_pattern = r'([А-ЯA-Z]{2,}[\-–—]?\d+[А-ЯA-Z]?)'
        equip_matches = re.findall(equip_pattern, cleaned_query)
        for eq in equip_matches:
            cleaned_query = cleaned_query.replace(eq, "[ОБОРУДОВАНИЕ]")

        return cleaned_query, found_fio

    def get_mapping_summary(self) -> str:
        lines = []
        if self.fio_map:
            lines.append("Ткачи:")
            for real, anon in self.fio_map.items():
                lines.append(f"  {real} → {anon}")
        if self.term_map:
            lines.append("\nТерминалы:")
            for real, anon in self.term_map.items():
                lines.append(f"  {real} → {anon}")
        if self.vrc_map:
            lines.append("\nВРЦ:")
            for real, anon in self.vrc_map.items():
                lines.append(f"  {real} → {anon}")
        if self.reason_map:
            lines.append("\nПричины простоя:")
            for real, anon in self.reason_map.items():
                lines.append(f"  {real} → {anon}")
        if self.equip_map:
            lines.append("\nОборудование:")
            for real, anon in self.equip_map.items():
                lines.append(f"  {real} → {anon}")
        if self.machine_map:
            lines.append("\nСтанки:")
            for real, anon in self.machine_map.items():
                lines.append(f"  {real} → {anon}")
        return "\n".join(lines) if lines else "Маппинг пуст"
