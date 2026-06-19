"""
Модуль загрузки и поиска по аварским словарям.
Загружает JSONL файлы в память при старте и предоставляет функции поиска.
"""

import json
import random
import os
from pathlib import Path
from typing import Optional


def get_first_letter(word: str) -> str:
    """Извлекает первую букву, учитывая аварские диграфы."""
    if not word:
        return ""
    word = word.strip().upper()
    # Нормализация палочки
    word = word.replace("I", "Ӏ").replace("1", "Ӏ").replace("L", "Ӏ")
    if len(word) >= 2:
        second = word[1]
        if second in ("Ъ", "Ь", "Ӏ"):
            return word[0:2]
    return word[0]


def normalize_for_search(word: str) -> str:
    """Нормализует слово для гибкого поиска (палочка, ё->е)."""
    if not word:
        return ""
    w = word.lower().strip()
    
    # 1. Замена ё на е
    w = w.replace('ё', 'е')
    
    # 2. Нормализация всех видов 'палочки' к единому символу '1'
    # Используются: '!', 'l' (латинская L), 'i' (латинская I), 'і' (укр/белорус), 'ӏ', 'Ӏ'
    for p in ['!', 'l', 'i', 'і', 'ӏ', 'Ӏ']:
        w = w.replace(p, '1')
        
    return w


class Dictionary:
    """Класс для работы с двуязычным словарём (один JSONL файл)."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.entries: list[dict] = []
        self.word_index: dict[str, list[int]] = {}  # word -> list of entry indices
        self.letters_index: dict[str, list[int]] = {} # letter -> list of entry indices
        self._load()

    def _load(self):
        """Загрузить JSONL файл в память и построить индекс."""
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    idx = len(self.entries)
                    self.entries.append(entry)

                    word = entry.get("word", "")
                    if word:
                        norm_word = normalize_for_search(word)
                        if norm_word not in self.word_index:
                            self.word_index[norm_word] = []
                        self.word_index[norm_word].append(idx)
                        
                        letter = get_first_letter(word)
                        if letter:
                            if letter not in self.letters_index:
                                self.letters_index[letter] = []
                            self.letters_index[letter].append(idx)
                except json.JSONDecodeError:
                    continue

        print(f"Загружено {len(self.entries)} записей из {self.filepath}")

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """
        Поиск по словарю. Сначала точное совпадение, затем по префиксу,
        затем подстрока.
        """
        query_norm = normalize_for_search(query)
        if not query_norm:
            return []

        results = []
        seen_indices = set()

        # 1. Точное совпадение
        if query_norm in self.word_index:
            for idx in self.word_index[query_norm]:
                if idx not in seen_indices:
                    results.append(self.entries[idx])
                    seen_indices.add(idx)

        # 2. Префиксный поиск
        if len(results) < limit:
            for word_norm, indices in self.word_index.items():
                if word_norm.startswith(query_norm) and word_norm != query_norm:
                    for idx in indices:
                        if idx not in seen_indices:
                            results.append(self.entries[idx])
                            seen_indices.add(idx)
                            if len(results) >= limit:
                                break
                if len(results) >= limit:
                    break

        # 3. Поиск по подстроке (если мало результатов)
        if len(results) < limit and len(query_norm) >= 3:
            for word_norm, indices in self.word_index.items():
                if query_norm in word_norm and not word_norm.startswith(query_norm):
                    for idx in indices:
                        if idx not in seen_indices:
                            results.append(self.entries[idx])
                            seen_indices.add(idx)
                            if len(results) >= limit:
                                break
                if len(results) >= limit:
                    break

        return results[:limit]

    def get_word(self, word: str) -> list[dict]:
        """Получить словарную статью по точному совпадению слова."""
        word_norm = normalize_for_search(word)
        if word_norm in self.word_index:
            return [self.entries[idx] for idx in self.word_index[word_norm]]
        return []

    def get_alphabet(self) -> list[dict]:
        """Получить список букв и количество слов."""
        return [{"letter": k, "count": len(v)} for k, v in sorted(self.letters_index.items())]

    def get_words_by_letter(self, letter: str) -> list[dict]:
        """Получить все слова на заданную букву."""
        letter = letter.upper()
        if letter in self.letters_index:
            return [self.entries[idx] for idx in self.letters_index[letter]]
        return []

    def get_random(self) -> dict:
        """Получить случайную запись из словаря."""
        return random.choice(self.entries)

    def get_random_with_examples(self) -> dict:
        """
        Получить случайную запись, у которой есть примеры использования.
        Идеально для 'слова дня'.
        """
        candidates = [
            entry for entry in self.entries
            if any(
                example
                for sense in entry.get("senses", [])
                for example in sense.get("examples", [])
            )
            and entry.get("pos") not in ("выражение",)
        ]
        if candidates:
            return random.choice(candidates)
        return self.get_random()


class DictionaryManager:
    """Менеджер словарей — загружает оба словаря и предоставляет единый интерфейс."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # По умолчанию ищем словари в корне проекта
            data_dir = str(Path(__file__).parent.parent)

        self.data_dir = data_dir
        self.dictionaries: dict[str, Dictionary] = {}
        self._load_all()

    def _load_all(self):
        """Загрузить все доступные словари."""
        av_ru_path = os.path.join(self.data_dir, "av-ru.jsonl")
        ru_av_path = os.path.join(self.data_dir, "ru-av.jsonl")

        if os.path.exists(av_ru_path):
            self.dictionaries["av-ru"] = Dictionary(av_ru_path)
        else:
            print(f"ВНИМАНИЕ: файл {av_ru_path} не найден!")

        if os.path.exists(ru_av_path):
            self.dictionaries["ru-av"] = Dictionary(ru_av_path)
        else:
            print(f"ВНИМАНИЕ: файл {ru_av_path} не найден!")

    def get_dict(self, name: str) -> Optional[Dictionary]:
        """Получить словарь по имени."""
        return self.dictionaries.get(name)

    def search(self, query: str, dict_name: str = "av-ru", limit: int = 50) -> list[dict]:
        d = self.get_dict(dict_name)
        if d is None:
            return []
        return d.search(query, limit)

    def get_word(self, word: str, dict_name: str = "av-ru") -> list[dict]:
        d = self.get_dict(dict_name)
        if d is None:
            return []
        return d.get_word(word)

    def get_random(self, dict_name: str = "av-ru") -> Optional[dict]:
        d = self.get_dict(dict_name)
        if d is None:
            return None
        return d.get_random_with_examples()

    def get_alphabet(self, dict_name: str = "av-ru") -> list[dict]:
        d = self.get_dict(dict_name)
        if d is None:
            return []
        return d.get_alphabet()

    def get_words_by_letter(self, letter: str, dict_name: str = "av-ru") -> list[dict]:
        d = self.get_dict(dict_name)
        if d is None:
            return []
        return d.get_words_by_letter(letter)
