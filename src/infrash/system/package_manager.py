#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł obsługi menedżerów pakietów. Umożliwia instalację, aktualizację
i zarządzanie pakietami systemowymi.
"""

import os
import sys
import subprocess
import platform
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, is_admin

# Inicjalizacja loggera
logger = get_logger(__name__)

class PackageManager:
    """
    Klasa zarządzająca menedżerami pakietów.
    """

    def __init__(self, manager_name: Optional[str] = None):
        """
        Inicjalizuje nową instancję PackageManager.
        
        Args:
            manager_name: Nazwa menedżera pakietów (opcjonalnie).
        """
        self.os_info = detect_os()

        # Określamy menedżera pakietów
        if manager_name:
            self.manager_name = manager_name
        else:
            self.manager_name = self._detect_package_manager()

    def _detect_package_manager(self) -> str:
        """
        Wykrywa domyślny menedżer pakietów dla systemu.
        
        Returns:
            Nazwa menedżera pakietów.
        """
        system = platform.system()
        os_type = self.os_info.get("type", "").lower()

        if system == "Linux":
            # Różne dystrybucje Linux
            if "debian" in os_type or "ubuntu" in os_type:
                return "apt"
            elif "fedora" in os_type:
                return "dnf"
            elif "centos" in os_type or "rhel" in os_type:
                # CentOS/RHEL 8+ używa dnf, wcześniejsze wersje yum
                if self.os_info.get("version", "").startswith(("8", "9")):
                    return "dnf"
                else:
                    return "yum"
            elif "arch" in os_type:
                return "pacman"
            elif "suse" in os_type:
                return "zypper"
            elif "alpine" in os_type:
                return "apk"
            else:
                # Domyślnie apt dla nieznanych dystrybucji
                return "apt"
        elif system == "Darwin":
            # macOS - Homebrew
            return "brew"
        elif system == "Windows":
            # Windows - Chocolatey, jeśli jest zainstalowany
            try:
                choco_process = subprocess.run(
                    ["choco", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if choco_process.returncode == 0:
                    return "choco"

                # Sprawdzamy winget
                winget_process = subprocess.run(
                    ["winget", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if winget_process.returncode == 0:
                    return "winget"
            except Exception:
                pass

            return "choco"  # Domyślnie Chocolatey
        else:
            # Inne systemy
            return "pip"  # Domyślnie pip

    def get_package_manager_command(self) -> str:
        """
        Zwraca polecenie menedżera pakietów.
        
        Returns:
            Polecenie menedżera pakietów.
        """
        manager_commands = {
            "apt": "apt-get",
            "apt-get": "apt-get",
            "dnf": "dnf",
            "yum": "yum",
            "pacman": "pacman",
            "zypper": "zypper",
            "apk": "apk",
            "brew": "brew",
            "choco": "choco",
            "winget": "winget",
            "pip": "pip"
        }

        return manager_commands.get(self.manager_name, self.manager_name)

    def needs_sudo(self) -> bool:
        """
        Sprawdza, czy menedżer pakietów wymaga uprawnień roota.
        
        Returns:
            True, jeśli menedżer pakietów wymaga uprawnień roota, False w przeciwnym razie.
        """
        # Menedżery pakietów, które wymagają uprawnień roota
        sudo_managers = ["apt", "apt-get", "dnf", "yum", "pacman", "zypper", "apk"]

        return self.manager_name in sudo_managers

    def get_install_command(self, package_name: str) -> List[str]:
        """
        Zwraca polecenie instalacji pakietu.
        
        Args:
            package_name: Nazwa pakietu.
            
        Returns:
            Lista z elementami polecenia instalacji.
        """
        manager = self.get_package_manager_command()

        # Przygotowujemy polecenie instalacji w zależności od menedżera pakietów
        if self.manager_name in ["apt", "apt-get"]:
            cmd = [manager, "install", "-y", package_name]
        elif self.manager_name in ["dnf", "yum"]:
            cmd = [manager, "install", "-y", package_name]
        elif self.manager_name == "pacman":
            cmd = [manager, "-S", "--noconfirm", package_name]
        elif self.manager_name == "zypper":
            cmd = [manager, "install", "-y", package_name]
        elif self.manager_name == "apk":
            cmd = [manager, "add", package_name]
        elif self.manager_name == "brew":
            cmd = [manager, "install", package_name]
        elif self.manager_name == "choco":
            cmd = [manager, "install", package_name, "-y"]
        elif self.manager_name == "winget":
            cmd = [manager, "install", "-e", "--id", package_name]
        elif self.manager_name == "pip":
            cmd = [sys.executable, "-m", "pip", "install", package_name]
        else:
            cmd = [manager, "install", package_name]

        # Dodajemy sudo, jeśli potrzebne
        if self.needs_sudo() and not is_admin():
            cmd = ["sudo"] + cmd

        return cmd

    def get_update_command(self) -> List[str]:
        """
        Zwraca polecenie aktualizacji bazy pakietów.
        
        Returns:
            Lista z elementami polecenia aktualizacji.
        """
        manager = self.get_package_manager_command()

        # Przygotowujemy polecenie aktualizacji w zależności od menedżera pakietów
        if self.manager_name in ["apt", "apt-get"]:
            cmd = [manager, "update"]
        elif self.manager_name in ["dnf", "yum"]:
            cmd = [manager, "check-update"]
        elif self.manager_name == "pacman":
            cmd = [manager, "-Sy"]
        elif self.manager_name == "zypper":
            cmd = [manager, "refresh"]
        elif self.manager_name == "apk":
            cmd = [manager, "update"]
        elif self.manager_name == "brew":
            cmd = [manager, "update"]
        elif self.manager_name == "choco":
            cmd = [manager, "source", "list"]
        elif self.manager_name == "winget":
            cmd = [manager, "source", "update"]
        elif self.manager_name == "pip":
            cmd = [sys.executable, "-m", "pip", "list", "--outdated"]
        else:
            cmd = [manager, "update"]

        # Dodajemy sudo, jeśli potrzebne
        if self.needs_sudo() and not is_admin():
            cmd = ["sudo"] + cmd

        return cmd

    def get_upgrade_command(self, package_name: Optional[str] = None) -> List[str]:
        """
        Zwraca polecenie aktualizacji pakietu lub wszystkich pakietów.
        
        Args:
            package_name: Nazwa pakietu (opcjonalnie).
            
        Returns:
            Lista z elementami polecenia aktualizacji.
        """
        manager = self.get_package_manager_command()

        # Przygotowujemy polecenie aktualizacji w zależności od menedżera pakietów
        if self.manager_name in ["apt", "apt-get"]:
            if package_name:
                cmd = [manager, "install", "--only-upgrade", "-y", package_name]
            else:
                cmd = [manager, "upgrade", "-y"]
        elif self.manager_name in ["dnf", "yum"]:
            if package_name:
                cmd = [manager, "update", "-y", package_name]
            else:
                cmd = [manager, "update", "-y"]
        elif self.manager_name == "pacman":
            if package_name:
                cmd = [manager, "-S", "--noconfirm", package_name]
            else:
                cmd = [manager, "-Syu", "--noconfirm"]
        elif self.manager_name == "zypper":
            if package_name:
                cmd = [manager, "update", "-y", package_name]
            else:
                cmd = [manager, "update", "-y"]
        elif self.manager_name == "apk":
            if package_name:
                cmd = [manager, "upgrade", package_name]
            else:
                cmd = [manager, "upgrade"]
        elif self.manager_name == "brew":
            if package_name:
                cmd = [manager, "upgrade", package_name]
            else:
                cmd = [manager, "upgrade"]
        elif self.manager_name == "choco":
            if package_name:
                cmd = [manager, "upgrade", package_name, "-y"]
            else:
                cmd = [manager, "upgrade", "all", "-y"]
        elif self.manager_name == "winget":
            if package_name:
                cmd = [manager, "upgrade", "-e", "--id", package_name]
            else:
                cmd = [manager, "upgrade", "--all"]
        elif self.manager_name == "pip":
            if package_name:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package_name]
            else:
                cmd = [sys.executable, "-m", "pip", "list", "--outdated", "--format=freeze", "|", "grep", "-v", "'^-e'", "|", "cut", "-d", "=", "-f", "1", "|", "xargs", "-n1", sys.executable, "-m", "pip", "install", "-U"]
                if platform.system() == "Windows":
                    cmd = [sys.executable, "-m", "pip", "list", "--outdated", "--format=freeze"]
        else:
            if package_name:
                cmd = [manager, "upgrade", package_name]
            else:
                cmd = [manager, "upgrade"]

        # Dodajemy sudo, jeśli potrzebne
        if self.needs_sudo() and not is_admin():
            cmd = ["sudo"] + cmd

        return cmd

    def get_uninstall_command(self, package_name: str) -> List[str]:
        """
        Zwraca polecenie odinstalowania pakietu.
        
        Args:
            package_name: Nazwa pakietu.
            
        Returns:
            Lista z elementami polecenia odinstalowania.
        """
        manager = self.get_package_manager_command()

        # Przygotowujemy polecenie odinstalowania w zależności od menedżera pakietów
        if self.manager_name in ["apt", "apt-get"]:
            cmd = [manager, "remove", "-y", package_name]
        elif self.manager_name in ["dnf", "yum"]:
            cmd = [manager, "remove", "-y", package_name]
        elif self.manager_name == "pacman":
            cmd = [manager, "-R", "--noconfirm", package_name]
        elif self.manager_name == "zypper":
            cmd = [manager, "remove", "-y", package_name]
        elif self.manager_name == "apk":
            cmd = [manager, "del", package_name]
        elif self.manager_name == "brew":
            cmd = [manager, "uninstall", package_name]
        elif self.manager_name == "choco":
            cmd = [manager, "uninstall", package_name, "-y"]
        elif self.manager_name == "winget":
            cmd = [manager, "uninstall", "-e", "--id", package_name]
        elif self.manager_name == "pip":
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
        else:
            cmd = [manager, "uninstall", package_name]

        # Dodajemy sudo, jeśli potrzebne
        if self.needs_sudo() and not is_admin():
            cmd = ["sudo"] + cmd

        return cmd

    def install_package(self, package_name: str) -> bool:
        """
        Instaluje pakiet.
        
        Args:
            package_name: Nazwa pakietu.
            
        Returns:
            True, jeśli pakiet został zainstalowany pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Instalacja pakietu {package_name} za pomocą {self.manager_name}")

        try:
            # Aktualizujemy bazę pakietów
            update_cmd = self.get_update_command()

            try:
                subprocess.run(
                    update_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            except Exception as e:
                logger.warning(f"Błąd podczas aktualizacji bazy pakietów: {str(e)}")

            # Pobieramy polecenie instalacji
            cmd = self.get_install_command(package_name)

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji pakietu {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas instalacji pakietu {package_name}: {str(e)}")
            return False

    def update_packages(self) -> bool:
        """
        Aktualizuje bazę pakietów.
        
        Returns:
            True, jeśli baza pakietów została zaktualizowana pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Aktualizacja bazy pakietów za pomocą {self.manager_name}")

        try:
            # Pobieramy polecenie aktualizacji
            cmd = self.get_update_command()

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0 and process.returncode != 100:  # 100 to kod wyjścia dla dnf/yum check-update, gdy są dostępne aktualizacje
                logger.error(f"Błąd podczas aktualizacji bazy pakietów: {process.stderr}")
                return False

            logger.info("Baza pakietów została zaktualizowana pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji bazy pakietów: {str(e)}")
            return False


    def upgrade_packages(self, package_name: Optional[str] = None) -> bool:
        """
        Aktualizuje pakiet lub wszystkie pakiety.

        Args:
            package_name: Nazwa pakietu (opcjonalnie).

        Returns:
            True, jeśli pakiety zostały zaktualizowane pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Aktualizacja {'pakietu ' + package_name if package_name else 'wszystkich pakietów'} za pomocą {self.manager_name}")

        try:
            # Aktualizujemy bazę pakietów
            self.update_packages()

            # Pobieramy polecenie aktualizacji
            cmd = self.get_upgrade_command(package_name)

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas aktualizacji {'pakietu ' + package_name if package_name else 'pakietów'}: {process.stderr}")
                return False

            logger.info(f"{'Pakiet ' + package_name if package_name else 'Pakiety'} został{'y' if not package_name or package_name.endswith('y') else ''} zaktualizowane pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji {'pakietu ' + package_name if package_name else 'pakietów'}: {str(e)}")
            return False

    def uninstall_package(self, package_name: str) -> bool:
        """
        Odinstalowuje pakiet.

        Args:
            package_name: Nazwa pakietu.

        Returns:
            True, jeśli pakiet został odinstalowany pomyślnie, False w przeciwnym razie.
        """
        logger.info(f"Odinstalowywanie pakietu {package_name} za pomocą {self.manager_name}")

        try:
            # Pobieramy polecenie odinstalowania
            cmd = self.get_uninstall_command(package_name)

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania pakietu {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas odinstalowywania pakietu {package_name}: {str(e)}")
            return False

    def check_package_installed(self, package_name: str) -> bool:
        """
        Sprawdza, czy pakiet jest zainstalowany.

        Args:
            package_name: Nazwa pakietu.

        Returns:
            True, jeśli pakiet jest zainstalowany, False w przeciwnym razie.
        """
        logger.debug(f"Sprawdzanie, czy pakiet {package_name} jest zainstalowany")

        try:
            # Przygotowujemy polecenie sprawdzania w zależności od menedżera pakietów
            manager = self.get_package_manager_command()

            if self.manager_name in ["apt", "apt-get"]:
                cmd = ["dpkg", "-l", package_name]
            elif self.manager_name in ["dnf", "yum"]:
                cmd = ["rpm", "-q", package_name]
            elif self.manager_name == "pacman":
                cmd = [manager, "-Q", package_name]
            elif self.manager_name == "zypper":
                cmd = [manager, "search", "-i", package_name]
            elif self.manager_name == "apk":
                cmd = [manager, "info", "-e", package_name]
            elif self.manager_name == "brew":
                cmd = [manager, "list", "--formula", package_name]
            elif self.manager_name == "choco":
                cmd = [manager, "list", "--local-only", package_name]
            elif self.manager_name == "winget":
                cmd = [manager, "list", "-e", "--id", package_name]
            elif self.manager_name == "pip":
                # Używamy importu modułu do sprawdzenia, czy pakiet jest zainstalowany
                try:
                    # Próbujemy zaimportować pakiet
                    __import__(package_name.replace("-", "_"))
                    return True
                except ImportError:
                    # Sprawdzamy przez pip list
                    cmd = [sys.executable, "-m", "pip", "show", package_name]
            else:
                cmd = [manager, "list", package_name]

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            return process.returncode == 0

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania, czy pakiet {package_name} jest zainstalowany: {str(e)}")
            return False

    def get_package_version(self, package_name: str) -> Optional[str]:
        """
        Pobiera wersję zainstalowanego pakietu.

        Args:
            package_name: Nazwa pakietu.

        Returns:
            Wersja pakietu lub None, jeśli pakiet nie jest zainstalowany.
        """
        logger.debug(f"Pobieranie wersji pakietu {package_name}")

        try:
            # Przygotowujemy polecenie pobierania wersji w zależności od menedżera pakietów
            manager = self.get_package_manager_command()

            if self.manager_name in ["apt", "apt-get"]:
                cmd = ["dpkg", "-l", package_name]
            elif self.manager_name in ["dnf", "yum"]:
                cmd = ["rpm", "-q", "--qf", "%{VERSION}", package_name]
            elif self.manager_name == "pacman":
                cmd = [manager, "-Q", package_name]
            elif self.manager_name == "zypper":
                cmd = [manager, "info", package_name]
            elif self.manager_name == "apk":
                cmd = [manager, "info", package_name]
            elif self.manager_name == "brew":
                cmd = [manager, "list", "--versions", package_name]
            elif self.manager_name == "choco":
                cmd = [manager, "list", "--local-only", package_name]
            elif self.manager_name == "winget":
                cmd = [manager, "list", "-e", "--id", package_name]
            elif self.manager_name == "pip":
                cmd = [sys.executable, "-m", "pip", "show", package_name]
            else:
                cmd = [manager, "list", package_name]

            # Wykonujemy polecenie
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Błąd podczas pobierania wersji pakietu {package_name}: {process.stderr}")
                return None

            # Przetwarzamy wynik w zależności od menedżera pakietów
            output = process.stdout.strip()

            if self.manager_name in ["apt", "apt-get"]:
                # dpkg -l output: ii package_name version description
                for line in output.split('\n'):
                    if line.startswith('ii ') and package_name in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]
            elif self.manager_name in ["dnf", "yum"]:
                # rpm -q --qf "%{VERSION}" output: version
                return output
            elif self.manager_name == "pacman":
                # pacman -Q output: package_name version
                for line in output.split('\n'):
                    if package_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
            elif self.manager_name == "zypper":
                # zypper info output: Version: version
                for line in output.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            elif self.manager_name == "apk":
                # apk info output: package_name-version ...
                for line in output.split('\n'):
                    if package_name in line:
                        for part in line.split():
                            if part.startswith(package_name + '-'):
                                return part[len(package_name + '-'):]
            elif self.manager_name == "brew":
                # brew list --versions output: package_name version
                for line in output.split('\n'):
                    if package_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
            elif self.manager_name == "choco":
                # choco list --local-only output: package_name version
                for line in output.split('\n'):
                    if package_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
            elif self.manager_name == "winget":
                # winget list -e --id output: ... package_name ... version
                for line in output.split('\n'):
                    if package_name in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == package_name and i < len(parts) - 1:
                                return parts[i + 1]
            elif self.manager_name == "pip":
                # pip show output: Version: version
                for line in output.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()

            # Jeśli nie udało się znaleźć wersji
            logger.warning(f"Nie udało się znaleźć wersji pakietu {package_name}")
            return None

        except Exception as e:
            logger.error(f"Błąd podczas pobierania wersji pakietu {package_name}: {str(e)}")
            return None