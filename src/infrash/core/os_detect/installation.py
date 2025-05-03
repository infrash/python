#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego - instalacja menedżera pakietów.
"""

import os
import sys
import platform
import subprocess
from typing import Dict, List, Any, Optional

from infrash.utils.logger import get_logger
from infrash.system.os_detect.base import detect_os, is_admin

# Inicjalizacja loggera
logger = get_logger(__name__)

def install_package_manager() -> bool:
    """
    Instaluje domyślny menedżer pakietów dla danego systemu operacyjnego.

    Returns:
        True, jeśli menedżer pakietów został zainstalowany pomyślnie, False w przeciwnym razie.
    """
    system = platform.system()

    if system == "Linux":
        # Linux ma zazwyczaj zainstalowany domyślny menedżer pakietów
        # Sprawdzamy typ dystrybucji
        os_info = detect_os()
        os_type = os_info.get("type", "").lower()

        if "debian" in os_type or "ubuntu" in os_type:
            # Debian/Ubuntu - apt-get
            try:
                process = subprocess.run(
                    ["apt-get", "update"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                return process.returncode == 0
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji apt-get: {str(e)}")
                return False

        elif "fedora" in os_type or "centos" in os_type or "rhel" in os_type:
            # Fedora/CentOS/RHEL - dnf/yum
            try:
                # Sprawdzamy, czy jest dnf (nowszy)
                try:
                    process_dnf = subprocess.run(
                        ["dnf", "check-update"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    return process_dnf.returncode == 0 or process_dnf.returncode == 100  # 100 oznacza dostępne aktualizacje
                except Exception:
                    # Jeśli nie ma dnf, używamy yum
                    process_yum = subprocess.run(
                        ["yum", "check-update"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    return process_yum.returncode == 0 or process_yum.returncode == 100  # 100 oznacza dostępne aktualizacje
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania dnf/yum: {str(e)}")
                return False

        elif "arch" in os_type:
            # Arch Linux - pacman
            try:
                process = subprocess.run(
                    ["pacman", "-Sy"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                return process.returncode == 0
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji pacman: {str(e)}")
                return False

        elif "alpine" in os_type:
            # Alpine Linux - apk
            try:
                process = subprocess.run(
                    ["apk", "update"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                return process.returncode == 0
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji apk: {str(e)}")
                return False

        else:
            # Nieznana dystrybucja - próbujemy apt-get jako najczęściej używany
            try:
                process = subprocess.run(
                    ["apt-get", "update"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                return process.returncode == 0
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji apt-get: {str(e)}")
                return False

    elif system == "Darwin":
        # macOS - instalujemy Homebrew
        try:
            # Sprawdzamy, czy Homebrew jest już zainstalowany
            try:
                process_check = subprocess.run(
                    ["brew", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process_check.returncode == 0:
                    logger.info("Homebrew jest już zainstalowany.")
                    return True
            except Exception:
                # Homebrew nie jest zainstalowany, instalujemy go
                logger.info("Instalowanie Homebrew...")

                # Polecenie instalacji Homebrew
                # Polecenie instalacji Homebrew
                install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

                process_install = subprocess.run(
                    install_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process_install.returncode == 0:
                    logger.info("Homebrew został zainstalowany pomyślnie.")
                    return True
                else:
                    logger.error(f"Błąd podczas instalacji Homebrew: {process_install.stderr}")
                    return False
        except Exception as e:
            logger.error(f"Błąd podczas instalacji Homebrew: {str(e)}")
            return False

    elif system == "Windows":
        # Windows - instalujemy Chocolatey
        try:
            # Sprawdzamy, czy Chocolatey jest już zainstalowany
            try:
                process_check = subprocess.run(
                    ["choco", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process_check.returncode == 0:
                    logger.info("Chocolatey jest już zainstalowany.")
                    return True
            except Exception:
                # Sprawdzamy, czy winget jest zainstalowany
                try:
                    process_winget = subprocess.run(
                        ["winget", "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    if process_winget.returncode == 0:
                        logger.info("Winget jest już zainstalowany.")
                        return True
                except Exception:
                    # Ani Chocolatey, ani winget nie są zainstalowane
                    # Instalujemy Chocolatey
                    logger.info("Instalowanie Chocolatey...")

                    # Polecenie instalacji Chocolatey (wymaga PowerShell z uprawnieniami administratora)
                    install_cmd = 'powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString(\'https://community.chocolatey.org/install.ps1\'))"'

                    process_install = subprocess.run(
                        install_cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    if process_install.returncode == 0:
                        logger.info("Chocolatey został zainstalowany pomyślnie.")
                        return True
                    else:
                        logger.error(f"Błąd podczas instalacji Chocolatey: {process_install.stderr}")
                        logger.warning("Używam pip jako alternatywnego menedżera pakietów.")
                        return False
        except Exception as e:
            logger.error(f"Błąd podczas instalacji Chocolatey: {str(e)}")
            return False

    else:
        # Nieznany system - używamy pip
        logger.warning(f"Nieznany system operacyjny: {system}. Używam pip jako menedżera pakietów.")

        # Sprawdzamy, czy pip jest zainstalowany
        try:
            process = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode == 0:
                logger.info("Pip jest już zainstalowany.")
                return True
            else:
                logger.error("Pip nie jest zainstalowany i nie można go automatycznie zainstalować na nieznanym systemie.")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania pip: {str(e)}")
            return False