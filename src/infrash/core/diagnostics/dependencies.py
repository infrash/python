#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie zależności.
"""

import os
import uuid
import platform
import re
from typing import Dict, List, Any

from infrash.utils.logger import get_logger
from infrash.system.dependency import check_dependencies

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_dependencies(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z zależnościami.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Sprawdzamy, czy wszystkie zależności są zainstalowane
    missing_deps = check_dependencies(path)

    if missing_deps:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": "Brakujące zależności",
            "description": f"Brakujące zależności: {', '.join(missing_deps)}",
            "solution": f"Zainstaluj brakujące zależności: infrash install",
            "severity": "error",
            "category": "dependencies",
            "metadata": {
                "missing_dependencies": missing_deps
            }
        })

    # Sprawdzamy, czy Python jest w wymaganej wersji
    try:
        # Sprawdzamy, czy istnieje plik z informacją o wymaganej wersji Pythona
        required_version = None

        # Sprawdzamy plik pyproject.toml
        pyproject_path = os.path.join(path, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            with open(pyproject_path, 'r') as f:
                content = f.read()

                # Szukamy wymaganej wersji Pythona
                match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
                if match:
                    required_version = match.group(1)

        # Jeśli znaleziono wymaganą wersję, sprawdzamy czy jest kompatybilna
        if required_version:
            import packaging.specifiers
            import packaging.version

            current_version = platform.python_version()
            specifier = packaging.specifiers.SpecifierSet(required_version)

            if not specifier.contains(current_version):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Niekompatybilna wersja Pythona",
                    "description": f"Aktualna wersja Pythona ({current_version}) nie jest kompatybilna z wymaganą ({required_version}).",
                    "solution": "Zainstaluj kompatybilną wersję Pythona lub użyj wirtualnego środowiska.",
                    "severity": "error",
                    "category": "dependencies",
                    "metadata": {
                        "current_version": current_version,
                        "required_version": required_version
                    }
                })
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania wersji Pythona: {str(e)}")

    return issues