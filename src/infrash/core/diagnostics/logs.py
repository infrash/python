#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie logów.
"""

import os
import uuid
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_logs(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza logi w poszukiwaniu problemów.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Katalogi, w których mogą znajdować się logi
    log_dirs = [
        os.path.join(path, "logs"),
        os.path.join(path, "log"),
        os.path.join(path, ".logs"),
        os.path.join(path, ".infrash", "logs")
    ]

    # Słowa kluczowe, które mogą wskazywać na problemy
    error_keywords = [
        "error", "exception", "failed", "failure", "fatal", "panic", "critical"
    ]

    # Sprawdzamy każdy katalog z logami
    for log_dir in log_dirs:
        if not os.path.isdir(log_dir):
            continue

        # Szukamy plików logów
        log_files = []
        for root, _, files in os.walk(log_dir):
            for file in files:
                if file.endswith(".log") or file.endswith(".txt"):
                    log_files.append(os.path.join(root, file))

        # Sprawdzamy każdy plik logów
        for log_file in log_files:
            try:
                # Otwieramy plik i szukamy problemów
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Czytamy ostatnie 100 linii (lub mniej, jeśli plik jest krótszy)
                    lines = f.readlines()[-100:]

                    # Szukamy linii z błędami
                    error_lines = []
                    for i, line in enumerate(lines):
                        if any(keyword in line.lower() for keyword in error_keywords):
                            error_lines.append((i, line.strip()))

                    # Jeśli znaleziono błędy, dodajemy problem
                    if error_lines:
                        # Wybieramy ostatni błąd
                        last_error = error_lines[-1][1]

                        issues.append({
                            "id": str(uuid.uuid4()),
                            "title": "Błędy w logach",
                            "description": f"Znaleziono {len(error_lines)} linii z błędami w pliku {os.path.basename(log_file)}. Ostatni błąd: {last_error[:100]}...",
                            "solution": "Sprawdź logi, aby zidentyfikować przyczynę błędów.",
                            "severity": "warning",
                            "category": "logs",
                            "metadata": {
                                "log_file": log_file,
                                "error_count": len(error_lines),
                                "last_error": last_error
                            }
                        })
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania pliku logu {log_file}: {str(e)}")

    return issues