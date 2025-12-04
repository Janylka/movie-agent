# 🎬 MovieAgent — Custom LLM Agent Framework (Variant 3)

This project implements a fully custom movie assistant agent using **OpenAI function calling** and a **completely self-built agent loop** (Variant 3 of the assignment).  
No LangChain agent executors, no LangChain memory — everything is implemented manually.

The agent can:
- 🔍 Search films  
- 📚 Retrieve detailed information  
- 🎯 Recommend movies  
- ⚖️ Compare movies  
- 🗄️ Use multiple data sources (SQLite + OMDb API)  
- 🧠 Remember user preferences  
- 🔧 Perform multi-step tool calling  
- 🧩 Produce structured reasoning in the final answer  
- ✨ Tolerate minor typos and fuzzy movie title matching (for English titles)

All agent responses are in **Russian**, as required.

---

## ⭐ Key Features

### ✔ Fully Custom Agent Framework (Variant 3)
- Custom **agent loop**
- Custom **memory**
- Custom **tool-calling system**
- Custom **final answer formatting**
- No LangChain Agents or LangChain Memory classes

### ✔ Data Sources
1. **Kaggle IMDb Top 1000** stored locally in a **SQLite database** (`imdb_top_1000.db`)  
2. **OMDb API** for online movie details and broader search

### ✔ Tools Included

**From Kaggle (SQLite):**

- `kaggle_movie_info(title)` — detailed movie info  
- `kaggle_movie_rating(title)` — IMDb rating  
- `kaggle_movies_with_actor(actor, limit)` — movies with a given actor  
- `kaggle_top_by_genre(genre, limit)` — top movies by genre  
- `kaggle_search_by_keyword(keyword, limit)` — search in overview text  

**From OMDb:**

- `omdb_movie_info(title)`  
- `omdb_movie_rating(title)`  
- `omdb_search(keyword, limit)`  

All tools return **human-readable Russian text**, not JSON.

### ✔ Memory
- Stores **user name**
- Stores **preferred genres**, actors, directors, movies  
- Persistent storage in `memory_store.json`
- Basic typo tolerance in Russian text (e.g. `я люлблю боевики` is treated as `я люблю боевики`)

### ✔ Fuzzy Matching (Manual FM3 Hybrid)
For Kaggle-based movie lookup (`kaggle_movie_info`, `kaggle_movie_rating`), the agent:

1. First tries direct `LIKE` search in SQLite:
   ```sql
   WHERE lower(Series_Title) LIKE '%query%'
   ```
2. If no exact/partial match is found:
   - Loads a cache of all titles and metadata from the database
   - Computes a **hybrid score** for each movie:
     - Levenshtein distance between normalized query and title  
     - Token overlap between query and title  
     - Token hits inside metadata (overview, genre, director, actors)
   - Chooses the best candidate above a threshold

This allows the agent to handle minor typos in English titles such as:

- `Intersellar` → `Interstellar`  
- `The Martain` → `The Martian`  

For purely Russian titles, Kaggle may not have matches (dataset is in English), but OMDb can still be used.

### ✔ Multi-Tool Calling

The agent can call multiple tools in sequence within one reasoning chain.  
Typical example:

> **User:** `Сравни Interstellar и The Martian`

The model may:

1. Call `kaggle_movie_info("Interstellar")`  
2. Call `kaggle_movie_info("The Martian")`  
3. Compare genres, ratings, directors, and plots  
4. Return a final answer:

```text
Interstellar — более философский и концентрируется на идее выживания человечества через космические путешествия,
а The Martian — более «земной» и сфокусирован на выживании одного человека на Марсе.

Пояснение: Я получил информацию о двух фильмах из Kaggle SQLite базы,
сравнил жанры, рейтинги и описания и на основе этого сформировал вывод.
```

---

## 📂 Project Structure

```text
movie-agent/
│
├── agent.py               # Main agent loop (function calling + memory + reasoning)
├── memory.py              # Custom memory with persistence
├── prompt.py              # System prompt with rules + formatting
├── tools.py               # Unified registry of all tools
├── tools_kaggle.py        # SQLite-based tools (+ manual fuzzy matching)
├── tools_omdb.py          # OMDb API tools
├── build_kaggle_db.py     # Converts CSV → SQLite database
│
├── data/
│   ├── imdb_top_1000.csv  # Kaggle CSV (provided by user)
│   └── imdb_top_1000.db   # SQLite DB (generated)
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Installation & Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

Copy `.env.example` to `.env` and fill:

```env
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
OMDB_API_KEY=your-omdb-key
```

### 3. Download Kaggle Dataset

Download the IMDb Top 1000 Movies and TV Shows dataset from Kaggle and place it as:

```text
data/imdb_top_1000.csv
```

### 4. Build SQLite DB

```bash
python build_kaggle_db.py
```

This creates:

```text
data/imdb_top_1000.db
```

---

## ▶️ Running the Agent

```bash
python agent.py
```

Example start:

```text
🛰️ Радиосигнал получен...
.--. .-. .. . --, .--. .-. .. . --

🎬 «Киноманьяк» выходит на связь!
Я — твой интеллектуальный кино-ассистент.

Я помогу тебе:
• подобрать фильм под настроение  
• узнать рейтинг и краткое описание  
• найти актёров и режиссёров  
• получить персональные рекомендации  

Задай свой вопрос — и мы стартуем в кино-вселенную 🚀  
Для выхода: /exit
```

---

## 🧠 Memory Examples

```text
Ты: Меня зовут Жаныл
Киноманьяк: Привет, Жаныл! ...

Ты: Как меня зовут?
Киноманьяк:
Тебя зовут Жаныл.

Пояснение: Я использовал сохранённую информацию о твоём имени из памяти.
```

Genre and preference memory:

```text
Ты: я люлблю боевики и научные фантастики
(опечатка «люлблю» будет автоматически исправлена)

Ты: какие жанры я люблю
Киноманьяк:
Ты любишь боевики и научную фантастику.

Пояснение: Я ответил на вопрос, используя сохранённые жанры из профиля пользователя.
```

---

## 🧪 Assignment Test Scenarios

### ✔ Basic Functionality

```text
Расскажи про фильм Interstellar
Какой рейтинг у The Martian?
Найди фильмы про Бэтмена
```

The agent will:

- Use Kaggle SQLite tools for well-known movies (IMDb Top 1000)  
- Tolerate minor typos in English titles via fuzzy matching  
- Use OMDb as a fallback when needed  

### ✔ Memory

```text
Меня зовут Жаныл
Как меня зовут?

Я люблю научные фантастики
Что я люблю?
```

Expected pattern:

- The agent remembers and retrieves your name and preferences  
- Answers are in natural Russian with a `Пояснение:` line.  

### ✔ Multi-Tool Calling

```text
Сравни Interstellar и The Martian
```

Typical behavior:

- Calls Kaggle tools for both movies  
- Compares ratings, genres, and plots  
- Produces a structured comparison  
- Includes a short reasoning line explaining which tools were used.  

---

## 🚀 Example Dialog (Realistic)

```text
Ты: Найди фильм с Джеки Чан

Киноманьяк:
Вот несколько фильмов с Джеки Чан из топ-1000, отсортированных по рейтингу:
1. Police Story ...
2. ...

Пояснение: Я использовал Kaggle SQLite базу, нашёл фильмы, где в списке актёров
встречается Джеки Чан, и отсортировал их по рейтингу.
```

---

## 🙌 Author

Developed by Zhanyl as part of the nFactorial LLM Engineering course ✨
