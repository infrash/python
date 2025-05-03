#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - wykonywanie poleceń i modyfikacja plików.
"""

import os
import subprocess
import re
import shutil
from typing import Dict, List, Any

from infrash.utils.logger import get_logger
from infrash.system.dependency import install_dependency

# Inicjalizacja loggera
logger = get_logger(__name__)

def _run_command(self, command: str) -> bool:
    """
    Wykonuje polecenie.

    Args:
        command: Polecenie do wykonania.

    Returns:
        True, jeśli polecenie zostało wykonane pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Wykonywanie polecenia: {command}")

        # Wykonujemy polecenie
        process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Sprawdzamy kod wyjścia
        if process.returncode != 0:
            logger.error(f"Polecenie zakończyło się błędem (kod {process.returncode}): {process.stderr}")
            return False

        logger.info(f"Polecenie wykonane pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas wykonywania polecenia: {str(e)}")
        return False

def _modify_file(self, file_path: str, pattern: str, replacement: str) -> bool:
    """
    Modyfikuje plik, zastępując wzorzec nowym tekstem.

    Args:
        file_path: Ścieżka do pliku.
        pattern: Wzorzec do zastąpienia (wyrażenie regularne).
        replacement: Tekst zastępujący.

    Returns:
        True, jeśli plik został zmodyfikowany pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Modyfikowanie pliku: {file_path}")

        # Sprawdzamy, czy plik istnieje
        if not os.path.isfile(file_path):
            logger.error(f"Plik nie istnieje: {file_path}")
            return False

        # Tworzymy kopię zapasową pliku
        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)

        # Odczytujemy zawartość pliku
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Zastępujemy wzorzec
        new_content = re.sub(pattern, replacement, content)

        # Jeśli zawartość nie uległa zmianie, nie zapisujemy pliku
        if new_content == content:
            logger.warning(f"Plik nie został zmodyfikowany (wzorzec nie znaleziony): {file_path}")
            os.unlink(backup_path)  # Usuwamy kopię zapasową
            return False

        # Zapisujemy zmodyfikowaną zawartość
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info(f"Plik został zmodyfikowany pomyślnie: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas modyfikowania pliku: {str(e)}")

        # Przywracamy kopię zapasową, jeśli istnieje
        if 'backup_path' in locals() and os.path.isfile(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(f"Przywrócono kopię zapasową pliku: {file_path}")
            except Exception as e2:
                logger.error(f"Błąd podczas przywracania kopii zapasowej: {str(e2)}")

        return False

def _create_file(self, file_path: str, content: str) -> bool:
    """
    Tworzy nowy plik z podaną zawartością.

    Args:
        file_path: Ścieżka do pliku.
        content: Zawartość pliku.

    Returns:
        True, jeśli plik został utworzony pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Tworzenie pliku: {file_path}")

        # Tworzymy katalog, jeśli nie istnieje
        directory = os.path.dirname(file_path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)

        # Zapisujemy zawartość do pliku
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Plik został utworzony pomyślnie: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia pliku: {str(e)}")
        return False

def _install_package(self, package_name: str, package_manager: str = None) -> bool:
    """
    Instaluje pakiet za pomocą menedżera pakietów.

    Args:
        package_name: Nazwa pakietu.
        package_manager: Nazwa menedżera pakietów (opcjonalne).

    Returns:
        True, jeśli pakiet został zainstalowany pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Instalowanie pakietu: {package_name}")

        # Jeśli nie podano menedżera pakietów, używamy domyślnego
        if not package_manager:
            package_manager = self.package_manager

        # Instalujemy pakiet
        result = install_dependency(package_name, package_manager)

        if result:
            logger.info(f"Pakiet został zainstalowany pomyślnie: {package_name}")
            return True
        else:
            logger.error(f"Nie udało się zainstalować pakietu: {package_name}")
            return False

    except Exception as e:
        logger.error(f"Błąd podczas instalacji pakietu: {str(e)}")
        return False