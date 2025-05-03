#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - stosowanie rozwiązań.
"""

import os
import re
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _apply_solution(self, solution: Dict[str, Any], issue: Dict[str, Any]) -> bool:
    """
    Stosuje rozwiązanie z bazy danych.

    Args:
        solution: Słownik opisujący rozwiązanie.
        issue: Słownik opisujący problem.

    Returns:
        True, jeśli rozwiązanie zostało zastosowane pomyślnie, False w przeciwnym razie.
    """
    # Typ rozwiązania określa, jak je zastosować
    solution_type = solution.get("type", "unknown")

    if solution_type == "command":
        # Rozwiązanie polega na wykonaniu polecenia
        command = solution.get("command", "")

        # Zastępujemy zmienne w poleceniu
        command = self._replace_variables(command, issue)

        # Wykonujemy polecenie
        return self._run_command(command)

    elif solution_type == "file_modify":
        # Rozwiązanie polega na modyfikacji pliku
        file_path = solution.get("file_path", "")
        pattern = solution.get("pattern", "")
        replacement = solution.get("replacement", "")

        # Zastępujemy zmienne w ścieżce, wzorcu i zastępniku
        file_path = self._replace_variables(file_path, issue)
        pattern = self._replace_variables(pattern, issue)
        replacement = self._replace_variables(replacement, issue)

        # Modyfikujemy plik
        return self._modify_file(file_path, pattern, replacement)

    elif solution_type == "file_create":
        # Rozwiązanie polega na utworzeniu pliku
        file_path = solution.get("file_path", "")
        content = solution.get("content", "")

        # Zastępujemy zmienne w ścieżce i zawartości
        file_path = self._replace_variables(file_path, issue)
        content = self._replace_variables(content, issue)

        # Tworzymy plik
        return self._create_file(file_path, content)

    elif solution_type == "package_install":
        # Rozwiązanie polega na instalacji pakietu
        package_name = solution.get("package_name", "")
        package_manager = solution.get("package_manager", "")

        # Zastępujemy zmienne w nazwie pakietu i menedżerze pakietów
        package_name = self._replace_variables(package_name, issue)
        package_manager = self._replace_variables(package_manager, issue)

        # Instalujemy pakiet
        if not package_manager:
            package_manager = self.package_manager

        return self._install_package(package_name, package_manager)

    elif solution_type == "composite":
        # Rozwiązanie składa się z wielu rozwiązań
        sub_solutions = solution.get("solutions", [])

        # Stosujemy każde rozwiązanie
        success = True
        for sub_solution in sub_solutions:
            if not self._apply_solution(sub_solution, issue):
                success = False

        return success

    else:
        logger.error(f"Nieznany typ rozwiązania: {solution_type}")
        return False

def _replace_variables(self, text: str, issue: Dict[str, Any]) -> str:
    """
    Zastępuje zmienne w tekście.

    Args:
        text: Tekst z zmiennymi.
        issue: Słownik opisujący problem.

    Returns:
        Tekst z zastąpionymi zmiennymi.
    """
    # Zastępujemy zmienne w formacie ${nazwa_zmiennej}
    if not text:
        return text

    # Pobieramy metadane z problemu
    metadata = issue.get("metadata", {})

    # Dodajemy podstawowe zmienne
    variables = {
        "os_name": self.os_info.get("name", "unknown"),
        "os_version": self.os_info.get("version", "unknown"),
        "os_type": self.os_info.get("type", "unknown"),
        "package_manager": self.package_manager,
        "python_version": platform.python_version(),
        "home_dir": os.path.expanduser("~"),
        "temp_dir": tempfile.gettempdir()
    }

    # Dodajemy zmienne z metadanych
    variables.update(metadata)

    # Zastępujemy zmienne
    for key, value in variables.items():
        text = text.replace(f"${{{key}}}", str(value))

    return text