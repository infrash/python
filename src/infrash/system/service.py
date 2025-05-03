#!/usr/bin/env python3
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

    def _start_service_linux(self, service_name: str) -> bool:
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
                logger.error(f"Błąd podczas zatrzymywania usługi {service_name}: {process.stderr}")
                return False

            logger.info(f"Usługa {service_name} została zatrzymana pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania usługi {service_name}: {str(e)}")
            return False

    def _start_service_macos(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu macOS
        pass

    def _stop_service_macos(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu macOS
        pass

    def _start_service_windows(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu Windows
        pass

    def _stop_service_windows(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu Windows
        pass

    def _is_command_available(self, command: str) -> bool:
        """
        Sprawdza, czy polecenie jest dostępne w systemie.

        Args:
            command: Nazwa polecenia.

        Returns:
            True, jeśli polecenie jest dostępne, False w przeciwnym razie.
        """
        try:
            if platform.system() == "Windows":
                process = subprocess.run(
                    ["where", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            else:
                process = subprocess.run(
                    ["which", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            return process.returncode == 0
        except Exception:
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

    def _restart_service_linux(self, service_name: str) -> bool:
        """
        Restartuje usługę systemową w systemie Linux.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została zrestartowana pomyślnie, False w przeciwnym razie.
        """
        try:
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                logger.warning(f"Restart usługi {service_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if self._is_command_available("sudo"):
                    cmd = ["sudo", "systemctl", "restart", service_name]
                else:
                    logger.error("Brak uprawnien administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = ["systemctl", "restart", service_name]

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas restartowania usługi {service_name}: {process.stderr}")
                return False

            logger.info(f"Usługa {service_name} została zrestartowana pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas restartowania usługi {service_name}: {str(e)}")
            return False

    def _restart_service_macos(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu macOS
        return False

    def _restart_service_windows(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu Windows
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

    def _service_status_linux(self, service_name: str) -> Dict[str, Any]:
        """
        Sprawdza status usługi systemowej w systemie Linux.

        Args:
            service_name: Nazwa usługi.

        Returns:
            Słownik ze statusem usługi.
        """
        try:
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                # Próbujemy użyć sudo
                if self._is_command_available("sudo"):
                    cmd = ["sudo", "systemctl", "status", service_name]
                else:
                    return {"status": "unknown", "error": "Brak uprawnień administratora i brak polecenia sudo."}
            else:
                cmd = ["systemctl", "status", service_name]

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Analizujemy wynik
            if process.returncode == 0:
                return {"status": "running", "output": process.stdout}
            elif process.returncode == 3:
                return {"status": "stopped", "output": process.stdout}
            else:
                return {"status": "unknown", "error": process.stderr}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _service_status_macos(self, service_name: str) -> Dict[str, Any]:
        # TODO: Implementacja dla systemu macOS
        return {"status": "unknown", "error": "Nieobsługiwany system operacyjny: macOS"}

    def _service_status_windows(self, service_name: str) -> Dict[str, Any]:
        # TODO: Implementacja dla systemu Windows
        return {"status": "unknown", "error": "Nieobsługiwany system operacyjny: Windows"}

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

    def _create_service_linux(self, service_name: str, command: str, description: str = "", auto_start: bool = True) -> bool:
        """
        Tworzy nową usługę systemową w systemie Linux.

        Args:
            service_name: Nazwa usługi.
            command: Polecenie uruchamiające usługę.
            description: Opis usługi (opcjonalne).
            auto_start: Czy usługa ma być uruchamiana automatycznie po starcie systemu (opcjonalne).

        Returns:
            True, jeśli usługa została utworzona pomyślnie, False w przeciwnym razie.
        """
        try:
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                logger.error("Tworzenie usługi wymaga uprawnień administratora.")
                return False

            # Tworzymy plik usługi systemd
            service_file = f"/etc/systemd/system/{service_name}.service"
            
            # Przygotowujemy zawartość pliku
            service_content = f"""[Unit]
Description={description if description else service_name}
After=network.target

[Service]
ExecStart={command}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""

            # Zapisujemy plik
            with open(service_file, "w") as f:
                f.write(service_content)

            # Przeładowujemy konfigurację systemd
            subprocess.run(
                ["systemctl", "daemon-reload"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Jeśli wybrano auto_start, włączamy usługę
            if auto_start:
                subprocess.run(
                    ["systemctl", "enable", service_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

            logger.info(f"Usługa {service_name} została utworzona pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas tworzenia usługi {service_name}: {str(e)}")
            return False

    def _create_service_macos(self, service_name: str, command: str, description: str = "", auto_start: bool = True) -> bool:
        # TODO: Implementacja dla systemu macOS
        return False

    def _create_service_windows(self, service_name: str, command: str, description: str = "", auto_start: bool = True) -> bool:
        # TODO: Implementacja dla systemu Windows
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

    def _delete_service_linux(self, service_name: str) -> bool:
        """
        Usuwa usługę systemową w systemie Linux.

        Args:
            service_name: Nazwa usługi.

        Returns:
            True, jeśli usługa została usunięta pomyślnie, False w przeciwnym razie.
        """
        try:
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                logger.error("Usuwanie usługi wymaga uprawnień administratora.")
                return False

            # Zatrzymujemy usługę
            subprocess.run(
                ["systemctl", "stop", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Wyłączamy usługę
            subprocess.run(
                ["systemctl", "disable", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Usuwamy plik usługi
            service_file = f"/etc/systemd/system/{service_name}.service"
            if os.path.exists(service_file):
                os.remove(service_file)

            # Przeładowujemy konfigurację systemd
            subprocess.run(
                ["systemctl", "daemon-reload"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            logger.info(f"Usługa {service_name} została usunięta pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas usuwania usługi {service_name}: {str(e)}")
            return False

    def _delete_service_macos(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu macOS
        return False

    def _delete_service_windows(self, service_name: str) -> bool:
        # TODO: Implementacja dla systemu Windows
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

    def _list_services_linux(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę usług systemowych w systemie Linux.

        Returns:
            Lista słowników opisujących usługi.
        """
        try:
            # Wykonujemy polecenie
            process = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas pobierania listy usług: {process.stderr}")
                return []

            # Analizujemy wynik
            services = []
            for line in process.stdout.splitlines()[1:]:  # Pomijamy nagłówek
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 5:
                    service_name = parts[0]
                    if service_name.endswith(".service"):
                        service_name = service_name[:-8]  # Usuwamy ".service"
                    
                    status = "running" if "running" in parts[3] else "stopped"
                    description = " ".join(parts[4:])
                    
                    services.append({
                        "name": service_name,
                        "status": status,
                        "description": description
                    })

            return services

        except Exception as e:
            logger.error(f"Błąd podczas pobierania listy usług: {str(e)}")
            return []

    def _list_services_macos(self) -> List[Dict[str, Any]]:
        # TODO: Implementacja dla systemu macOS
        return []

    def _list_services_windows(self) -> List[Dict[str, Any]]:
        # TODO: Implementacja dla systemu Windows
        return []