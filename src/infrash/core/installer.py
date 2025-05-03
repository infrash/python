#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł instalatora infrash. Umożliwia instalację zależności i konfigurację
środowiska projektowego.
"""

import os
import sys
import subprocess
import platform
import re
import yaml
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import check_dependencies, install_dependency, create_virtual_env

# Inicjalizacja loggera
logger = get_logger(__name__)

class Installer:
    """
    Klasa instalatora do instalacji zależności i konfiguracji środowiska.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Installer.
        """
        self.os_info = detect_os()
        self.package_manager = get_package_manager()

    def install_dependencies(self, project_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności projektu.
        
        Args:
            project_path: Ścieżka do projektu.
            force: Czy wymusić reinstalację istniejących zależności.
            
        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności dla projektu w {project_path}")

        # Sprawdzamy, czy katalog projektu istnieje
        if not os.path.isdir(project_path):
            logger.error(f"Katalog projektu {project_path} nie istnieje")
            return False

        # Sprawdzamy brakujące zależności
        if not force:
            missing_deps = check_dependencies(project_path)

            if not missing_deps:
                logger.info("Wszystkie zależności są już zainstalowane")
                return True

        # Znajdujemy pliki z zależnościami
        dependency_files = self._find_dependency_files(project_path)

        if not dependency_files:
            logger.warning(f"Nie znaleziono plików z zależnościami w {project_path}")
            return False

        # Instalujemy zależności z każdego pliku
        success = True
        for dep_file in dependency_files:
            file_path = os.path.join(project_path, dep_file)

            if not os.path.isfile(file_path):
                continue

            try:
                if dep_file.endswith('.txt'):
                    self._install_from_requirements_txt(file_path, force)
                elif dep_file.endswith('.toml'):
                    self._install_from_pyproject_toml(file_path, force)
                elif dep_file.endswith('.py') and 'setup.py' in dep_file:
                    self._install_from_setup_py(file_path, force)
                elif dep_file.endswith('.cfg') and 'setup.cfg' in dep_file:
                    self._install_from_setup_cfg(file_path, force)
                elif dep_file.endswith('.json') and 'package.json' in dep_file:
                    self._install_from_package_json(file_path, force)
                else:
                    continue
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności z {dep_file}: {str(e)}")
                success = False

        # Sprawdzamy, czy wszystkie zależności zostały zainstalowane
        missing_deps_after = check_dependencies(project_path)

        if missing_deps_after:
            logger.warning(f"Nie udało się zainstalować wszystkich zależności: {', '.join(missing_deps_after)}")
            success = False

        return success

    def _find_dependency_files(self, project_path: str) -> List[str]:
        """
        Znajduje pliki z zależnościami w projekcie.
        
        Args:
            project_path: Ścieżka do projektu.
            
        Returns:
            Lista ścieżek do plików z zależnościami.
        """
        dependency_files = []

        # Typowe pliki z zależnościami
        common_files = [
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "package.json",
            "Pipfile",
            "poetry.lock",
            "environment.yml"
        ]

        # Sprawdzamy, czy pliki istnieją
        for file in common_files:
            if os.path.isfile(os.path.join(project_path, file)):
                dependency_files.append(file)

        # Szukamy requirements*.txt
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.startswith("requirements") and file.endswith(".txt") and file not in dependency_files:
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    dependency_files.append(rel_path)

        return dependency_files

    def _install_from_requirements_txt(self, file_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku requirements.txt.
        
        Args:
            file_path: Ścieżka do pliku requirements.txt.
            force: Czy wymusić reinstalację istniejących zależności.
            
        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności z {file_path}")

        try:
            # Przygotowujemy polecenie pip install
            cmd = [sys.executable, "-m", "pip", "install", "-r", file_path]

            # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
            if force:
                cmd.append("--force-reinstall")

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            logger.info(f"Zależności z pliku {file_path} zostały zainstalowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
            return False

    def _install_from_pyproject_toml(self, file_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku pyproject.toml.

        Args:
            file_path: Ścieżka do pliku pyproject.toml.
            force: Czy wymusić reinstalację istniejących zależności.

        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności z {file_path}")

        try:
            # Sprawdzamy, czy mamy zainstalowane narzędzie do instalacji projektów z pyproject.toml
            pip_tools = False
            poetry = False

            try:
                # Sprawdzamy pip-tools
                pip_tools_process = subprocess.run(
                    [sys.executable, "-m", "pip", "show", "pip-tools"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                pip_tools = pip_tools_process.returncode == 0

                # Sprawdzamy poetry
                poetry_process = subprocess.run(
                    ["poetry", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                poetry = poetry_process.returncode == 0
            except Exception:
                pass

            # Przygotowujemy polecenie instalacji
            if poetry:
                # Używamy poetry
                cmd = ["poetry", "install"]

                # Dodajemy opcję --force, jeśli wybrano wymuszenie
                if force:
                    cmd.append("--force")

                # Wykonujemy polecenie w katalogu projektu
                process = subprocess.run(
                    cmd,
                    cwd=os.path.dirname(file_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            else:
                # Używamy pip
                cmd = [sys.executable, "-m", "pip", "install", "-e", os.path.dirname(file_path)]

                # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
                if force:
                    cmd.append("--force-reinstall")

                # Wykonujemy polecenie
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            logger.info(f"Zależności z pliku {file_path} zostały zainstalowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
            return False

    def _install_from_setup_py(self, file_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku setup.py.

        Args:
            file_path: Ścieżka do pliku setup.py.
            force: Czy wymusić reinstalację istniejących zależności.

        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności z {file_path}")

        try:
            # Przygotowujemy polecenie pip install
            cmd = [sys.executable, "-m", "pip", "install", "-e", os.path.dirname(file_path)]

            # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
            if force:
                cmd.append("--force-reinstall")

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            logger.info(f"Zależności z pliku {file_path} zostały zainstalowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
            return False

    def _install_from_setup_cfg(self, file_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku setup.cfg.

        Args:
            file_path: Ścieżka do pliku setup.cfg.
            force: Czy wymusić reinstalację istniejących zależności.

        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności z {file_path}")

        try:
            # Przygotowujemy polecenie pip install
            cmd = [sys.executable, "-m", "pip", "install", "-e", os.path.dirname(file_path)]

            # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
            if force:
                cmd.append("--force-reinstall")

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            logger.info(f"Zależności z pliku {file_path} zostały zainstalowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
            return False

    def _install_from_package_json(self, file_path: str, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku package.json.

        Args:
            file_path: Ścieżka do pliku package.json.
            force: Czy wymusić reinstalację istniejących zależności.

        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności z {file_path}")

        try:
            # Sprawdzamy, czy mamy zainstalowane npm lub yarn
            npm = False
            yarn = False

            try:
                # Sprawdzamy npm
                npm_process = subprocess.run(
                    ["npm", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                npm = npm_process.returncode == 0

                # Sprawdzamy yarn
                yarn_process = subprocess.run(
                    ["yarn", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                yarn = yarn_process.returncode == 0
            except Exception:
                pass

            # Jeśli nie mamy ani npm, ani yarn, nie możemy zainstalować zależności
            if not npm and not yarn:
                logger.error("Brak zainstalowanego npm lub yarn. Nie można zainstalować zależności JavaScript.")
                return False

            # Przygotowujemy polecenie instalacji
            if yarn:
                # Używamy yarn
                cmd = ["yarn", "install"]

                # Dodajemy opcję --force, jeśli wybrano wymuszenie
                if force:
                    cmd.append("--force")
            else:
                # Używamy npm
                cmd = ["npm", "install"]

                # Dodajemy opcję --force, jeśli wybrano wymuszenie
                if force:
                    cmd.append("--force")

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                cwd=os.path.dirname(file_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
                return False

            logger.info(f"Zależności JavaScript z pliku {file_path} zostały zainstalowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności JavaScript: {str(e)}")
            return False

    def create_and_setup_venv(self, project_path: str, venv_path: Optional[str] = None,
                              python_version: Optional[str] = None, requirements: Optional[str] = None) -> bool:
        """
        Tworzy i konfiguruje wirtualne środowisko Python.

        Args:
            project_path: Ścieżka do projektu.
            venv_path: Ścieżka do wirtualnego środowiska (opcjonalnie).
            python_version: Wersja Pythona (opcjonalnie).
            requirements: Ścieżka do pliku requirements.txt (opcjonalnie).

        Returns:
            True, jeśli wirtualne środowisko zostało utworzone i skonfigurowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Tworzenie wirtualnego środowiska dla projektu w {project_path}")

        # Określamy ścieżkę do wirtualnego środowiska
        if not venv_path:
            venv_path = os.path.join(project_path, "venv")

        # Tworzymy wirtualne środowisko
        if not create_virtual_env(venv_path, python_version):
            logger.error("Nie udało się utworzyć wirtualnego środowiska")
            return False

        # Określamy ścieżkę do interpretera Pythona w wirtualnym środowisku
        if platform.system() == "Windows":
            python_path = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            python_path = os.path.join(venv_path, "bin", "python")

        # Aktualizujemy pip
        try:
            subprocess.run(
                [python_path, "-m", "pip", "install", "--upgrade", "pip"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji pip: {str(e)}")

        # Instalujemy zależności z pliku requirements.txt, jeśli podano
        if requirements:
            try:
                req_path = os.path.join(project_path, requirements)

                if os.path.isfile(req_path):
                    logger.info(f"Instalacja zależności z {req_path}")

                    process = subprocess.run(
                        [python_path, "-m", "pip", "install", "-r", req_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    if process.returncode != 0:
                        logger.error(f"Błąd podczas instalacji zależności: {process.stderr}")
                        return False

                    logger.info("Zależności zostały zainstalowane pomyślnie")
                else:
                    logger.warning(f"Plik {req_path} nie istnieje")
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
                return False

        logger.info(f"Wirtualne środowisko zostało utworzone i skonfigurowane pomyślnie w {venv_path}")
        return True

    def install_system_dependencies(self, dependencies: List[str]) -> bool:
        """
        Instaluje zależności systemowe.

        Args:
            dependencies: Lista zależności do zainstalowania.

        Returns:
            True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja zależności systemowych: {', '.join(dependencies)}")

        # Przygotowujemy polecenie instalacji w zależności od systemu
        success = True

        for dependency in dependencies:
            try:
                # Instalujemy zależność
                result = install_dependency(dependency, self.package_manager)

                if not result:
                    logger.error(f"Nie udało się zainstalować zależności: {dependency}")
                    success = False
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności {dependency}: {str(e)}")
                success = False

        return success