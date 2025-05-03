#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie repozytorium.
"""

import os
import uuid
from typing import Dict, List, Any

from infrash.utils.logger import get_logger
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_repository(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z repozytorium git.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    git = GitRepo()

    # Sprawdzamy, czy katalog jest repozytorium git
    if not os.path.isdir(os.path.join(path, ".git")):
        # To nie jest błąd, ale dodajemy informację
        issues.append({
            "id": str(uuid.uuid4()),
            "title": "Brak repozytorium git",
            "description": "Katalog nie jest repozytorium git.",
            "solution": "Zainicjalizuj repozytorium git: git init",
            "severity": "info",
            "category": "repository",
            "metadata": {
                "path": path
            }
        })
        return issues  # Nie ma sensu kontynuować, jeśli nie ma repozytorium

    try:
        # Sprawdzamy, czy repozytorium ma niezatwierdzone zmiany
        repo_status = git.get_status(path)

        if repo_status.get("dirty", False):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Niezatwierdzone zmiany w repozytorium",
                "description": f"Repozytorium ma {repo_status.get('changes', 0)} niezatwierdzonych zmian.",
                "solution": "Zatwierdź zmiany lub cofnij je: git commit lub git reset",
                "severity": "warning",
                "category": "repository",
                "metadata": {
                    "path": path,
                    "changes": repo_status.get("changes", 0)
                }
            })

        # Sprawdzamy, czy repozytorium ma skonfigurowane zdalne repozytorium
        remote_url = git.get_remote_url(path)

        if not remote_url:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak zdalnego repozytorium",
                "description": "Repozytorium nie ma skonfigurowanego zdalnego repozytorium.",
                "solution": "Dodaj zdalne repozytorium: git remote add origin <url>",
                "severity": "info",
                "category": "repository",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy repozytorium jest aktualne
        is_behind = git.is_behind_remote(path)

        if is_behind:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Repozytorium nie jest aktualne",
                "description": "Lokalne repozytorium jest nieaktualne w stosunku do zdalnego.",
                "solution": "Zaktualizuj repozytorium: git pull",
                "severity": "warning",
                "category": "repository",
                "metadata": {
                    "path": path,
                    "commits_behind": git.get_commits_behind(path)
                }
            })

    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania repozytorium: {str(e)}")

    return issues