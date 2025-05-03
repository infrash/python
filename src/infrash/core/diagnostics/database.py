#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie bazy danych.
"""

import os
import uuid
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_database(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z bazą danych.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Sprawdzamy, czy projekt używa bazy danych
    db_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".db") or file.endswith(".sqlite") or file.endswith(".sqlite3"):
                db_files.append(os.path.join(root, file))

    # Jeśli nie znaleziono plików bazy danych, kończymy
    if not db_files:
        return issues

    # Sprawdzamy każdy plik bazy danych
    for db_file in db_files:
        try:
            # Sprawdzamy, czy plik bazy danych jest dostępny do odczytu
            if not os.access(db_file, os.R_OK):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak dostępu do bazy danych",
                    "description": f"Brak uprawnień do odczytu pliku bazy danych: {os.path.basename(db_file)}",
                    "solution": "Zmień uprawnienia do pliku bazy danych.",
                    "severity": "error",
                    "category": "database",
                    "metadata": {
                        "db_file": db_file
                    }
                })
                continue

            # Sprawdzamy, czy plik bazy danych jest uszkodzony
            import sqlite3
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Sprawdzamy, czy możemy wykonać prostą operację
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]

            if result != "ok":
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Uszkodzona baza danych",
                    "description": f"Plik bazy danych {os.path.basename(db_file)} jest uszkodzony: {result}",
                    "solution": "Przywróć bazę danych z kopii zapasowej lub napraw ją.",
                    "severity": "critical",
                    "category": "database",
                    "metadata": {
                        "db_file": db_file,
                        "integrity_check": result
                    }
                })

            conn.close()
        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Problem z bazą danych",
                "description": f"Wystąpił problem z bazą danych {os.path.basename(db_file)}: {str(e)}",
                "solution": "Sprawdź plik bazy danych i upewnij się, że jest poprawny.",
                "severity": "error",
                "category": "database",
                "metadata": {
                    "db_file": db_file,
                    "error": str(e)
                }
            })

    return issues