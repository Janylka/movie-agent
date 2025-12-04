"""
Kaggle-инструменты для кино-агента.

Используют локальную SQLite-базу:
data/imdb_top_1000.db

Таблица: movies
Ожидается, что она создана скриптом build_kaggle_db.py
из CSV-файла IMDb Top 1000.

Здесь реализован ручной fuzzy matching:
- расстояние Левенштейна между названием фильма и запросом
- пересечение токенов в названии
- совпадения токенов в описании и метаданных
"""

import os
import sqlite3
from typing import List, Optional, Dict, Any

DATASET_DB_PATH = os.path.join("data", "imdb_top_1000.db")
TABLE_NAME = "movies"

if not os.path.exists(DATASET_DB_PATH):
    print(
        "⚠ ПРЕДУПРЕЖДЕНИЕ: SQLite-файл с датасетом не найден "
        "(ожидается data/imdb_top_1000.db). "
        "Инструменты Kaggle будут ограничены."
    )

# Кэш фильмов для fuzzy matching
_MOVIES_CACHE: List[Dict[str, Any]] = []
_MOVIES_CACHE_LOADED = False


def _get_connection() -> Optional[sqlite3.Connection]:
    """Вернуть подключение к SQLite, либо None, если база не найдена."""
    if not os.path.exists(DATASET_DB_PATH):
        return None
    return sqlite3.connect(DATASET_DB_PATH)


def _kaggle_unavailable_message() -> str:
    """Сообщение пользователю, когда база Kaggle недоступна."""
    return (
        "Данные Kaggle недоступны (файл data/imdb_top_1000.db не найден). "
        "Сначала создай базу через build_kaggle_db.py."
    )


def _normalize(text: str) -> str:
    """Нормализовать строку для поиска (обрезать и привести к нижнему регистру)."""
    return (text or "").strip().lower()


# ==========================
# Fuzzy matching helpers
# ==========================

def _levenshtein(a: str, b: str) -> int:
    """
    Ручная реализация расстояния Левенштейна.
    Используется для оценки похожести названий фильмов.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur_row = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = cur_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (0 if ca == cb else 1)
            cur_row.append(min(insert_cost, delete_cost, replace_cost))
        prev_row = cur_row
    return prev_row[-1]


def _load_movies_cache():
    """
    Загрузить в память список фильмов для fuzzy matching:
    - оригинальное название
    - нормализованное название
    - текст из overview + жанров + режиссёра + актёров
    """
    global _MOVIES_CACHE, _MOVIES_CACHE_LOADED

    if _MOVIES_CACHE_LOADED:
        return

    conn = _get_connection()
    if not conn:
        _MOVIES_CACHE = []
        _MOVIES_CACHE_LOADED = True
        return

    try:
        cur = conn.execute(
            f"""
            SELECT
                Series_Title,
                COALESCE(Overview, ''),
                COALESCE(Genre, ''),
                COALESCE(Director, ''),
                COALESCE(Star1, ''),
                COALESCE(Star2, ''),
                COALESCE(Star3, ''),
                COALESCE(Star4, '')
            FROM {TABLE_NAME}
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    cache: List[Dict[str, Any]] = []
    for row in rows:
        title = row[0] or ""
        overview = row[1] or ""
        meta_parts = [x for x in row[2:] if x]
        meta_text = " ".join(meta_parts)
        combined_meta = (overview + " " + meta_text).lower()

        cache.append(
            {
                "title": title,
                "title_norm": _normalize(title),
                "meta": combined_meta,
            }
        )

    _MOVIES_CACHE = cache
    _MOVIES_CACHE_LOADED = True


