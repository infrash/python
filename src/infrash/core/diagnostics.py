#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny do wykrywania i rozwiązywania problemów z infrash.
"""

import os
import sys
import socket
import platform
import importlib
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from infrash.utils.logger import get_logger

logger = get_logger(__name__)


class DiagnosticsEngine:
    """
    Silnik diagnostyczny do wykrywania i rozwiązywania problemów z infrash.
    Zapewnia inteligentne diagnostyki i sugestie rozwiązań.
    """
    
    def __init__(self):
        """Inicjalizacja silnika diagnostycznego."""
        self.system_info = self._get_system_info()
        self.required_packages = [
            "click", "rich", "paramiko", "requests", "pyyaml"
        ]
        self.required_tools = [
            "git", "ssh", "python3", "pip"
        ]
    
    def _get_system_info(self) -> Dict[str, str]:
        """
        Pobiera informacje o systemie.
        
        Returns:
            Dict[str, str]: Informacje o systemie
        """
        try:
            return {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "python_path": sys.executable
            }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o systemie: {str(e)}")
            # Zwróć podstawowe informacje w przypadku błędu
            return {
                "system": platform.system(),
                "python_version": platform.python_version(),
                "python_path": sys.executable
            }
    
    def check_package_installed(self, package_name: str) -> Dict[str, Any]:
        """
        Sprawdza, czy pakiet jest zainstalowany.
        
        Args:
            package_name: Nazwa pakietu do sprawdzenia
            
        Returns:
            Dict[str, Any]: Status pakietu
        """
        try:
            # Próba importu pakietu
            importlib.import_module(package_name)
            return {
                "success": True,
                "message": f"Pakiet {package_name} jest zainstalowany."
            }
        except ImportError:
            # Pakiet nie jest zainstalowany
            return {
                "success": False,
                "message": f"Pakiet {package_name} nie jest zainstalowany.",
                "suggestion": f"Zainstaluj pakiet używając: pip install {package_name}"
            }
        except Exception as e:
            # Inny błąd podczas importu
            return {
                "success": False,
                "message": f"Błąd podczas sprawdzania pakietu {package_name}: {str(e)}",
                "suggestion": "Sprawdź logi, aby uzyskać więcej informacji."
            }
    
    def check_required_packages(self) -> Dict[str, Any]:
        """
        Sprawdza, czy wszystkie wymagane pakiety są zainstalowane.
        
        Returns:
            Dict[str, Any]: Status pakietów
        """
        missing_packages = []
        
        for package in self.required_packages:
            try:
                result = self.check_package_installed(package)
                if not result["success"]:
                    missing_packages.append(package)
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania pakietu {package}: {str(e)}")
                # Kontynuuj sprawdzanie innych pakietów
        
        if missing_packages:
            return {
                "success": False,
                "missing": missing_packages,
                "message": f"Brakujące pakiety: {', '.join(missing_packages)}",
                "suggestion": f"Zainstaluj brakujące pakiety używając: pip install {' '.join(missing_packages)}"
            }
        else:
            return {
                "success": True,
                "message": "Wszystkie wymagane pakiety są zainstalowane."
            }
    
    def check_tool_available(self, tool_name: str) -> Dict[str, Any]:
        """
        Sprawdza, czy narzędzie jest dostępne w systemie.
        
        Args:
            tool_name: Nazwa narzędzia do sprawdzenia
            
        Returns:
            Dict[str, Any]: Status narzędzia
        """
        try:
            # Sprawdź, czy narzędzie jest dostępne w PATH
            if shutil.which(tool_name) is not None:
                return {
                    "success": True,
                    "message": f"Narzędzie {tool_name} jest dostępne."
                }
            else:
                # Narzędzie nie jest dostępne
                return {
                    "success": False,
                    "message": f"Narzędzie {tool_name} nie jest dostępne.",
                    "suggestion": f"Zainstaluj {tool_name} używając menedżera pakietów twojego systemu."
                }
        except Exception as e:
            # Inny błąd podczas sprawdzania
            return {
                "success": False,
                "message": f"Błąd podczas sprawdzania narzędzia {tool_name}: {str(e)}",
                "suggestion": "Sprawdź logi, aby uzyskać więcej informacji."
            }
    
    def check_required_tools(self, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sprawdza, czy wszystkie wymagane narzędzia są dostępne.
        
        Args:
            tools: Lista narzędzi do sprawdzenia (opcjonalne, domyślnie używa self.required_tools)
            
        Returns:
            Dict[str, Any]: Status narzędzi
        """
        if tools is None:
            tools = self.required_tools
        
        missing_tools = []
        
        for tool in tools:
            try:
                result = self.check_tool_available(tool)
                if not result["success"]:
                    missing_tools.append(tool)
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania narzędzia {tool}: {str(e)}")
                # Kontynuuj sprawdzanie innych narzędzi
        
        if missing_tools:
            suggestion = ""
            if "apt-get" in self._get_package_manager():
                suggestion = f"Zainstaluj brakujące narzędzia używając: sudo apt-get install {' '.join(missing_tools)}"
            elif "yum" in self._get_package_manager():
                suggestion = f"Zainstaluj brakujące narzędzia używając: sudo yum install {' '.join(missing_tools)}"
            elif "dnf" in self._get_package_manager():
                suggestion = f"Zainstaluj brakujące narzędzia używając: sudo dnf install {' '.join(missing_tools)}"
            elif "brew" in self._get_package_manager():
                suggestion = f"Zainstaluj brakujące narzędzia używając: brew install {' '.join(missing_tools)}"
            else:
                suggestion = "Zainstaluj brakujące narzędzia używając menedżera pakietów twojego systemu."
            
            return {
                "success": False,
                "missing": missing_tools,
                "message": f"Brakujące narzędzia: {', '.join(missing_tools)}",
                "suggestion": suggestion
            }
        else:
            return {
                "success": True,
                "message": "Wszystkie wymagane narzędzia są dostępne."
            }
    
    def _get_package_manager(self) -> str:
        """
        Wykrywa menedżer pakietów systemu.
        
        Returns:
            str: Nazwa menedżera pakietów
        """
        try:
            if self.system_info["system"] == "Linux":
                # Sprawdź popularne menedżery pakietów
                for pm in ["apt-get", "yum", "dnf", "pacman", "zypper"]:
                    if shutil.which(pm) is not None:
                        return pm
            elif self.system_info["system"] == "Darwin":  # macOS
                if shutil.which("brew") is not None:
                    return "brew"
            elif self.system_info["system"] == "Windows":
                if shutil.which("choco") is not None:
                    return "choco"
                elif shutil.which("scoop") is not None:
                    return "scoop"
            
            return "unknown"
        except Exception as e:
            logger.error(f"Błąd podczas wykrywania menedżera pakietów: {str(e)}")
            return "unknown"
    
    def check_network_connectivity(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> Dict[str, Any]:
        """
        Sprawdza połączenie sieciowe.
        
        Args:
            host: Host do sprawdzenia (domyślnie Google DNS)
            port: Port do sprawdzenia (domyślnie 53 dla DNS)
            timeout: Limit czasu w sekundach
            
        Returns:
            Dict[str, Any]: Status połączenia
        """
        try:
            # Utwórz socket
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_obj.settimeout(timeout)
            
            # Próba połączenia
            result = socket_obj.connect_ex((host, port))
            socket_obj.close()
            
            if result == 0:
                return {
                    "success": True,
                    "message": f"Połączenie z {host}:{port} działa poprawnie."
                }
            else:
                return {
                    "success": False,
                    "message": f"Nie można połączyć się z {host}:{port}.",
                    "suggestion": "Sprawdź swoje połączenie internetowe i ustawienia zapory sieciowej."
                }
        except socket.gaierror:
            return {
                "success": False,
                "message": f"Nie można rozwiązać nazwy hosta {host}.",
                "suggestion": "Sprawdź swoje ustawienia DNS lub użyj adresu IP zamiast nazwy hosta."
            }
        except socket.timeout:
            return {
                "success": False,
                "message": f"Upłynął limit czasu podczas łączenia z {host}:{port}.",
                "suggestion": "Sprawdź swoje połączenie internetowe lub zwiększ limit czasu."
            }
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania połączenia sieciowego: {str(e)}")
            return {
                "success": False,
                "message": f"Błąd podczas sprawdzania połączenia sieciowego: {str(e)}",
                "suggestion": "Sprawdź swoje połączenie internetowe i ustawienia sieciowe."
            }
    
    def check_git_repo(self, repo_path: str) -> Dict[str, Any]:
        """
        Sprawdza, czy katalog jest poprawnym repozytorium Git.
        
        Args:
            repo_path: Ścieżka do repozytorium
            
        Returns:
            Dict[str, Any]: Status repozytorium
        """
        try:
            # Sprawdź, czy katalog istnieje
            if not os.path.isdir(repo_path):
                return {
                    "success": False,
                    "message": f"Katalog {repo_path} nie istnieje.",
                    "suggestion": "Utwórz katalog lub podaj poprawną ścieżkę."
                }
            
            # Sprawdź, czy to repozytorium Git
            git_dir = os.path.join(repo_path, ".git")
            if not os.path.isdir(git_dir):
                return {
                    "success": False,
                    "message": f"Katalog {repo_path} nie jest repozytorium Git.",
                    "suggestion": f"Zainicjuj repozytorium Git używając: git init {repo_path}"
                }
            
            # Sprawdź, czy można wykonać polecenia Git
            try:
                result = subprocess.run(
                    ["git", "-C", repo_path, "status"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    return {
                        "success": False,
                        "message": f"Błąd podczas wykonywania 'git status' w {repo_path}: {result.stderr}",
                        "suggestion": "Sprawdź uprawnienia dostępu do repozytorium."
                    }
                
                return {
                    "success": True,
                    "message": f"Repozytorium Git w {repo_path} jest poprawne."
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Błąd podczas wykonywania poleceń Git w {repo_path}: {str(e)}",
                    "suggestion": "Sprawdź, czy Git jest zainstalowany i dostępny w PATH."
                }
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania repozytorium Git: {str(e)}")
            return {
                "success": False,
                "message": f"Błąd podczas sprawdzania repozytorium Git: {str(e)}",
                "suggestion": "Sprawdź logi, aby uzyskać więcej informacji."
            }
    
    def run_full_diagnostics(self) -> Dict[str, Any]:
        """
        Uruchamia pełną diagnostykę systemu.
        
        Returns:
            Dict[str, Any]: Wyniki diagnostyki
        """
        results = {
            "system_info": self.system_info,
            "packages": self.check_required_packages(),
            "tools": self.check_required_tools(),
            "network": self.check_network_connectivity()
        }
        
        # Określ ogólny status
        all_success = all([
            results["packages"]["success"],
            results["tools"]["success"],
            results["network"]["success"]
        ])
        
        results["success"] = all_success
        
        if all_success:
            results["message"] = "Wszystkie diagnostyki zakończone pomyślnie."
        else:
            results["message"] = "Niektóre diagnostyki nie powiodły się. Sprawdź szczegółowe wyniki."
        
        return results
    
    def fix_common_issues(self) -> Dict[str, Any]:
        """
        Próbuje automatycznie naprawić typowe problemy.
        
        Returns:
            Dict[str, Any]: Wyniki naprawy
        """
        results = {
            "fixed": [],
            "failed": []
        }
        
        # Sprawdź i napraw brakujące pakiety
        packages_result = self.check_required_packages()
        if not packages_result["success"]:
            try:
                # Instalacja brakujących pakietów
                missing_packages = packages_result["missing"]
                logger.info(f"Próba instalacji brakujących pakietów: {', '.join(missing_packages)}")
                
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", *missing_packages
                ])
                
                # Sprawdź, czy instalacja się powiodła
                packages_result = self.check_required_packages()
                if packages_result["success"]:
                    results["fixed"].append("missing_packages")
                else:
                    results["failed"].append("missing_packages")
            except Exception as e:
                logger.error(f"Błąd podczas instalacji pakietów: {str(e)}")
                results["failed"].append("missing_packages")
        
        # Określ ogólny status
        results["success"] = len(results["failed"]) == 0
        
        if results["success"]:
            results["message"] = "Wszystkie problemy zostały naprawione."
        else:
            results["message"] = "Niektóre problemy nie zostały naprawione. Sprawdź szczegółowe wyniki."
        
        return results


# Klasa Diagnostics dla kompatybilności wstecznej
class Diagnostics(DiagnosticsEngine):
    """Klasa diagnostyczna dla kompatybilności wstecznej."""
    pass
