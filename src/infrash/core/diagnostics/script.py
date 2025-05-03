#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - analiza błędów skryptów.
"""

import os
import uuid
import re
from typing import Dict, List, Any, Optional

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def analyze_script_error(script_path: str, error_message: str) -> Dict[str, Any]:
    """
    Analizuje błąd wykonania skryptu Python.

    Args:
        script_path: Ścieżka do skryptu.
        error_message: Komunikat o błędzie.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    # Podstawowy wynik
    result = {
        "id": str(uuid.uuid4()),
        "title": "Błąd wykonania skryptu",
        "description": f"Wystąpił błąd podczas wykonywania skryptu {os.path.basename(script_path)}: {error_message}",
        "solution": "Debuguj skrypt, aby znaleźć przyczynę błędu.",
        "severity": "error",
        "category": "script",
        "metadata": {
            "script_path": script_path,
            "error_message": error_message
        }
    }

    # Analizujemy różne typy błędów
    if "ImportError" in error_message or "ModuleNotFoundError" in error_message:
        # Próbujemy znaleźć nazwę brakującego modułu
        match = re.search(r"No module named '([^']+)'", error_message)

        if match:
            module_name = match.group(1)
            result["title"] = f"Brakujący moduł: {module_name}"
            result["description"] = f"Nie można zaimportować modułu {module_name}."

            # Szukamy odpowiedniego pakietu dla modułu
            package_name = _find_package_for_module(module_name)

            if package_name:
                result["solution"] = f"Zainstaluj brakujący moduł: pip install {package_name}"
            else:
                result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"

            result["metadata"]["missing_module"] = module_name
            result["metadata"]["package_name"] = package_name

    elif "SyntaxError" in error_message:
        # Próbujemy znaleźć linię z błędem
        match = re.search(r"line (\d+)", error_message)

        if match:
            line_number = match.group(1)
            result["title"] = f"Błąd składni w linii {line_number}"
            result["description"] = f"Skrypt zawiera błąd składni w linii {line_number}: {error_message}"
            result["solution"] = f"Popraw błąd składni w linii {line_number} skryptu."
            result["metadata"]["line_number"] = line_number

    elif "PermissionError" in error_message:
        result["title"] = "Błąd uprawnień"
        result["description"] = f"Brak odpowiednich uprawnień: {error_message}"
        result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

    elif "FileNotFoundError" in error_message:
        # Próbujemy znaleźć nazwę brakującego pliku
        match = re.search(r"No such file or directory: '([^']+)'", error_message)

        if match:
            file_name = match.group(1)
            result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
            result["description"] = f"Nie można znaleźć pliku: {file_name}"
            result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
            result["metadata"]["missing_file"] = file_name

    elif "ConnectionRefusedError" in error_message or "ConnectionError" in error_message:
        result["title"] = "Błąd połączenia"
        result["description"] = f"Nie można nawiązać połączenia: {error_message}"
        result["solution"] = "Sprawdź, czy serwer jest uruchomiony i dostępny."
        result["category"] = "networking"

    elif "TimeoutError" in error_message:
        result["title"] = "Timeout połączenia"
        result["description"] = f"Upłynął limit czasu połączenia: {error_message}"
        result["solution"] = "Sprawdź, czy serwer jest dostępny i czy limit czasu jest wystarczający."
        result["category"] = "networking"

    return result

def _find_package_for_module(module_name: str) -> Optional[str]:
    """
    Znajduje nazwę pakietu dla podanego modułu.

    Args:
        module_name: Nazwa modułu.

    Returns:
        Nazwa pakietu lub None, jeśli nie znaleziono.
    """
    # Słownik mapowania między nazwami modułów a nazwami pakietów
    # Często nazwa pakietu to nazwa modułu, ale nie zawsze
    module_to_package = {
        "PIL": "pillow",
        "bs4": "beautifulsoup4",
        "sklearn": "scikit-learn",
        "cv2": "opencv-python",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "jwt": "pyjwt",
        "cairo": "pycairo",
        "gpiozero": "gpiozero",
        "RPi.GPIO": "RPi.GPIO",
        # ... (pozostałe mapowania)
    }

    # Sprawdzamy, czy mamy mapowanie dla tego modułu
    if module_name in module_to_package:
        return module_to_package[module_name]

    # Sprawdzamy, czy to podmoduł (np. requests.exceptions)
    parts = module_name.split('.')
    if parts[0] in module_to_package:
        return module_to_package[parts[0]]

    # Domyślnie zwracamy nazwę modułu jako nazwę pakietu
    return module_name