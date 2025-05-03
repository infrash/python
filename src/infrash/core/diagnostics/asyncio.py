#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - rozwiązywanie problemów asyncio.
"""

import os
import uuid
import re
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def solve_asyncio_error(error_message: str, script_content: str) -> Dict[str, Any]:
    """
    Analizuje i rozwiązuje problemy związane z asyncio.

    Args:
        error_message: Komunikat o błędzie.
        script_content: Zawartość skryptu.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    result = {
        "id": str(uuid.uuid4()),
        "title": "Problem z asyncio",
        "description": f"Wystąpił problem związany z asyncio: {error_message}",
        "solution": "Sprawdź poprawność używania asyncio w skrypcie.",
        "severity": "error",
        "category": "asyncio",
        "metadata": {
            "error_message": error_message
        }
    }

    # Problem 1: RuntimeError: asyncio.run() cannot be called from a running event loop
    if "asyncio.run() cannot be called from a running event loop" in error_message:
        result["title"] = "Próba wywołania asyncio.run() z działającej pętli zdarzeń"
        result["description"] = "Funkcja asyncio.run() nie może być wywołana z działającej pętli zdarzeń."
        result["solution"] = "Zamiast asyncio.run(), użyj await na funkcji asynchronicznej lub utwórz nową pętlę zdarzeń."

        # Proponowana poprawka
        fixed_code = script_content.replace("asyncio.run(", "await ")

        if fixed_code == script_content:
            # Jeśli powyższa zamiana nie zadziałała, próbujemy innego rozwiązania
            fixed_code = script_content.replace(
                "asyncio.run(main(args.host, args.port))",
                "loop = asyncio.get_event_loop()\nloop.run_until_complete(main(args.host, args.port))"
            )

        result["metadata"]["fixed_code"] = fixed_code

    # Problem 2: RuntimeWarning: coroutine 'function_name' was never awaited
    elif "was never awaited" in error_message:
        match = re.search(r"coroutine '([^']+)' was never awaited", error_message)

        if match:
            function_name = match.group(1)
            result["title"] = f"Coroutine '{function_name}' nigdy nie została awaited"
            result["description"] = f"Funkcja asynchroniczna '{function_name}' została wywołana, ale nie została awaited."
            result["solution"] = f"Dodaj 'await' przed wywołaniem funkcji '{function_name}' lub użyj asyncio.run()."

            # Proponowana poprawka
            fixed_code = script_content.replace(f"{function_name}(", f"await {function_name}(")
            result["metadata"]["fixed_code"] = fixed_code

    # Problem 3: SyntaxError: 'await' outside async function
    elif "'await' outside async function" in error_message:
        result["title"] = "'await' poza funkcją asynchroniczną"
        result["description"] = "Operator 'await' może być używany tylko wewnątrz funkcji asynchronicznej."
        result["solution"] = "Przekształć funkcję na asynchroniczną (async def) lub użyj asyncio.run()."

        # Proponowana poprawka - znajdujemy funkcję, która zawiera await
        lines = script_content.split('\n')

        # Szukamy linii z await
        await_lines = []
        for i, line in enumerate(lines):
            if "await" in line:
                await_lines.append(i)

        if await_lines:
            # Dla każdej linii z await, szukamy najbliższej definicji funkcji
            for line_num in await_lines:
                # Szukamy wstecz do definicji funkcji
                for i in range(line_num, -1, -1):
                    if re.search(r"def\s+\w+\s*\(", lines[i]):
                        # Znaleziono definicję funkcji - dodajemy async
                        if "async def" not in lines[i]:
                            lines[i] = lines[i].replace("def", "async def")
                        break

            fixed_code = '\n'.join(lines)
            result["metadata"]["fixed_code"] = fixed_code

    # Problem 4: SyntaxError: 'yield' inside async function
    elif "'yield' inside async function" in error_message:
        result["title"] = "'yield' wewnątrz funkcji asynchronicznej"
        result["description"] = "W Pythonie 3.5-3.6 nie można używać 'yield' wewnątrz funkcji asynchronicznej (async def)."
        result["solution"] = "Przekształć funkcję na zwykłą (def) lub zaktualizuj Python do wersji 3.7+ i użyj 'async for'."

        # Proponowana poprawka
        fixed_code = re.sub(r"async\s+def", "def", script_content)
        result["metadata"]["fixed_code"] = fixed_code

    # Problem 5: AttributeError: module 'asyncio' has no attribute 'run'
    elif "module 'asyncio' has no attribute 'run'" in error_message:
        result["title"] = "Funkcja asyncio.run() nie jest dostępna"
        result["description"] = "Funkcja asyncio.run() została wprowadzona w Pythonie 3.7. Używasz starszej wersji Pythona."
        result["solution"] = "Zaktualizuj Python do wersji 3.7+ lub użyj alternatywnej metody uruchamiania coroutines."

        # Proponowana poprawka
        fixed_code = script_content.replace(
            "asyncio.run(main(args.host, args.port))",
            "loop = asyncio.get_event_loop()\nloop.run_until_complete(main(args.host, args.port))\nloop.close()"
        )
        result["metadata"]["fixed_code"] = fixed_code

    return result