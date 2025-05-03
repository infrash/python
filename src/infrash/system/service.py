"""
service.py
"""

"""
        Uruchamia usługę systemową w systemie Linux.
        
        Args:
            service_name: Nazwa usługi.
            
        Returns:
            True, jeśli usługa została uruchomiona pomyślnie, False w przeciwnym razie.
        """
try:
    # Sprawdzamy, czy mamy uprawnienia administratora
    if not is_admin():
        logger.warning(f"Uruchomienie usługi {service_name} wymaga uprawnień administratora.")

        # Próbujemy użyć sudo
        if self._is_command_available("sudo"):
            cmd = ["sudo", "systemctl", "start", service_name]
        else:
            logger.error("Brak uprawnień administratora i brak polecenia sudo.")
            return False
    else:
        cmd = ["systemctl", "start", service_name]

    # Wykonujemy polecenie
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    # Sprawdzamy kod wyjścia
    if process.returncode != 0:
        logger.error(f"Błąd podczas uruchamiania usługi {service_name}: {process.stderr}")
        return False

    logger.info(f"Usługa {service_name} została uruchomiona pomyślnie.")
    return True

except Exception as e:
    logger.error(f"Błąd podczas uruchamiania usługi {service_name}: {str(e)}")
    return False

def _stop_service_linux(self, service_name: str) -> bool:
    """
    Zatrzymuje usługę systemową w systemie Linux.

    Args:
        service_name: Nazwa usługi.

    Returns:
        True, jeśli usługa została zatrzymana pomyślnie, False w przeciwnym razie.
    """
    try:
        # Sprawdzamy, czy mamy uprawnienia administratora
        if not is_admin():
            logger.warning(f"Zatrzymanie usługi {service_name} wymaga uprawnień administratora.")

            # Próbujemy użyć sudo
            if self._is_command_available("sudo"):
                cmd = ["sudo", "systemctl", "stop", service_name]
            else:
                logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                return False
        else:
            cmd = ["systemctl", "stop", service_name]

        # Wykonujemy polecenie
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Sprawdzamy kod wyjścia
        if process.returncode != 0:
            logger.error(f"Błąd podczas zatrzymywania usługi {service_name}: {process.stder#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł zarządzania usługami systemowymi. Umożliwia uruchamianie, zatrzymywanie
i monitorowanie usług systemowych.
"""

import os
import sys
import subprocess
import platform
import time
import shutil
import stat
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, is_admin

# Inicjalizacja loggera
logger = get_logger(__name__)

class ServiceManager:
    """
    Klasa zarządzająca usługami systemowymi.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję ServiceManager.
        """
        self.os_info = detect_os()
        self.os_type = self.os_info.get("type", "unknown").lower()

    def start_service(self, service_name: str) -> bool:
        """
        Uruchamia usługę systemową.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została uruchomiona pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Uruchamianie usługi: {service_name}")

        if "linux" in self.os_type:
            return self._start_service_linux(service_name)
        elif self.os_type == "macos":
            return self._start_service_macos(service_name)
        elif self.os_type == "windows":
            return self._start_service_windows(service_name)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """
        Zatrzymuje usługę systemową.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została zatrzymana pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Zatrzymywanie usługi: {service_name}")

        if "linux" in self.os_type:
            return self._stop_service_linux(service_name)
        elif self.os_type == "macos":
            return self._stop_service_macos(service_name)
        elif self.os_type == "windows":
            return self._stop_service_windows(service_name)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """
        Restartuje usługę systemową.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została zrestartowana pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Restartowanie usługi: {service_name}")

        if "linux" in self.os_type:
            return self._restart_service_linux(service_name)
        elif self.os_type == "macos":
            return self._restart_service_macos(service_name)
        elif self.os_type == "windows":
            return self._restart_service_windows(service_name)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return False

    def service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Sprawdza status usługi systemowej.

        Args:
            service_name: Nazwa usługi.

        Returns:
            Słownik ze statusem usługi.
        """
        logger.info(f"Sprawdzanie statusu usługi: {service_name}")

        if "linux" in self.os_type:
            return self._service_status_linux(service_name)
        elif self.os_type == "macos":
            return self._service_status_macos(service_name)
        elif self.os_type == "windows":
            return self._service_status_windows(service_name)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return {"status": "unknown", "error": f"Nieobsługiwany system operacyjny: {self.os_type}"}

    def create_service(self, service_name: str, command: str, description: str = "", auto_start: bool = True) -> bool:
        """
        Tworzy nową usługę systemową.

        Args:
            service_name: Nazwa usługi.
            command: Polecenie uruchamiające usługę.
            description: Opis usługi (opcjonalne).
            auto_start: Czy usługa ma być uruchamiana automatycznie po starcie systemu (opcjonalne).

        Returns:
            True, jeśli usługa została utworzona pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Tworzenie usługi: {service_name}")

        if "linux" in self.os_type:
            return self._create_service_linux(service_name, command, description, auto_start)
        elif self.os_type == "macos":
            return self._create_service_macos(service_name, command, description, auto_start)
        elif self.os_type == "windows":
            return self._create_service_windows(service_name, command, description, auto_start)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return False

    def delete_service(self, service_name: str) -> bool:
        """
        Usuwa usługę systemową.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została usunięta pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Usuwanie usługi: {service_name}")

        if "linux" in self.os_type:
            return self._delete_service_linux(service_name)
        elif self.os_type == "macos":
            return self._delete_service_macos(service_name)
        elif self.os_type == "windows":
            return self._delete_service_windows(service_name)
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return False

    def list_services(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę usług systemowych.

        Returns:
            Lista słowników opisujących usługi.
        """
        logger.info("Pobieranie listy usług systemowych")

        if "linux" in self.os_type:
            return self._list_services_linux()
        elif self.os_type == "macos":
            return self._list_services_macos()
        elif self.os_type == "windows":
            return self._list_services_windows()
        else:
            logger.error(f"Nieobsługiwany system operacyjny: {self.os_type}")
            return []

    def _start_service_linux(self, service_name: str) -> bool:
        """
        Uruchamia usługę systemową w systemie Linux.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True