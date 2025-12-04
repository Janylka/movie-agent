"""
OMDb-инструменты для кино-агента.

Используют публичный API OMDb:
http://www.omdbapi.com/

Здесь мы не делаем жёстких мэппингов русских названий на английские.
Если пользователь вводит русское название, OMDb сам попытается его понять.
"""

import os
from typing import Optional, Dict, Any

import requests

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_URL = "http://www.omdbapi.com/"


def safe_request(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправить GET-запрос к OMDb с базовой обработкой ошибок.

    Возвращает:
        Распарсенный JSON-словарь при успехе или None при любой ошибке.
    """
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # OMDb может вернуть {"Response": "False", "Error": "..."}
        if isinstance(data, dict) and data.get("Response") == "False":
            return None

        return data
    except Exception:
        return None


def _omdb_unavailable_message() -> str:
    """Сообщение пользователю, если OMDb API ключ не задан."""
    return "OMDb API ключ не найден. Укажи OMDB_API_KEY в .env."


def omdb_movie_info(title: str) -> str:
    """
    Получить подробную информацию о фильме из OMDb.
    """
    if not OMDB_API_KEY:
        return _omdb_unavailable_message()

    params = {"t": title, "apikey": OMDB_API_KEY, "plot": "full"}
    data = safe_request(OMDB_URL, params)

    if not data:
        return f"Фильм '{title}' не найден в OMDb."

    return (
        f"🎬 {data.get('Title')} ({data.get('Year')})\n"
        f"Режиссёр: {data.get('Director')}\n"
        f"Актёры: {data.get('Actors')}\n"
        f"Жанр: {data.get('Genre')}\n"
        f"Рейтинг IMDb: {data.get('imdbRating')}\n\n"
        f"Сюжет: {data.get('Plot')}"
    )


def omdb_movie_rating(title: str) -> str:
    """
    Получить рейтинг IMDb фильма из OMDb.
    """
    if not OMDB_API_KEY:
        return _omdb_unavailable_message()

    params = {"t": title, "apikey": OMDB_API_KEY}
    data = safe_request(OMDB_URL, params)

    if not data:
        return f"Рейтинг фильма '{title}' не найден в OMDb."

    return f"Рейтинг IMDb фильма '{data.get('Title')}' — {data.get('imdbRating')}"


def omdb_search(keyword: str, limit: int = 5) -> str:
    """
    Найти фильмы по ключевому слову через OMDb.
    """
    if not OMDB_API_KEY:
        return _omdb_unavailable_message()

    params = {"s": keyword, "apikey": OMDB_API_KEY}
    data = safe_request(OMDB_URL, params)

    if not data or "Search" not in data:
        return f"Нет фильмов по запросу '{keyword}' в OMDb."

    movies = data["Search"][:limit]
    lines = [f"{m['Title']} ({m['Year']})" for m in movies]
    return f"Результаты поиска OMDb по запросу '{keyword}':\n" + "\n".join(lines)