def _fuzzy_score(query_norm: str, item: Dict[str, Any]) -> float:
    """
    Посчитать гибридный скор похожести между запросом и фильмом:
    - базовый скор: 1 - (Левенштейн / max_len)
    - + бонус за пересечение токенов в названии
    - + небольшой бонус за вхождения токенов в метаданных (overview/жанры/актёры)
    """
    q = query_norm
    t = item["title_norm"]

    if not q or not t:
        return 0.0

    max_len = max(len(q), len(t))
    dist = _levenshtein(q, t)
    base = 1.0 - dist / max_len

    tokens_q = {tok for tok in q.split() if tok}
    tokens_t = {tok for tok in t.split() if tok}
    overlap = len(tokens_q & tokens_t)
    token_bonus = 0.1 * overlap

    meta = item["meta"]
    meta_hits = sum(1 for tok in tokens_q if tok and tok in meta)
    meta_bonus = 0.05 * meta_hits

    score = base + token_bonus + meta_bonus
    # ограничим сверху и снизу
    if score < 0.0:
        score = 0.0
    if score > 1.5:
        score = 1.5
    return score


def _fuzzy_find_best_title(query: str) -> Optional[str]:
    """
    Найти самое подходящее название фильма по запросу с помощью гибридного fuzzy matching.

    Возвращает:
        Строку с оригинальным названием фильма (как в датасете)
        или None, если подходящего совпадения нет.
    """
    _load_movies_cache()
    if not _MOVIES_CACHE:
        return None

    q_norm = _normalize(query)
    if not q_norm:
        return None

    best_title = None
    best_score = 0.0

    for item in _MOVIES_CACHE:
        score = _fuzzy_score(q_norm, item)
        if score > best_score:
            best_score = score
            best_title = item["title"]

    # Порог (эмпирически): если скор слишком низкий, считаем, что совпадений нет.
    if best_score < 0.6:
        return None

    return best_title


# ==========================
# Kaggle Tools
# ==========================

def kaggle_movie_info(title: str) -> str:
    """
    Вернуть форматированное описание фильма из SQLite-базы Kaggle.
    При необходимости использовать fuzzy matching для подбора названия.
    """
    conn = _get_connection()
    if not conn:
        return _kaggle_unavailable_message()

    norm = _normalize(title)

    # Сначала пробуем прямой LIKE-поиск по названию
    query_direct = f"""
        SELECT
            Series_Title,
            Released_Year,
            Genre,
            IMDB_Rating,
            Director,
            Star1, Star2, Star3, Star4,
            Overview
        FROM {TABLE_NAME}
        WHERE lower(Series_Title) LIKE ?
        LIMIT 1
    """

    try:
        cur = conn.execute(query_direct, (f"%{norm}%",))
        row = cur.fetchone()
    finally:
        conn.close()

    # Если прямой поиск ничего не дал — пробуем fuzzy matching
    if not row:
        best_title = _fuzzy_find_best_title(title)
        if not best_title:
            return f"Фильм '{title}' не найден в датасете IMDb Top 1000."

        conn = _get_connection()
        if not conn:
            return _kaggle_unavailable_message()
        try:
            cur = conn.execute(
                f"""
                SELECT
                    Series_Title,
                    Released_Year,
                    Genre,
                    IMDB_Rating,
                    Director,
                    Star1, Star2, Star3, Star4,
                    Overview
                FROM {TABLE_NAME}
                WHERE Series_Title = ?
                LIMIT 1
                """,
                (best_title,),
            )
            row = cur.fetchone()
        finally:
            conn.close()

    if not row:
        return f"Фильм '{title}' не найден в датасете IMDb Top 1000."

    series_title, year, genre, rating, director, star1, star2, star3, star4, overview = row

    actors_list: List[str] = []
    for val in (star1, star2, star3, star4):
        if isinstance(val, str) and val.strip():
            actors_list.append(val.strip())
    actors = ", ".join(actors_list) if actors_list else "—"

    return (
        f"🎬 {series_title} ({year})\n"
        f"Жанр: {genre}\n"
        f"Рейтинг IMDb: {rating}\n"
        f"Режиссёр: {director}\n"
        f"Актёры: {actors}\n\n"
        f"Описание: {overview}"
    )


