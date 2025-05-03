#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego - wykrywanie menedżera pakietów.
"""

import os
import sys
import platform
import subprocess
from typing import Dict, List, Any, Optional

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def get_package_manager() -> str:
    """
    Wykrywa menedżera pakietów.
    
    Returns:
        Nazwa menedżera pakietów.
    """
    system = platform.system()

    if system == "Linux":
        # Sprawdzamy dostępne menedżery pakietów
        package_managers = {
            "apt-get": ["apt-get", "--version"],
            "apt": ["apt", "--version"],
            "yum": ["yum", "--version"],
            "dnf": ["dnf", "--version"],
            "pacman": ["pacman", "--version"],
            "zypper": ["zypper", "--version"],
            "apk": ["apk", "--version"]
        }

        for pm_name, pm_cmd in package_managers.items():
            try:
                process = subprocess.run(
                    pm_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process.returncode == 0:
                    logger.debug(f"Wykryto menedżera pakietów: {pm_name}")
                    return pm_name
            except Exception:
                pass

        # Jeśli nie wykryto żadnego menedżera pakietów, zwracamy apt-get jako domyślny
        logger.warning("Nie wykryto menedżera pakietów. Używam apt-get jako domyślnego.")
        return "apt-get"

    elif system == "Darwin":
        # macOS - sprawdzamy, czy zainstalowany jest Homebrew
        try:
            process = subprocess.run(
                ["brew", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode == 0:
                logger.debug("Wykryto menedżera pakietów: brew")
                return "brew"
        except Exception:
            pass

        # Jeśli nie zainstalowano Homebrew, zwracamy brew jako domyślny (trzeba będzie go zainstalować)
        logger.warning("Nie wykryto menedżera pakietów Homebrew. Używam brew jako domyślnego.")
        return "brew"

    elif system == "Windows":
        # Windows - sprawdzamy, czy zainstalowany jest Chocolatey
        try:
            process = subprocess.run(
                ["choco", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode == 0:
                logger.debug("Wykryto menedżera pakietów: choco")
                return "choco"
        except Exception:
            pass

        # Jeśli nie zainstalowano Chocolatey, sprawdzamy winget
        try:
            process = subprocess.run(
                ["winget", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode == 0:
                logger.debug("Wykryto menedżera pakietów: winget")
                return "winget"
        except Exception:
            pass

        # Jeśli nie zainstalowano Chocolatey ani winget, zwracamy pip jako domyślny
        logger.warning("Nie wykryto menedżera pakietów Chocolatey ani winget. Używam pip jako domyślnego.")
        return "pip"

    else:
        # Nieznany system - używamy pip jako domyślnego
        logger.warning(f"Nieznany system operacyjny: {system}. Używam pip jako domyślnego menedżera pakietów.")
        return "pip"