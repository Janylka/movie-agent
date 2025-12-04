"""
Реестр инструментов для кино-агента.

Импортирует конкретные реализации из:
- tools_kaggle
- tools_omdb

и предоставляет единый словарь TOOLS, который использует агент.
"""

from tools_kaggle import (
    kaggle_movie_info,
    kaggle_movie_rating,
    kaggle_movies_with_actor,
    kaggle_top_by_genre,
    kaggle_search_by_keyword,
)
from tools_omdb import (
    omdb_movie_info,
    omdb_movie_rating,
    omdb_search,
)


TOOLS = {
    # Kaggle-инструменты
    "kaggle_movie_info": kaggle_movie_info,
    "kaggle_movie_rating": kaggle_movie_rating,
    "kaggle_movies_with_actor": kaggle_movies_with_actor,
    "kaggle_top_by_genre": kaggle_top_by_genre,
    "kaggle_search_by_keyword": kaggle_search_by_keyword,

    # OMDb-инструменты
    "omdb_movie_info": omdb_movie_info,
    "omdb_movie_rating": omdb_movie_rating,
    "omdb_search": omdb_search,
}
