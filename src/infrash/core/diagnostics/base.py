#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - klasa bazowa.
"""

import os
import sys
import platform
import subprocess
import json
import uuid
import psutil
import yaml
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import check_dependencies
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Diagnostics:
    """
    Klasa diagnostyczna do identyfikowania i raportowania problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Diagnostics.
        """
        self.os_info = detect_os()
        self.package_manager = get_package_manager()
        self.git = GitRepo()

        # Ładujemy bazę danych rozwiązań
        self.solutions_db = self._load_solutions_db()

    def _load_solutions_db(self) -> Dict[str, Any]:
        """
        Ładuje bazę danych rozwiązań.

        Returns:
            Słownik z bazą danych rozwiązań.
        """
        solutions_db = {}

        try:
            # Ścieżka do katalogu z rozwiązaniami
            solutions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "solutions")

            # Ładujemy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_file = os.path.join(solutions_dir, f"{os_type}.json")

            if os.path.isfile(os_specific_file):
                with open(os_specific_file, 'r') as f:
                    os_specific_solutions = json.load(f)
                solutions_db.update(os_specific_solutions)

            # Ładujemy wspólne rozwiązania
            common_file = os.path.join(solutions_dir, "common.json")
            if os.path.isfile(common_file):
                with open(common_file, 'r') as f:
                    common_solutions = json.load(f)
                solutions_db.update(common_solutions)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania bazy danych rozwiązań: {str(e)}")

        return solutions_db

    def run(self, path: str = ".", level: str = "basic") -> List[Dict[str, Any]]:
        """
        Uruchamia diagnostykę dla projektu.

        Args:
            path: Ścieżka do projektu.
            level: Poziom diagnostyki (basic, advanced, full).

        Returns:
            Lista zidentyfikowanych problemów.
        """
        # Normalizujemy ścieżkę
        path = os.path.abspath(path)
        logger.info(f"Uruchamianie diagnostyki dla katalogu: {path} (poziom: {level})")

        # Lista na znalezione problemy
        issues = []

        # Sprawdzamy, czy katalog istnieje
        if not os.path.isdir(path):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Katalog projektu nie istnieje",
                "description": f"Katalog {path} nie istnieje.",
                "solution": "Utwórz katalog projektu lub użyj poprawnej ścieżki.",
                "severity": "critical",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })
            return issues

        # Podstawowe sprawdzenia (dla wszystkich poziomów)
        issues.extend(self._check_filesystem(path))
        issues.extend(self._check_permissions(path))
        issues.extend(self._check_dependencies(path))

        # Zaawansowane sprawdzenia (dla poziomów advanced i full)
        if level in ["advanced", "full"]:
            issues.extend(self._check_configuration(path))
            issues.extend(self._check_repository(path))
            issues.extend(self._check_networking())

        # Pełne sprawdzenia (tylko dla poziomu full)
        if level == "full":
            issues.extend(self._check_system_resources())
            issues.extend(self._check_logs(path))
            issues.extend(self._check_database(path))

        # Sortujemy problemy według ważności
        severity_order = {
            "critical": 0,
            "error": 1,
            "warning": 2,
            "info": 3
        }

        issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 999))

        logger.info(f"Znaleziono {len(issues)} problemów.")
        return issues