def kaggle_movie_rating(title: str) -> str:
    """
    Вернуть рейтинг IMDb фильма из SQLite-базы Kaggle.
    При необходимости использовать fuzzy matching для подбора названия.
    """
    conn = _get_connection()
    if not conn:
        return _kaggle_unavailable_message()

    norm = _normalize(title)
    query_direct = f"""
        SELECT Series_Title, IMDB_Rating
        FROM {TABLE_NAME}
        WHERE lower(Series_Title) LIKE ?
        LIMIT 1
    """

    try:
        cur = conn.execute(query_direct, (f"%{norm}%",))
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        best_title = _fuzzy_find_best_title(title)
        if not best_title:
            return f"Рейтинг фильма '{title}' не найден в датасете IMDb Top 1000."

        conn = _get_connection()
        if not conn:
            return _kaggle_unavailable_message()

        try:
            cur = conn.execute(
                f"""
                SELECT Series_Title, IMDB_Rating
                FROM {TABLE_NAME}
                WHERE Series_Title = ?
                LIMIT 1
                """,
                (best_title,),
            )
            row = cur.fetchone()
        finally:
            conn.close()

    if not row:
        return f"Рейтинг фильма '{title}' не найден в датасете IMDb Top 1000."

    series_title, rating = row
    return f"Рейтинг IMDb фильма '{series_title}' — {rating}"


def kaggle_movies_with_actor(actor: str, limit: int = 5) -> str:
    """
    Вернуть список фильмов с указанным актёром из датасета Kaggle.
    """
    conn = _get_connection()
    if not conn:
        return _kaggle_unavailable_message()

    norm = _normalize(actor)
    query = f"""
        SELECT
            Series_Title,
            Released_Year,
            IMDB_Rating
        FROM {TABLE_NAME}
        WHERE
            lower(COALESCE(Star1, '')) LIKE ?
            OR lower(COALESCE(Star2, '')) LIKE ?
            OR lower(COALESCE(Star3, '')) LIKE ?
            OR lower(COALESCE(Star4, '')) LIKE ?
        ORDER BY IMDB_Rating DESC
        LIMIT ?
    """

    try:
        cur = conn.execute(query, (f"%{norm}%",) * 4 + (int(limit),))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return f"Фильмы с актёром '{actor}' не найдены в топ-1000."

    lines = [
        f"{title} ({year}) — рейтинг {rating}"
        for (title, year, rating) in rows
    ]
    return f"Фильмы с актёром '{actor}':\n" + "\n".join(lines)


def kaggle_top_by_genre(genre: str, limit: int = 5) -> str:
    """
    Вернуть топ фильмов по жанру из датасета Kaggle, отсортированных по рейтингу.
    """
    conn = _get_connection()
    if not conn:
        return _kaggle_unavailable_message()

    norm = _normalize(genre)
    query = f"""
        SELECT
            Series_Title,
            Released_Year,
            IMDB_Rating
        FROM {TABLE_NAME}
        WHERE lower(COALESCE(Genre, '')) LIKE ?
        ORDER BY IMDB_Rating DESC
        LIMIT ?
    """

    try:
        cur = conn.execute(query, (f"%{norm}%", int(limit)))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return f"Нет фильмов в жанре '{genre}' в датасете IMDb Top 1000."

    lines = [
        f"{title} ({year}) — {rating}"
        for (title, year, rating) in rows
    ]
    return f"Топ {limit} фильмов жанра '{genre}':\n" + "\n".join(lines)


def kaggle_search_by_keyword(keyword: str, limit: int = 5) -> str:
    """
    Найти фильмы по ключевому слову в описании (overview) из датасета Kaggle.
    """
    conn = _get_connection()
    if not conn:
        return _kaggle_unavailable_message()

    norm = _normalize(keyword)
    query = f"""
        SELECT
            Series_Title,
            Overview
        FROM {TABLE_NAME}
        WHERE lower(COALESCE(Overview, '')) LIKE ?
        LIMIT ?
    """

    try:
        cur = conn.execute(query, (f"%{norm}%", int(limit)))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return f"Нет фильмов, содержащих слово '{keyword}', в описании."

    lines = [
        f"{title} — {overview[:150]}..."
        for (title, overview) in rows
    ]
    return f"Фильмы по ключевому слову '{keyword}':\n" + "\n".join(lines)
