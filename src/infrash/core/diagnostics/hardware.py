#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - rozwiązywanie problemów sprzętowych.
"""

import os
import uuid
import platform
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def analyze_hardware_issues(error_message: str, hardware_type: str) -> Dict[str, Any]:
    """
    Analizuje i rozwiązuje problemy sprzętowe.

    Args:
        error_message: Komunikat o błędzie.
        hardware_type: Typ sprzętu (gpio, audio, camera, itp.).

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    result = {
        "id": str(uuid.uuid4()),
        "title": f"Problem ze sprzętem: {hardware_type}",
        "description": f"Wystąpił problem związany ze sprzętem typu {hardware_type}: {error_message}",
        "solution": "Sprawdź, czy sprzęt jest prawidłowo podłączony i czy sterowniki są zainstalowane.",
        "severity": "error",
        "category": "hardware",
        "metadata": {
            "error_message": error_message,
            "hardware_type": hardware_type
        }
    }

    # Problem 1: GPIO nie jest dostępne (zwykle na Raspberry Pi)
    if hardware_type == "gpio" and ("ImportError: No module named 'RPi.GPIO'" in error_message or "ImportError: No module named 'RPi'" in error_message):
        result["title"] = "Brak modułu RPi.GPIO"
        result["description"] = "Nie można zaimportować modułu RPi.GPIO, który jest wymagany do obsługi GPIO."

        # Sprawdzamy, czy jesteśmy na Raspberry Pi
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            is_raspberry_pi = 'BCM2708' in cpuinfo or 'BCM2709' in cpuinfo or 'BCM2711' in cpuinfo or 'BCM2835' in cpuinfo
        except:
            pass

        if is_raspberry_pi:
            result["solution"] = "Zainstaluj moduł RPi.GPIO: 'pip install RPi.GPIO' lub 'sudo apt-get install python3-rpi.gpio'"
        else:
            result["solution"] = "Ten program wymaga Raspberry Pi. Jeśli używasz Raspberry Pi, zainstaluj moduł RPi.GPIO."

    # Problem 2: GPIO wymaga uprawnień roota
    elif hardware_type == "gpio" and "Permission denied" in error_message:
        result["title"] = "Brak uprawnień do GPIO"
        result["description"] = "Brak uprawnień do dostępu do GPIO."
        result["solution"] = "Uruchom program z uprawnieniami roota (sudo) lub dodaj użytkownika do grupy gpio."

    # Problem 3: Audio - brak urządzenia audio
    elif hardware_type == "audio" and ("No such file or directory" in error_message or "No default output device available" in error_message):
        result["title"] = "Brak urządzenia audio"
        result["description"] = "Nie znaleziono urządzenia audio."
        result["solution"] = "Sprawdź, czy urządzenie audio jest prawidłowo podłączone i wykrywane przez system."

        # Na Raspberry Pi często trzeba włączyć urządzenie audio
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            is_raspberry_pi = 'BCM2708' in cpuinfo or 'BCM2709' in cpuinfo or 'BCM2711' in cpuinfo or 'BCM2835' in cpuinfo
        except:
            pass

        if is_raspberry_pi:
            result["solution"] = ("Włącz urządzenie audio w konfiguracji Raspberry Pi: "
                                  "1. Uruchom 'sudo raspi-config' "
                                  "2. Wybierz 'System Options' > 'Audio' "
                                  "3. Wybierz odpowiednie urządzenie audio")

    # Problem 4: Audio - błąd podczas inicjalizacji PyAudio
    elif hardware_type == "audio" and "ImportError: No module named 'pyaudio'" in error_message:
        result["title"] = "Brak modułu PyAudio"
        result["description"] = "Nie można zaimportować modułu PyAudio, który jest wymagany do obsługi dźwięku."

        # PyAudio wymaga biblioteki systemowej portaudio
        if platform.system() == "Linux":
            result["solution"] = "Zainstaluj PyAudio i wymagane zależności: 'sudo apt-get install python3-pyaudio portaudio19-dev' i 'pip install pyaudio'"
        elif platform.system() == "Windows":
            result["solution"] = "Zainstaluj PyAudio: 'pip install pyaudio'"
        elif platform.system() == "Darwin":  # macOS
            result["solution"] = "Zainstaluj PyAudio i wymagane zależności: 'brew install portaudio' i 'pip install pyaudio'"

    # Problem 5: Camera - brak urządzenia kamery
    elif hardware_type == "camera" and ("No camera found" in error_message or "Can't open camera" in error_message):
        result["title"] = "Brak urządzenia kamery"
        result["description"] = "Nie znaleziono urządzenia kamery."
        result["solution"] = "Sprawdź, czy kamera jest prawidłowo podłączona i wykrywana przez system."

        # Na Raspberry Pi często trzeba włączyć kamerę
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            is_raspberry_pi = 'BCM2708' in cpuinfo or 'BCM2709' in cpuinfo or 'BCM2711' in cpuinfo or 'BCM2835' in cpuinfo
        except:
            pass

        if is_raspberry_pi:
            result["solution"] = ("Włącz kamerę w konfiguracji Raspberry Pi: "
                                  "1. Uruchom 'sudo raspi-config' "
                                  "2. Wybierz 'Interface Options' > 'Camera' "
                                  "3. Włącz kamerę i zrestartuj Raspberry Pi")

    # Problem 6: Camera - błąd podczas inicjalizacji modułu kamery
    elif hardware_type == "camera" and "ImportError: No module named 'picamera'" in error_message:
        result["title"] = "Brak modułu picamera"
        result["description"] = "Nie można zaimportować modułu picamera, który jest wymagany do obsługi kamery Raspberry Pi."
        result["solution"] = "Zainstaluj moduł picamera: 'pip install picamera' lub 'sudo apt-get install python3-picamera'"

    # Problem 7: I2C - błąd podczas komunikacji z urządzeniem I2C
    elif hardware_type == "i2c" and ("ImportError: No module named 'smbus'" in error_message or "ImportError: No module named 'smbus2'" in error_message):
        result["title"] = "Brak modułu SMBus"
        result["description"] = "Nie można zaimportować modułu SMBus, który jest wymagany do komunikacji I2C."

        # Na Raspberry Pi często trzeba włączyć I2C
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            is_raspberry_pi = 'BCM2708' in cpuinfo or 'BCM2709' in cpuinfo or 'BCM2711' in cpuinfo or 'BCM2835' in cpuinfo
        except:
            pass

        if is_raspberry_pi:
            result["solution"] = ("Włącz I2C i zainstaluj wymagane pakiety: "
                                  "1. Uruchom 'sudo raspi-config' "
                                  "2. Wybierz 'Interface Options' > 'I2C' "
                                  "3. Włącz I2C "
                                  "4. Zainstaluj wymagane pakiety: 'sudo apt-get install python3-smbus i2c-tools'")
        else:
            result["solution"] = "Zainstaluj moduł SMBus: 'pip install smbus2'"

    return result