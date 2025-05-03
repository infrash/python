#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego - funkcje narzędziowe.
"""

import os
import sys
import platform
import subprocess
from typing import Dict, List, Any, Optional

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

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
        return False