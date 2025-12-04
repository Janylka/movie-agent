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

# 🚀 Example Dialog (Real & Best Quality)

---

### ⭐ Recommendations Based on “Interstellar”

```text
Ты: Мне нравится Интерстеллар
Киноманьяк:
Если тебе понравился "Интерстеллар", вот несколько фильмов о космосе, которые могут тебя заинтересовать:

1. WALL·E — В далеком будущем маленький робот по сбору мусора случайно отправляется в космическое путешествие, которое в конечном итоге решит судьбу человечества.
2. Alien — После того как космический торговый корабль получает неизвестный сигнал бедствия, один из членов экипажа подвергается атаке загадочного существа.
3. Aliens — Спустя пятьдесят семь лет после выживания в апокалиптической атаке на своем космическом судне, офицер Рипли пробуждается от гиперсна и сталкивается с новыми угрозами.

Эти фильмы предлагают уникальные взгляды на космос и его загадки, и я думаю, что они могут тебе понравиться! 🚀

Пояснение: Я нашел фильмы о космосе, используя ключевое слово "space" в базе данных Kaggle.
Среди них есть WALL·E, Alien и Aliens, которые могут быть интересны, если тебе понравился "Интерстеллар".

---

Ты: ого круто. А какие самые топовые?
Киноманьяк:
Вот несколько топовых фильмов, которые могут тебя заинтересовать, хотя они не все строго о космосе, но относятся к жанрам приключений и научной фантастики:

1. Властелин колец: Возвращение короля (The Lord of the Rings: The Return of the King) (2003) — Рейтинг: 8.9
2. Начало (Inception) (2010) — Рейтинг: 8.8
3. Властелин колец: Братство кольца (The Lord of the Rings: The Fellowship of the Ring) (2001) — Рейтинг: 8.8
4. Властелин колец: Две крепости (The Lord of the Rings: The Two Towers) (2002) — Рейтинг: 8.7
5. Звёздные войны: Эпизод V — Империя наносит ответный удар (Star Wars: Episode V - The Empire Strikes Back) (1980) — Рейтинг: 8.7

Эти фильмы получили высокие оценки и являются классикой, так что они точно стоят твоего внимания! 🌌

Пояснение: Я нашёл топовые фильмы в жанре приключений из датасета IMDb Top 1000.
Хотя в жанре научной фантастики не оказалось фильмов, я подобрал популярные приключенческие фильмы,
такие как "Властелин колец" и "Начало".

---

Ты: А из того что ты ранее мне предлагал, какой из них самый топовый?
Киноманьяк:
Из фильмов, которые я ранее предлагал, WALL·E и Alien имеют одинаковый рейтинг IMDb — 8.4,
что делает их самыми топовыми среди предложенных. "Aliens" немного ниже с рейтингом 8.3.

Если ты ищешь что-то с высоким рейтингом, WALL·E и Alien — отличные варианты! 🌟

Пояснение: Я проверил рейтинги фильмов WALL·E, Alien и Aliens в базе данных Kaggle.
WALL·E и Alien имеют рейтинг 8.4, а Aliens — 8.3.

---

Ты: Ты крутой
Киноманьяк:
Спасибо, Жаныл! Мне приятно это слышать! 😊  
Если у тебя есть еще вопросы о фильмах или ты хочешь получить рекомендации, не стесняйся спрашивать.  
Я здесь, чтобы помочь! 🎬✨

```

---

### ⭐ Star Wars Description

```text
Ты: Можешь рассказать про Звездные Войны?

Киноманьяк:
"Звёздные войны: Эпизод V — Империя наносит ответный удар" (1980) — это второй фильм оригинальной трилогии "Звёздных войн".

Жанр: экшен, приключения, фэнтези  
Рейтинг IMDb: 8.7  
Режиссёр: Ирвин Кершнер  
В главных ролях: Марк Хэмилл, Харрисон Форд, Кэрри Фишер, Билли Ди Уильямс

Описание:
После того как повстанцы жестоко побеждены Империей на ледяной планете Хот, Люк Скайуокер начинает обучение у Йоды.
Тем временем его друзья преследуются Дартом Вейдером и охотником за головами Бобой Феттом по всей галактике.

Этот фильм считается одним из лучших в серии и получил высокие оценки за сюжет, масштабность и развитие персонажей. 🌌

Пояснение:
Я использовал данные из Kaggle, чтобы предоставить информацию о фильме
"Звёздные войны: Эпизод V — Империя наносит ответный удар": жанр, рейтинг, режиссёра и описание сюжета.

```

---

### ⭐ Leonardo DiCaprio Movies

```text
Ты: Найди фильмы с Leonardo DiCaprio и покажи их рейтинги

Киноманьяк:
Вот несколько фильмов с Леонардо ДиКаприо и их рейтинги:

1. Начало (Inception) (2010) — Рейтинг: 8.8  
2. Отступники (The Departed) (2006) — Рейтинг: 8.5  
3. Джанго освобожденный (Django Unchained) (2012) — Рейтинг: 8.4  
4. Остров проклятых (Shutter Island) (2010) — Рейтинг: 8.2  
5. Волк с Уолл-стрит (The Wolf of Wall Street) (2013) — Рейтинг: 8.2  

Эти фильмы демонстрируют выдающуюся игру ДиКаприо и предлагают захватывающие сюжеты! 🎬

Пояснение:
Я нашёл фильмы с Леонардо ДиКаприо в базе данных Kaggle и вывел их названия и рейтинги.
Все фильмы имеют высокие оценки, что подчёркивает их популярность и качество.

```

---

### ⭐ Farewell Example

```text
Ты: Пока
Киноманьяк:
🛰️ Связь завершается...
Спасибо за сеанс ✨
До следующего сигнала! 👋
```

---

# 🙌 Author

Developed by **Zhanyl** for *nFactorial LLM Engineering* ✨
