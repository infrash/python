#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł aktualizacji repozytoriów. Umożliwia zarządzanie aktualizacjami
repozytoriów git, synchronizację zmian i śledzenie zmian.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class RepoUpdater:
    """
    Klasa zarządzająca aktualizacjami repozytoriów git.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję RepoUpdater.
        """
        self.git = GitRepo()

    def update_repository(self, repo_path: str, branch: Optional[str] = None, remote: str = "origin") -> bool:
        """
        Aktualizuje repozytorium git.
        
        Args:
            repo_path: Ścieżka do repozytorium.
            branch: Nazwa gałęzi (opcjonalnie).
            remote: Nazwa zdalnego repozytorium (opcjonalnie).
            
        Returns:
            True, jeśli repozytorium zostało zaktualizowane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Aktualizacja repozytorium w {repo_path}")

            # Sprawdzamy, czy ścieżka istnieje i jest repozytorium git
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                logger.error(f"Katalog {repo_path} nie jest repozytorium git")
                return False

            # Pobieramy aktualne gałęzie zdalne
            cmd_fetch = ["git", "fetch", remote]

            result_fetch = subprocess.run(
                cmd_fetch,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_fetch.returncode != 0:
                logger.error(f"Błąd podczas pobierania gałęzi zdalnych: {result_fetch.stderr}")
                return False

            # Określamy gałąź do aktualizacji
            target_branch = branch or self.git.get_current_branch(repo_path)

            if not target_branch or target_branch == "unknown":
                logger.error("Nie można określić gałęzi do aktualizacji")
                return False

            # Sprawdzamy, czy repozytorium ma niezatwierdzone zmiany
            status = self.git.get_status(repo_path)

            if status.get("dirty", False):
                logger.warning(f"Repozytorium ma niezatwierdzone zmiany ({status.get('changes', 0)})")

                # Zapisujemy lokalne zmiany w stash
                cmd_stash = ["git", "stash", "save", "Automatyczny stash przez infrash przed aktualizacją"]

                result_stash = subprocess.run(
                    cmd_stash,
                    cwd=repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if result_stash.returncode != 0:
                    logger.error(f"Błąd podczas tworzenia stash: {result_stash.stderr}")
                    return False

                logger.info("Lokalne zmiany zostały zapisane w stash")

            # Aktualizujemy repozytorium
            cmd_pull = ["git", "pull", remote, target_branch]

            result_pull = subprocess.run(
                cmd_pull,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_pull.returncode != 0:
                logger.error(f"Błąd podczas aktualizacji repozytorium: {result_pull.stderr}")

                # Przywracamy lokalne zmiany ze stash, jeśli były
                if status.get("dirty", False):
                    cmd_stash_pop = ["git", "stash", "pop"]

                    subprocess.run(
                        cmd_stash_pop,
                        cwd=repo_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                return False

            # Przywracamy lokalne zmiany ze stash, jeśli były
            if status.get("dirty", False):
                cmd_stash_pop = ["git", "stash", "pop"]

                result_stash_pop = subprocess.run(
                    cmd_stash_pop,
                    cwd=repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if result_stash_pop.returncode != 0:
                    logger.warning(f"Błąd podczas przywracania zmian ze stash: {result_stash_pop.stderr}")
                    logger.info("Lokalnie zmiany pozostają w stash. Użyj 'git stash pop' aby je przywrócić.")

            logger.info(f"Repozytorium zostało zaktualizowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji repozytorium: {str(e)}")
            return False

    def check_for_updates(self, repo_path: str, remote: str = "origin") -> Dict[str, Any]:
        """
        Sprawdza, czy są dostępne aktualizacje dla repozytorium.
        
        Args:
            repo_path: Ścieżka do repozytorium.
            remote: Nazwa zdalnego repozytorium (opcjonalnie).
            
        Returns:
            Słownik z informacjami o dostępnych aktualizacjach.
        """
        result = {
            "has_updates": False,
            "current_branch": "unknown",
            "remote_branch": "unknown",
            "commits_behind": 0,
            "commits_ahead": 0
        }

        try:
            logger.info(f"Sprawdzanie aktualizacji dla repozytorium w {repo_path}")

            # Sprawdzamy, czy ścieżka istnieje i jest repozytorium git
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                logger.error(f"Katalog {repo_path} nie jest repozytorium git")
                return result

            # Pobieramy aktualne gałęzie zdalne
            cmd_fetch = ["git", "fetch", remote]

            result_fetch = subprocess.run(
                cmd_fetch,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_fetch.returncode != 0:
                logger.error(f"Błąd podczas pobierania gałęzi zdalnych: {result_fetch.stderr}")
                return result

            # Pobieramy aktualną gałąź
            current_branch = self.git.get_current_branch(repo_path)
            result["current_branch"] = current_branch

            if not current_branch or current_branch == "unknown":
                logger.error("Nie można określić aktualnej gałęzi")
                return result

            # Określamy nazwę zdalnej gałęzi
            remote_branch = f"{remote}/{current_branch}"
            result["remote_branch"] = remote_branch

            # Sprawdzamy, ile commitów lokalnie jest za zdalnym repozytorium
            cmd_behind = ["git", "rev-list", "--count", f"{current_branch}..{remote_branch}"]

            result_behind = subprocess.run(
                cmd_behind,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_behind.returncode == 0:
                result["commits_behind"] = int(result_behind.stdout.strip() or 0)

            # Sprawdzamy, ile commitów lokalnie jest przed zdalnym repozytorium
            cmd_ahead = ["git", "rev-list", "--count", f"{remote_branch}..{current_branch}"]

            result_ahead = subprocess.run(
                cmd_ahead,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_ahead.returncode == 0:
                result["commits_ahead"] = int(result_ahead.stdout.strip() or 0)

            # Określamy, czy są dostępne aktualizacje
            result["has_updates"] = result["commits_behind"] > 0

            return result

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania aktualizacji: {str(e)}")
            return result

    def auto_update(self, repo_path: str, remote: str = "origin") -> bool:
        """
        Automatycznie aktualizuje repozytorium, jeśli są dostępne aktualizacje.
        
        Args:
            repo_path: Ścieżka do repozytorium.
            remote: Nazwa zdalnego repozytorium (opcjonalnie).
            
        Returns:
            True, jeśli repozytorium zostało zaktualizowane pomyślnie, False w przeciwnym razie.
        """
        try:
            # Sprawdzamy, czy są dostępne aktualizacje
            updates = self.check_for_updates(repo_path, remote)

            if not updates["has_updates"]:
                logger.info(f"Repozytorium w {repo_path} jest aktualne")
                return True

            # Aktualizujemy repozytorium
            logger.info(f"Znaleziono aktualizacje: {updates['commits_behind']} commitów do pobrania")
            return self.update_repository(repo_path, updates["current_branch"], remote)

        except Exception as e:
            logger.error(f"Błąd podczas automatycznej aktualizacji: {str(e)}")
            return False