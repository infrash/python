# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego i menedżera pakietów.
"""

import os
import sys
import platform
import subprocess
import re
from typing import Dict, List, Any, Optional

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def detect_os() -> Dict[str, str]:
    """
    Wykrywa system operacyjny.

    Returns:
        Słownik z informacjami o systemie operacyjnym.
    """
    system = platform.system()
    result = {
        "name": system,
        "version": "",
        "type": system.lower()
    }

    try:
        if system == "Linux":
            # Sprawdzamy dystrybucję Linux
            if os.path.isfile("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    lines = f.readlines()

                for line in lines:
                    if line.startswith("ID="):
                        result["type"] = line.split("=")[1].strip().strip('"').lower()
                    elif line.startswith("VERSION_ID="):
                        result["version"] = line.split("=")[1].strip().strip('"')
                    elif line.startswith("PRETTY_NAME="):
                        result["name"] = line.split("=")[1].strip().strip('"')

            # Jeśli nie udało się ustalić wersji, próbujemy pobrać ją z uname
            if not result["version"]:
                uname = platform.uname()
                result["version"] = uname.release

        elif system == "Darwin":
            # macOS
            result["type"] = "macos"

            # Pobieramy wersję macOS
            cmd = ["sw_vers", "-productVersion"]

            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process.returncode == 0:
                    result["version"] = process.stdout.strip()

                    # Ustalamy nazwę wersji
                    macos_versions = {
                        "10.15": "Catalina",
                        "11": "Big Sur",
                        "12": "Monterey",
                        "13": "Ventura",
                        "14": "Sonoma"
                    }

                    major_version = result["version"].split(".")[0]
                    if major_version in macos_versions:
                        result["name"] = f"macOS {macos_versions[major_version]}"
                    else:
                        result["name"] = f"macOS {result['version']}"
            except Exception as e:
                logger.error(f"Błąd podczas pobierania wersji macOS: {str(e)}")

        elif system == "Windows":
            # Windows
            result["type"] = "windows"

            # Pobieramy wersję Windows
            version = platform.version()
            result["version"] = version

            # Ustalamy nazwę wersji
            windows_versions = {
                "10.0": "Windows 10/11",
                "6.3": "Windows 8.1",
                "6.2": "Windows 8",
                "6.1": "Windows 7",
                "6.0": "Windows Vista",
                "5.2": "Windows XP 64-bit",
                "5.1": "Windows XP",
                "5.0": "Windows 2000"
            }

            major_version = ".".join(version.split(".")[:2])
            if major_version in windows_versions:
                result["name"] = windows_versions[major_version]
            else:
                result["name"] = f"Windows {version}"

        else:
            # Nieznany system
            result["name"] = system
            result["version"] = platform.version()
            result["type"] = system.lower()

    except Exception as e:
        logger.error(f"Błąd podczas wykrywania systemu operacyjnego: {str(e)}")

    return result

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
            process_winget = subprocess.run(
                ["winget", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process_winget.returncode == 0:
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

def is_admin() -> bool:
    """
    Sprawdza, czy skrypt jest uruchomiony z uprawnieniami administratora.

    Returns:
        True, jeśli skrypt jest uruchomiony z uprawnieniami administratora, False w przeciwnym razie.
    """
    system = platform.system()

    if system == "Windows":
        try:
            # Windows
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False

def get_python_version() -> str:
    """
    Pobiera wersję Pythona.

    Returns:
        Wersja Pythona.
    """
    return platform.python_version()

def is_virtual_env() -> bool:
    """
    Sprawdza, czy skrypt jest uruchomiony w wirtualnym środowisku Pythona.

    Returns:
        True, jeśli skrypt jest uruchomiony w wirtualnym środowisku, False w przeciwnym razie.
    """
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)

def is_raspberry_pi() -> bool:
    """
    Sprawdza, czy system działa na Raspberry Pi.

    Returns:
        True, jeśli system działa na Raspberry Pi, False w przeciwnym razie.
    """
    # Sprawdzamy, czy istnieje plik /proc/cpuinfo
    if not os.path.isfile("/proc/cpuinfo"):
        return False

    try:
        # Odczytujemy zawartość pliku /proc/cpuinfo
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()

        # Sprawdzamy, czy zawiera informacje o procesorze Broadcom używanym w Raspberry Pi
        return any(processor in cpuinfo for processor in ["BCM2708", "BCM2709", "BCM2711", "BCM2835", "BCM2836", "BCM2837"])
    except Exception:
        return False

def is_available_command(command: str) -> bool:
    """
    Sprawdza, czy polecenie jest dostępne w systemie.

    Args:
        command: Nazwa polecenia.

    Returns:
        True, jeśli polecenie jest dostępne, False w przeciwnym razie.
    """
    try:
        # Sprawdzamy, czy polecenie jest dostępne
        if platform.system() == "Windows":
            # W Windows używamy where
            process = subprocess.run(
                ["where", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        else:
            # W Unix używamy which
            process = subprocess.run(
                ["which", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

        return process.returncode == 0
    except Exception:
        return False#!/usr/bin/env python3
