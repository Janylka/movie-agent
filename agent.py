"""
Главный модуль агента (Вариант 3 — полностью самописный фреймворк).

Функции:
- построение схемы инструментов для OpenAI tools
- интеграция с кастомной памятью
- многошаговый цикл агента (agent loop) с tool calling
- форматирование финального ответа: обычный текст + обязательное «Пояснение: ...»
"""

import json
import os
import inspect
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from memory import Memory, answer_from_memory_if_applicable
from prompt import SYSTEM_PROMPT
from tools import TOOLS

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DEBUG = False  # можно включить для дополнительной отладки


# ======================================================
# TOOL SCHEMA BUILDER
# ======================================================

def map_py_type_to_json(t: Any) -> str:
    """
    Конвертация Python-аннотации типов в тип JSON-схемы для OpenAI tools.
    """
    try:
        origin = getattr(t, "__origin__", None)
        if origin and hasattr(t, "__args__"):
            t = t.__args__[0]
    except Exception:
        pass

    if t in (int,):
        return "integer"
    if t in (float,):
        return "number"
    if t in (bool,):
        return "boolean"
    return "string"


def build_tool_specs() -> List[Dict[str, Any]]:
    """
    Построить список описаний инструментов в формате,
    который ожидает OpenAI для function calling.
    """
    specs = []

    for name, func in TOOLS.items():
        sig = inspect.signature(func)
        props: Dict[str, Any] = {}
        req: List[str] = []

        for p_name, param in sig.parameters.items():
            if param.kind in (
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL
            ):
                # **kwargs / *args не описываем
                continue

            ann = param.annotation if param.annotation != inspect._empty else str
            j_type = map_py_type_to_json(ann)

            props[p_name] = {
                "type": j_type,
                "description": f"Параметр '{p_name}' функции {name}"
            }
            if param.default is inspect._empty:
                req.append(p_name)

        schema: Dict[str, Any] = {"type": "object", "properties": props}
        if req:
            schema["required"] = req

        specs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": func.__doc__ or f"Инструмент {name}.",
                "parameters": schema
            }
        })

    return specs


TOOLS_SPEC = build_tool_specs()


# ======================================================
# ФОРМАТИРОВАНИЕ ФИНАЛЬНОГО ОТВЕТА
# ======================================================

def format_final_answer(raw: str) -> str:
    """
    Гарантировать, что финальный ответ всегда содержит строку
    с префиксом «Пояснение:».

    При этом мы БОЛЬШЕ НЕ добавляем слово «Ответ:» вообще.

    Логика:
    - Если текст пустой — возвращаем шаблон с сообщением об ошибке + пояснение.
    - Если в тексте уже есть «Пояснение:» (в любом регистре) — возвращаем как есть.
    - Иначе добавляем формальное пояснение в конце (вариант R1 — формальный стиль).
    """
    text = (raw or "").strip()
    if not text:
        return (
            "Я не смог сформировать осмысленный ответ.\n"
            "Пояснение: Я столкнулся с внутренней ошибкой при обработке запроса."
        )

    # Если модель уже сама добавила «Пояснение:», оставляем как есть
    if "пояснение:" in text.lower():
        return text

    # Иначе добавляем формальный reasoning (вариант R1)
    return (
        f"{text}\n\n"
        "Пояснение: Я сформировал этот ответ, опираясь на твой запрос, контекст диалога "
        "и данные из доступных инструментов и своей памяти, если это было необходимо."
    )


# ======================================================
# MESSAGE BUILDER (ВСТРАИВАЕМ ПАМЯТЬ)
# ======================================================

def build_messages(memory: Memory, user_input: str) -> List[Dict[str, Any]]:
    """
    Собрать список сообщений для отправки в LLM:
    - системный промпт + профиль
    - несколько последних сообщений user/assistant
    - текущее сообщение пользователя
    """
    profile_block = ""
    prefs_text = memory.get_preferences_text()

    if memory.user_name or prefs_text:
        profile_block += "\n[Профиль пользователя]\n"
        if memory.user_name:
            profile_block += f"Имя пользователя: {memory.user_name}\n"
        if prefs_text:
            profile_block += prefs_text + "\n"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + profile_block}
    ]

    # Берём только user/assistant, без tool-сообщений
    for msg in memory.history[-12:]:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_input})
    return messages


