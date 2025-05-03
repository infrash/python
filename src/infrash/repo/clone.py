#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł klonowania repozytoriów. Umożliwia klonowanie repozytoriów git
z różnych źródeł, konfigurację i inicjalizację.
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

class RepoCloner:
    """
    Klasa do klonowania repozytoriów git.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję RepoCloner.
        """
        self.git = GitRepo()

    def clone_repository(self, url: str, target_path: str, branch: Optional[str] = None, depth: Optional[int] = None) -> bool:
        """
        Klonuje repozytorium git.
        
        Args:
            url: URL repozytorium.
            target_path: Ścieżka docelowa.
            branch: Nazwa gałęzi do sklonowania (opcjonalnie).
            depth: Głębokość klonowania (opcjonalnie).
            
        Returns:
            True, jeśli repozytorium zostało sklonowane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Klonowanie repozytorium {url} do {target_path}")

            # Tworzymy katalog docelowy, jeśli nie istnieje
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

            # Sprawdzamy, czy katalog docelowy jest pusty
            if os.path.exists(target_path) and os.listdir(target_path):
                logger.error(f"Katalog docelowy {target_path} nie jest pusty")
                return False

            # Przygotowujemy polecenie git clone
            cmd = ["git", "clone"]

            # Dodajemy opcje
            if branch:
                cmd.extend(["-b", branch])

            if depth:
                cmd.extend(["--depth", str(depth)])

            # Dodajemy URL i ścieżkę docelową
            cmd.extend([url, target_path])

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas klonowania repozytorium: {process.stderr}")
                return False

            logger.info(f"Repozytorium zostało sklonowane pomyślnie do {target_path}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas klonowania repozytorium: {str(e)}")
            return False

    def clone_and_setup(self, url: str, target_path: str, branch: Optional[str] = None,
                        init_command: Optional[str] = None, post_clone_commands: List[str] = None) -> bool:
        """
        Klonuje repozytorium git i wykonuje polecenia po klonowaniu.
        
        Args:
            url: URL repozytorium.
            target_path: Ścieżka docelowa.
            branch: Nazwa gałęzi do sklonowania (opcjonalnie).
            init_command: Polecenie inicjalizacyjne (opcjonalnie).
            post_clone_commands: Lista poleceń do wykonania po klonowaniu (opcjonalnie).
            
        Returns:
            True, jeśli repozytorium zostało sklonowane i skonfigurowane pomyślnie, False w przeciwnym razie.
        """
        try:
            # Klonujemy repozytorium
            clone_result = self.clone_repository(url, target_path, branch)

            if not clone_result:
                return False

            # Wykonujemy polecenie inicjalizacyjne, jeśli podano
            if init_command:
                logger.info(f"Wykonywanie polecenia inicjalizacyjnego: {init_command}")

                init_process = subprocess.run(
                    init_command,
                    shell=True,
                    cwd=target_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if init_process.returncode != 0:
                    logger.error(f"Błąd podczas wykonywania polecenia inicjalizacyjnego: {init_process.stderr}")
                    return False

            # Wykonujemy polecenia po klonowaniu, jeśli podano
            if post_clone_commands:
                for i, command in enumerate(post_clone_commands, 1):
                    logger.info(f"Wykonywanie polecenia {i}/{len(post_clone_commands)}: {command}")

                    cmd_process = subprocess.run(
                        command,
                        shell=True,
                        cwd=target_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    if cmd_process.returncode != 0:
                        logger.error(f"Błąd podczas wykonywania polecenia {i}/{len(post_clone_commands)}: {cmd_process.stderr}")
                        return False

            logger.info(f"Repozytorium zostało sklonowane i skonfigurowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas klonowania i konfiguracji repozytorium: {str(e)}")
            return False

    def clone_with_dependencies(self, config: Dict[str, Any], base_path: str = ".") -> bool:
        """
        Klonuje repozytorium git wraz z zależnościami.
        
        Args:
            config: Konfiguracja repozytorium i zależności.
            base_path: Ścieżka bazowa dla klonowania (opcjonalnie).
            
        Returns:
            True, jeśli repozytorium i zależności zostały sklonowane pomyślnie, False w przeciwnym razie.
        """
        try:
            main_repo = config.get("main_repo", {})
            dependencies = config.get("dependencies", [])

            # Klonujemy główne repozytorium
            if main_repo:
                url = main_repo.get("url")
                rel_path = main_repo.get("path", ".")
                branch = main_repo.get("branch")

                if not url:
                    logger.error("Brak URL dla głównego repozytorium")
                    return False

                target_path = os.path.join(base_path, rel_path)

                logger.info(f"Klonowanie głównego repozytorium: {url}")
                if not self.clone_repository(url, target_path, branch):
                    return False

            # Klonujemy zależności
            for i, dep in enumerate(dependencies, 1):
                url = dep.get("url")
                rel_path = dep.get("path", f"deps/{i}")
                branch = dep.get("branch")

                if not url:
                    logger.warning(f"Brak URL dla zależności {i}, pomijam")
                    continue

                target_path = os.path.join(base_path, rel_path)

                logger.info(f"Klonowanie zależności {i}/{len(dependencies)}: {url}")
                self.clone_repository(url, target_path, branch)

            logger.info(f"Repozytorium i zależności zostały sklonowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas klonowania repozytorium z zależnościami: {str(e)}")
            return False