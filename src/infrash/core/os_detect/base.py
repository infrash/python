#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego - funkcje bazowe.
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