# ======================================================
# MAIN AGENT LOOP
# ======================================================

def run_agent():
    """
    Запустить интерактивный цикл общения с кино-агентом в консоли.
    """
    memory = Memory()

    print("\n 🛰️ Радиосигнал получен...")
    print(".--. .-. .. . --, .--. .-. .. . --\n")
    print("🎬 «Киноманьяк» выходит на связь!")
    print("Я — Киноманьяк, твой интеллектуальный ассистент по кино.\n")
    print("Я помогу тебе выбрать фильм, понять его рейтинг, "
          "узнать больше об актёрах и подобрать персональные рекомендации.\n")
    print("Задай свой вопрос — и мы отправимся в путешествие по кино-вселенной 🚀")
    print("Для завершения сеанса: /exit")

    while True:
        user_input = input("\nТы: ").strip()
        if user_input.lower() in ("/exit", "выход", "пока"):
            bye_text = (
                "🛰️ Связь завершается... \n"
                "Спасибо за сеанс ✨ \n\n"
                "Когда захочешь вернуться — я включу передатчик. Я всегда на орбите 🚀 \n"
                "До следующего сигнала! 👋"
            )
            final_bye = format_final_answer(bye_text)
            print("Киноманьяк:", final_bye)
            memory.add("assistant", final_bye)
            break

        # Сохраняем в память
        memory.add("user", user_input)
        memory.update_from_user_text(user_input)

        # Попробуем ответить из памяти (имя, «что я люблю», «какие жанры я люблю» и т.п.)
        direct = answer_from_memory_if_applicable(user_input, memory)
        if direct:
            final_direct = format_final_answer(direct)
            print("Киноманьяк:", final_direct)
            memory.add("assistant", final_direct)
            continue

        # Иначе запускаем LLM tool-calling
        messages = build_messages(memory, user_input)
        final_answer_done = False

        for step in range(8):  # ограничение шагов chain-of-thought
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.2,
                tools=TOOLS_SPEC,
                tool_choice="auto"
            )

            msg = response.choices[0].message

            if DEBUG:
                print("\n[DEBUG] Шаг агента:", step)
                print("[DEBUG] tool_calls:", msg.tool_calls)
                print("[DEBUG] content:", msg.content)

            # ==== CASE 1: ФИНАЛЬНЫЙ ОТВЕТ ====
            if not msg.tool_calls:
                raw_final = msg.content or "Я не смог сформировать осмысленный ответ."
                final = format_final_answer(raw_final)
                print("Киноманьяк:", final)
                memory.add("assistant", final)
                final_answer_done = True
                break

            # ==== CASE 2: TOOL CALL(S) ====
            # Сообщение ассистента БЕЗ content, только tool_calls
            assistant_msg = {"role": "assistant", "tool_calls": []}

            for tc in msg.tool_calls:
                assistant_msg["tool_calls"].append(
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                )

            messages.append(assistant_msg)

            # Выполняем инструменты
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                raw_args = tc.function.arguments

                # Парсим аргументы (поддерживаем и dict, и строку JSON)
                args: Dict[str, Any] = {}
                if isinstance(raw_args, dict):
                    args = raw_args
                elif isinstance(raw_args, str):
                    try:
                        parsed = json.loads(raw_args)
                        if isinstance(parsed, dict):
                            args = parsed
                    except Exception:
                        args = {}

                tool_func = TOOLS.get(tool_name)
                if not tool_func:
                    result = f"[ERROR] Инструмент '{tool_name}' не найден."
                else:
                    try:
                        result = tool_func(**args)
                    except Exception as e:
                        result = f"[ERROR] Ошибка инструмента '{tool_name}': {e}"

                # В память tool-сообщения не пишем, только в контекст диалога
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tool_name,
                    "content": result
                })

        if not final_answer_done:
            fallback = (
                "Похоже, запрос получился слишком сложным для одного диалога, "
                "и я достиг лимита шагов рассуждения."
            )
            final_fallback = format_final_answer(fallback)
            print("Киноманьяк:", final_fallback)
            memory.add("assistant", final_fallback)


if __name__ == "__main__":
    run_agent()
