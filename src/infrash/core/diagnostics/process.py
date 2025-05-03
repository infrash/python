#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - analiza problemów procesów.
"""

import os
import uuid
import subprocess
import re
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_process_handling(path: str, script_path: str, command: str) -> Dict[str, Any]:
    """
    Analizuje błędy związane z uruchamianiem procesów i skryptów.

    Args:
        path: Ścieżka do projektu.
        script_path: Ścieżka do skryptu.
        command: Polecenie, które spowodowało błąd.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    # Podstawowy wynik
    result = {
        "id": str(uuid.uuid4()),
        "title": "Problem z uruchomieniem procesu",
        "description": f"Wystąpił problem podczas uruchamiania polecenia: {command}",
        "solution": "Sprawdź składnię polecenia i upewnij się, że wszystkie wymagane pakiety są zainstalowane.",
        "severity": "error",
        "category": "process",
        "metadata": {
            "command": command,
            "script_path": script_path
        }
    }

    try:
        # Wykonujemy polecenie z przechwyceniem wyjścia
        process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=path,
            timeout=5  # Maksymalny czas wykonania
        )

        # Jeśli polecenie zakończyło się błędem, analizujemy wyjście
        if process.returncode != 0:
            stderr = process.stderr.strip()

            # Analizujemy różne typy błędów
            if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                # Próbujemy znaleźć nazwę brakującego modułu
                match = re.search(r"No module named '([^']+)'", stderr)

                if match:
                    module_name = match.group(1)
                    result["title"] = f"Brakujący moduł: {module_name}"
                    result["description"] = f"Nie można zaimportować modułu {module_name}."
                    result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"
                    result["metadata"]["missing_module"] = module_name

            elif "SyntaxError" in stderr:
                result["title"] = "Błąd składni"
                result["description"] = f"Skrypt zawiera błąd składni: {stderr}"
                result["solution"] = "Popraw błąd składni w skrypcie."

            elif "PermissionError" in stderr:
                result["title"] = "Błąd uprawnień"
                result["description"] = f"Brak odpowiednich uprawnień: {stderr}"
                result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

            elif "FileNotFoundError" in stderr:
                # Próbujemy znaleźć nazwę brakującego pliku
                match = re.search(r"No such file or directory: '([^']+)'", stderr)

                if match:
                    file_name = match.group(1)
                    result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
                    result["description"] = f"Nie można znaleźć pliku: {file_name}"
                    result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
                    result["metadata"]["missing_file"] = file_name

            else:
                # Ogólny błąd
                result["description"] = f"Polecenie zakończyło się błędem (kod {process.returncode}): {stderr}"

    except subprocess.TimeoutExpired:
        result["title"] = "Timeout podczas wykonywania polecenia"
        result["description"] = f"Polecenie nie zakończyło się w wyznaczonym czasie: {command}"
        result["solution"] = "Sprawdź, czy polecenie nie zawiesza się lub nie wymaga interakcji użytkownika."
        result["severity"] = "warning"

    except Exception as e:
        result["description"] = f"Wystąpił nieoczekiwany błąd podczas analizy polecenia: {str(e)}"

    return result