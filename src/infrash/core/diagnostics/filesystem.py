#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie systemu plików.
"""

import os
import uuid
import shutil
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_filesystem(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z systemem plików.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Sprawdzamy, czy podstawowe pliki i katalogi istnieją
    essential_files = [
        "infrash.yaml", "infrash.yml",
        ".infrash/config.yaml", ".infrash/config.yml",
        "requirements.txt", "pyproject.toml", "setup.py",
        "Dockerfile", "docker-compose.yml"
    ]

    file_exists = False
    for file in essential_files:
        if os.path.isfile(os.path.join(path, file)):
            file_exists = True
            break

    if not file_exists:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": "Brak plików konfiguracyjnych",
            "description": "Nie znaleziono żadnych plików konfiguracyjnych projektu.",
            "solution": "Zainicjalizuj projekt za pomocą 'infrash init'.",
            "severity": "warning",
            "category": "filesystem",
            "metadata": {
                "path": path
            }
        })

    # Sprawdzamy, czy jest wystarczająco dużo miejsca na dysku
    try:
        disk_usage = shutil.disk_usage(path)
        free_space_gb = disk_usage.free / (1024 ** 3)

        if free_space_gb < 1.0:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Mało miejsca na dysku",
                "description": f"Na dysku pozostało tylko {free_space_gb:.2f} GB wolnego miejsca.",
                "solution": "Zwolnij miejsce na dysku lub użyj innej partycji.",
                "severity": "warning",
                "category": "filesystem",
                "metadata": {
                    "free_space_gb": free_space_gb
                }
            })
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania miejsca na dysku: {str(e)}")

    return issues

def _check_permissions(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z uprawnieniami.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Sprawdzamy, czy mamy uprawnienia do zapisu w katalogu projektu
    if not os.access(path, os.W_OK):
        issues.append({
            "id": str(uuid.uuid4()),
            "title": "Brak uprawnień do zapisu",
            "description": f"Brak uprawnień do zapisu w katalogu {path}.",
            "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
            "severity": "critical",
            "category": "permissions",
            "metadata": {
                "path": path
            }
        })

    # Sprawdzamy, czy mamy uprawnienia do wykonywania plików w katalogu projektu
    if not os.access(path, os.X_OK):
        issues.append({
            "id": str(uuid.uuid4()),
            "title": "Brak uprawnień do wykonywania",
            "description": f"Brak uprawnień do wykonywania plików w katalogu {path}.",
            "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
            "severity": "critical",
            "category": "permissions",
            "metadata": {
                "path": path
            }
        })

    # W systemach Unix sprawdzamy właściciela i grupę
    if os.name == "posix":
        try:
            owner = os.stat(path).st_uid
            current_user = os.getuid()

            if owner != current_user:
                import pwd
                owner_name = pwd.getpwuid(owner).pw_name
                current_user_name = pwd.getpwuid(current_user).pw_name

                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Katalog należy do innego użytkownika",
                    "description": f"Katalog {path} należy do użytkownika {owner_name}, a aktualny użytkownik to {current_user_name}.",
                    "solution": f"Zmień właściciela katalogu: sudo chown -R {current_user_name}:{current_user_name} {path}",
                    "severity": "warning",
                    "category": "permissions",
                    "metadata": {
                        "path": path,
                        "owner": owner_name,
                        "current_user": current_user_name
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania właściciela katalogu: {str(e)}")

    return issues