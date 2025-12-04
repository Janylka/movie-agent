"""
Модуль памяти для кино-агента.

Функции:
- хранение истории диалога (user/assistant)
- хранение профиля пользователя (имя, предпочтения)
- простые ответы напрямую из памяти (имя, что любит, какие жанры любит)
- базовая обработка опечаток (например, «я люлблю боевики»)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

MEMORY_FILE = "memory_store.json"
MAX_HISTORY = 100  # максимальное количество сообщений в истории


COMMON_CORRECTIONS = {
    # Частые опечатки → исправленные варианты
    "люлблю": "люблю",
    "люблбю": "люблю",
    "научные фантастики": "научную фантастику",
}


@dataclass
class Message:
    role: str   # user, assistant
    content: str


@dataclass
class Memory:
    history: List[Message] = field(default_factory=list)
    profile: Dict[str, Any] = field(default_factory=lambda: {
        "name": None,
        "genres": [],
        "actors": [],
        "directors": [],
        "movies": []
    })

    def __post_init__(self):
        self._load()

    # ====================================
    # FILE I/O
    # ====================================

    def _load(self):
        """Загрузить память из файла, если он существует."""
        if not os.path.exists(MEMORY_FILE):
            return

        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.profile = data.get("profile", self.profile)
            loaded_history = data.get("history", [])
            self.history = [Message(**m) for m in loaded_history]
        except Exception:
            # Если файл битый, просто игнорируем
            pass

    def _save(self):
        """Сохранить память в файл."""
        data = {
            "profile": self.profile,
            "history": [m.__dict__ for m in self.history]
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ====================================
    # HISTORY
    # ====================================

    def add(self, role: str, content: str):
        """
        Добавить новое сообщение в историю.

        Сохраняем только роли user/assistant,
        сообщения tool нас здесь не интересуют.
        """
        if role not in ("user", "assistant"):
            return
        self.history.append(Message(role=role, content=content))

        # Ограничиваем размер истории
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        self._save()

    # ====================================
    # UPDATE PROFILE
    # ====================================

    def update_from_user_text(self, text: str):
        """
        Обновить профиль пользователя на основе текста:
        - имя
        - жанры
        - актёры
        - режиссёры
        - любимые фильмы
        """

        # Сначала мягко исправляем наиболее частые опечатки
        clean = text
        for wrong, correct in COMMON_CORRECTIONS.items():
            clean = re.sub(wrong, correct, clean, flags=re.IGNORECASE)

        txt = clean.strip()
        low = txt.lower()

        # ---- ИМЯ ----
        name_match = re.search(
            r"меня зовут\s+([A-Za-zА-Яа-яЁёІіӨөҮүЩщ\-]+)",
            txt,
            re.IGNORECASE
        )
        if name_match:
            self.profile["name"] = name_match.group(1).strip()
            self._save()

        # Дополнительный простой хак: если пользователь упомянул Джеки Чана — добавим в актёры
        if "джеки чан" in low or "jackie chan" in low:
            self._append_unique("actors", "Джеки Чан")

        # ---- РЕЖИССЁРЫ: "я люблю фильмы Нолана" ----
        directors_matches = re.findall(
            r"я люблю фильмы\s+([A-Za-zА-Яа-яЁёІіӨөҮүЩщ \-]+)",
            low,
            re.IGNORECASE
        )
        for dm in directors_matches:
            name = dm.strip()
            if name:
                # Нормализуем: "нолана" → "Нолан"
                name_norm = name.capitalize()
                self._append_unique("directors", name_norm)

        # Удаляем фрагменты "я люблю фильмы ..." из текста, чтобы они не превратились в жанры
        low_for_genres = re.sub(
            r"я люблю фильмы\s+[A-Za-zА-Яа-яЁёІіӨөҮүЩщ \-]+",
            "",
            low,
            flags=re.IGNORECASE
        )

        # ---- ЖАНРЫ ----
        # пример: "я люблю научную фантастику", "я люблю боевики, фэнтези"
        g = re.findall(
            r"я люблю\s+([A-Za-zА-Яа-яЁёІіӨөҮүЩщ ,]+)",
            low_for_genres,
            re.IGNORECASE
        )
        for grp in g:
            for piece in grp.split(","):
                p = piece.strip()
                # убираем слово "тоже", если оно прилипло
                p = re.sub(r"\bтоже\b", "", p, flags=re.IGNORECASE).strip()
                if p:
                    self._append_unique("genres", p)

        # ---- ФИЛЬМЫ ----
        # пример: "мне нравится фильм Интерстеллар"
        mv = re.findall(
            r"фильм\s+([A-Za-zА-Яа-яЁёІіӨөҮүЩщ \-]+)",
            txt,
            re.IGNORECASE
        )
        for mv1 in mv:
            title = mv1.strip()
            if title:
                self._append_unique("movies", title)

        self._save()

    # ====================================
    # HELPERS
    # ====================================

    def _append_unique(self, key: str, value: str):
        """Добавить значение в список профиля, если его там ещё нет (без учёта регистра)."""
        arr = self.profile.get(key, [])
        if value.lower() not in {x.lower() for x in arr}:
            arr.append(value)
        self.profile[key] = arr

    @property
    def user_name(self):
        """Удобное свойство для доступа к имени пользователя."""
        return self.profile.get("name")

    def get_preferences_text(self) -> Optional[str]:
        """
        Вернуть человекочитаемое описание предпочтений пользователя
        или None, если данных ещё нет.
        """
        result = []

        if self.profile["genres"]:
            result.append("любимые жанры: " + ", ".join(self.profile["genres"]))
        if self.profile["actors"]:
            result.append("любимые актёры: " + ", ".join(self.profile["actors"]))
        if self.profile["directors"]:
            result.append("любимые режиссёры: " + ", ".join(self.profile["directors"]))
        if self.profile["movies"]:
            result.append("любимые фильмы: " + ", ".join(self.profile["movies"]))

        if not result:
            return None

        return "У пользователя " + "; ".join(result) + "."


# ====================================
# DIRECT MEMORY ANSWERS
# ====================================

def answer_from_memory_if_applicable(user_text: str, memory: Memory):
    """
    Попробовать ответить прямо из памяти без обращения к LLM:
    - "Как меня зовут?"
    - "Что я люблю?"
    - "Какие жанры я люблю?"
    """
    low = user_text.lower()

    if "как меня зовут" in low:
        if memory.user_name:
            return f"Тебя зовут {memory.user_name}."
        return "Я ещё не знаю, как тебя зовут."

    if "какие жанры я люблю" in low:
        genres = memory.profile.get("genres") or []
        if genres:
            return "Ты любишь " + ", ".join(genres) + "."
        return "Я пока не знаю, какие жанры ты любишь."

    if "что я люблю" in low:
        prefs = memory.get_preferences_text()
        return prefs or "Ты пока не рассказала, что ты любишь."

    return None
