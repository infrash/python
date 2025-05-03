"""
git.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł obsługi repozytoriów git. Umożliwia klonowanie, aktualizację
i zarządzanie repozytoriami git.
"""

import os
import sys
import subprocess
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

class GitRepo:
    """
    Klasa obsługująca operacje na repozytoriach git.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję GitRepo.
        """
        self._check_git_installed()

    def _check_git_installed(self) -> bool:
        """
        Sprawdza, czy git jest zainstalowany.

        Returns:
            True, jeśli git jest zainstalowany, False w przeciwnym razie.
        """
        try:
            result = subprocess.run(
                ["git", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result.returncode != 0:
                logger.warning("Git nie jest zainstalowany.")
                return False

            logger.debug(f"Git zainstalowany: {result.stdout.strip()}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania instalacji git: {str(e)}")
            return False

    def clone(self, url: str, path: str = ".", branch: Optional[str] = None) -> bool:
        """
        Klonuje repozytorium git.

        Args:
            url: URL repozytorium.
            path: Ścieżka docelowa.
            branch: Gałąź do sklonowania (opcjonalne).

        Returns:
            True, jeśli repozytorium zostało sklonowane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Klonowanie repozytorium {url} do {path}")

            # Przygotowujemy polecenie git clone
            cmd = ["git", "clone"]

            # Dodajemy gałąź, jeśli podano
            if branch:
                cmd.extend(["-b", branch])

            # Dodajemy URL i ścieżkę
            cmd.extend([url, path])

            # Wykonujemy polecenie
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result.returncode != 0:
                logger.error(f"Błąd podczas klonowania repozytorium: {result.stderr}")
                return False

            logger.info("Repozytorium zostało sklonowane pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas klonowania repozytorium: {str(e)}")
            return False

    def init(self, path: str = ".") -> bool:
        """
        Inicjalizuje nowe repozytorium git.

        Args:
            path: Ścieżka do katalogu.

        Returns:
            True, jeśli repozytorium zostało zainicjalizowane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Inicjalizacja repozytorium w {path}")

            # Tworzymy katalog, jeśli nie istnieje
            os.makedirs(path, exist_ok=True)

            # Przygotowujemy polecenie git init
            cmd = ["git", "init"]

            # Wykonujemy polecenie
            result = subprocess.run(
                cmd,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result.returncode != 0:
                logger.error(f"Błąd podczas inicjalizacji repozytorium: {result.stderr}")
                return False

            logger.info("Repozytorium zostało zainicjalizowane pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji repozytorium: {str(e)}")
            return False

    def update(self, path: str = ".", branch: Optional[str] = None) -> bool:
        """
        Aktualizuje repozytorium git.

        Args:
            path: Ścieżka do repozytorium.
            branch: Gałąź do aktualizacji (opcjonalne).

        Returns:
            True, jeśli repozytorium zostało zaktualizowane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Aktualizacja repozytorium w {path}")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return False

            # Jeśli podano gałąź, przechodzimy na nią
            if branch:
                cmd_checkout = ["git", "checkout", branch]

                result_checkout = subprocess.run(
                    cmd_checkout,
                    cwd=path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if result_checkout.returncode != 0:
                    logger.error(f"Błąd podczas przechodzenia na gałąź {branch}: {result_checkout.stderr}")
                    return False

            # Przygotowujemy polecenie git pull
            cmd_pull = ["git", "pull"]

            # Wykonujemy polecenie
            result_pull = subprocess.run(
                cmd_pull,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result_pull.returncode != 0:
                logger.error(f"Błąd podczas aktualizacji repozytorium: {result_pull.stderr}")
                return False

            logger.info("Repozytorium zostało zaktualizowane pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji repozytorium: {str(e)}")
            return False

    def get_status(self, path: str = ".") -> Dict[str, Any]:
        """
        Pobiera status repozytorium git.

        Args:
            path: Ścieżka do repozytorium.

        Returns:
            Słownik ze statusem repozytorium.
        """
        try:
            logger.debug(f"Pobieranie statusu repozytorium w {path}")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return {"error": "Katalog nie jest repozytorium git."}

            # Przygotowujemy polecenie git status
            cmd_status = ["git", "status", "--porcelain"]

            # Wykonujemy polecenie
            result_status = subprocess.run(
                cmd_status,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result_status.returncode != 0:
                logger.error(f"Błąd podczas pobierania statusu repozytorium: {result_status.stderr}")
                return {"error": result_status.stderr}

            # Sprawdzamy, czy są niezatwierdzone zmiany
            changes = result_status.stdout.strip().split('\n')
            changes = [change for change in changes if change]  # Usuwamy puste linie

            # Pobieramy aktualny commit
            cmd_log = ["git", "log", "--format=%H", "-n", "1"]

            result_log = subprocess.run(
                cmd_log,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            commit = result_log.stdout.strip() if result_log.returncode == 0 else "unknown"

            # Zwracamy status repozytorium
            return {
                "dirty": bool(changes),
                "changes": len(changes),
                "commit": commit
            }

        except Exception as e:
            logger.error(f"Błąd podczas pobierania statusu repozytorium: {str(e)}")
            return {"error": str(e)}

    def get_current_branch(self, path: str = ".") -> str:
        """
        Pobiera aktualną gałąź repozytorium git.

        Args:
            path: Ścieżka do repozytorium.

        Returns:
            Nazwa aktualnej gałęzi.
        """
        try:
            logger.debug(f"Pobieranie aktualnej gałęzi repozytorium w {path}")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return "unknown"

            # Przygotowujemy polecenie git branch
            cmd_branch = ["git", "branch", "--show-current"]

            # Wykonujemy polecenie
            result_branch = subprocess.run(
                cmd_branch,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result_branch.returncode != 0:
                logger.error(f"Błąd podczas pobierania aktualnej gałęzi: {result_branch.stderr}")
                return "unknown"

            # Zwracamy nazwę gałęzi
            return result_branch.stdout.strip()

        except Exception as e:
            logger.error(f"Błąd podczas pobierania aktualnej gałęzi: {str(e)}")
            return "unknown"

    def get_remote_url(self, path: str = ".") -> str:
        """
        Pobiera URL zdalnego repozytorium git.

        Args:
            path: Ścieżka do repozytorium.

        Returns:
            URL zdalnego repozytorium.
        """
        try:
            logger.debug(f"Pobieranie URL zdalnego repozytorium w {path}")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return ""

            # Przygotowujemy polecenie git remote
            cmd_remote = ["git", "remote", "get-url", "origin"]

            # Wykonujemy polecenie
            result_remote = subprocess.run(
                cmd_remote,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if result_remote.returncode != 0:
                logger.debug(f"Brak zdalnego repozytorium: {result_remote.stderr}")
                return ""

            # Zwracamy URL
            return result_remote.stdout.strip()

        except Exception as e:
            logger.error(f"Błąd podczas pobierania URL zdalnego repozytorium: {str(e)}")
            return ""

    def is_behind_remote(self, path: str = ".") -> bool:
        """
        Sprawdza, czy lokalne repozytorium jest nieaktualne w stosunku do zdalnego.

        Args:
            path: Ścieżka do repozytorium.

        Returns:
            True, jeśli lokalne repozytorium jest nieaktualne, False w przeciwnym razie.
        """
        try:
            logger.debug(f"Sprawdzanie, czy repozytorium w {path} jest nieaktualne")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return False

            # Pobieramy URL zdalnego repozytorium
            remote_url = self.get_remote_url(path)

            if not remote_url:
                logger.debug("Brak zdalnego repozytorium.")
                return False

            # Pobieramy aktualną gałąź
            current_branch = self.get_current_branch(path)

            if current_branch == "unknown":
                logger.error("Nie można określić aktualnej gałęzi.")
                return False

            # Aktualizujemy referencje
            cmd_fetch = ["git", "fetch"]

            result_fetch = subprocess.run(
                cmd_fetch,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_fetch.returncode != 0:
                logger.error(f"Błąd podczas aktualizacji referencji: {result_fetch.stderr}")
                return False

            # Sprawdzamy, czy lokalne repozytorium jest nieaktualne
            cmd_status = ["git", "status", "-uno"]

            result_status = subprocess.run(
                cmd_status,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_status.returncode != 0:
                logger.error(f"Błąd podczas sprawdzania statusu: {result_status.stderr}")
                return False

            # Sprawdzamy, czy w wyniku jest informacja o nieaktualności
            return "branch is behind" in result_status.stdout or "Your branch is behind" in result_status.stdout

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania nieaktualności repozytorium: {str(e)}")
            return False

    def get_commits_behind(self, path: str = ".") -> int:
        """
        Pobiera liczbę commitów, o które lokalne repozytorium jest nieaktualne.

        Args:
            path: Ścieżka do repozytorium.

        Returns:
            Liczba commitów.
        """
        try:
            logger.debug(f"Pobieranie liczby commitów, o które repozytorium w {path} jest nieaktualne")

            # Sprawdzamy, czy katalog jest repozytorium git
            if not os.path.isdir(os.path.join(path, ".git")):
                logger.error(f"Katalog {path} nie jest repozytorium git.")
                return 0

            # Pobieramy URL zdalnego repozytorium
            remote_url = self.get_remote_url(path)

            if not remote_url:
                logger.debug("Brak zdalnego repozytorium.")
                return 0

            # Pobieramy aktualną gałąź
            current_branch = self.get_current_branch(path)

            if current_branch == "unknown":
                logger.error("Nie można określić aktualnej gałęzi.")
                return 0

            # Aktualizujemy referencje
            cmd_fetch = ["git", "fetch"]

            result_fetch = subprocess.run(
                cmd_fetch,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_fetch.returncode != 0:
                logger.error(f"Błąd podczas aktualizacji referencji: {result_fetch.stderr}")
                return 0

            # Pobieramy liczbę commitów
            cmd_log = ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"]

            result_log = subprocess.run(
                cmd_log,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result_log.returncode != 0:
                logger.error(f"Błąd podczas pobierania liczby commitów: {result_log.stderr}")
                return 0

            # Zwracamy liczbę commitów
            try:
                return int(result_log.stdout.strip())
            except ValueError:
                logger.error(f"Nie można przekonwertować wyniku na liczbę: {result_log.stdout}")
                return 0

        except Exception as e:
            logger.error(f"Błąd podczas pobierania liczby commitów: {str(e)}")
            return 0