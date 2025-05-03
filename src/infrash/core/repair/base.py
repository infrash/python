#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - klasa bazowa.
"""

import os
import sys
import shutil
import subprocess
import platform
import re
import uuid
import json
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager, is_admin
from infrash.system.dependency import install_dependency
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Repair:
    """
    Klasa naprawcza do rozwiązywania zidentyfikowanych problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Repair.
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

    def fix(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia zidentyfikowany problem.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        logger.info(f"Próba naprawy problemu: {issue.get('title', 'Nieznany problem')}")

        # Sprawdzamy, czy mamy dedykowaną metodę dla tej kategorii problemu
        category = issue.get("category", "unknown")
        method_name = f"_fix_{category}"

        if hasattr(self, method_name):
            try:
                method = getattr(self, method_name)
                return method(issue)
            except Exception as e:
                logger.error(f"Błąd podczas naprawy problemu ({category}): {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody, szukamy w bazie danych rozwiązań
        solution_id = issue.get("solution_id")
        if solution_id and solution_id in self.solutions_db:
            try:
                solution = self.solutions_db[solution_id]
                return self._apply_solution(solution, issue)
            except Exception as e:
                logger.error(f"Błąd podczas stosowania rozwiązania {solution_id}: {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody ani rozwiązania, zwracamy False
        logger.error(f"Brak metody naprawy dla problemu kategorii: {category}")
        return False