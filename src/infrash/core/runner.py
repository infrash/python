"""
runner.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Główny moduł runnera infrash. Zarządza uruchamianiem, zatrzymywaniem
i monitorowaniem aplikacji oraz diagnostyką i rozwiązywaniem problemów.
"""

import os
import sys
import time
import shutil
import yaml
import json
import signal
import subprocess
import tempfile
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger
from infrash.repo.git import GitRepo
from infrash.system.os_detect import detect_os
from infrash.system.dependency import check_dependencies, install_dependency
from infrash.system.service import ServiceManager

# Inicjalizacja loggera
logger = get_logger(__name__)

class Runner:
    """
    Główna klasa runnera, odpowiedzialna za uruchamianie, zatrzymywanie
    i monitorowanie aplikacji oraz rozwiązywanie problemów.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Inicjalizuje nową instancję Runner.

        Args:
            config_path: Opcjonalna ścieżka do pliku konfiguracyjnego.
        """
        self.config = self._load_config(config_path)
        self.os_info = detect_os()
        self.service_manager = ServiceManager()
        self.processes = {}  # Słownik przechowujący uruchomione procesy
        self.git = GitRepo()

        # Ścieżka do katalogu przechowującego pliki PID
        self.pid_dir = Path(tempfile.gettempdir()) / "infrash" / "pids"
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Ładuje konfigurację z pliku.

        Args:
            config_path: Ścieżka do pliku konfiguracyjnego.

        Returns:
            Słownik z konfiguracją.
        """
        default_config = {
            "auto_repair": True,
            "diagnostic_level": "basic",
            "monitor_interval": 60,  # Interwał monitorowania w sekundach
            "solution_db": {
                "auto_update": True,
                "update_interval": 86400  # 24 godziny
            },
            "repositories": {},
            "environments": {
                "development": {
                    "start_command": "python app.py",
                    "stop_command": None
                },
                "production": {
                    "start_command": "gunicorn -w 4 app:app",
                    "stop_command": None
                }
            }
        }

        # Jeśli podano ścieżkę do konfiguracji, ładujemy ją
        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, 'r') as f:
                    custom_config = yaml.safe_load(f)

                # Łączymy konfigurację domyślną z niestandardową
                return self._merge_configs(default_config, custom_config)
            except Exception as e:
                logger.error(f"Błąd podczas ładowania konfiguracji: {str(e)}")
                logger.warning("Używam konfiguracji domyślnej.")

        # Sprawdzamy, czy istnieje plik konfiguracyjny w bieżącym katalogu
        default_config_paths = [
            os.path.join(os.getcwd(), 'infrash.yaml'),
            os.path.join(os.getcwd(), 'infrash.yml'),
            os.path.join(os.getcwd(), '.infrash', 'config.yaml'),
            os.path.expanduser('~/.config/infrash/config.yaml')
        ]

        for path in default_config_paths:
            if os.path.isfile(path):
                try:
                    with open(path, 'r') as f:
                        custom_config = yaml.safe_load(f)
                    return self._merge_configs(default_config, custom_config)
                except Exception as e:
                    logger.error(f"Błąd podczas ładowania konfiguracji z {path}: {str(e)}")

        return default_config

    def _merge_configs(self, default_config: Dict[str, Any], custom_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Łączy konfigurację domyślną z niestandardową.

        Args:
            default_config: Domyślna konfiguracja.
            custom_config: Niestandardowa konfiguracja.

        Returns:
            Połączona konfiguracja.
        """
        result = default_config.copy()

        for key, value in custom_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def run(self, command: str, **kwargs) -> bool:
        """
        Uruchamia polecenie runner.

        Args:
            command: Polecenie do uruchomienia.
            **kwargs: Dodatkowe argumenty.

        Returns:
            True, jeśli polecenie zostało wykonane pomyślnie, False w przeciwnym razie.
        """
        # Mapowanie poleceń na metody
        command_map = {
            "start": self.start,
            "stop": self.stop,
            "restart": self.restart,
            "status": self.status
        }

        # Sprawdzamy, czy podane polecenie jest obsługiwane
        if command not in command_map:
            logger.error(f"Nieobsługiwane polecenie: {command}")
            return False

    def is_running_pid(self, pid: int) -> bool:
        """
        Sprawdza, czy proces o podanym PID jest uruchomiony.

        Args:
            pid: PID procesu.

        Returns:
            True, jeśli proces jest uruchomiony, False w przeciwnym razie.
        """
        try:
            # W systemach Unix, sprawdzenie czy proces istnieje
            # można wykonać wysyłając sygnał 0, który nie robi nic,
            # ale sprawdza czy proces istnieje
            os.kill(pid, 0)
            return True
        except OSError:
            return False
        except Exception:
            return False

    def _get_process_info(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera informacje o procesie dla podanej ścieżki.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Słownik z informacjami o procesie lub None, jeśli nie znaleziono.
        """
        # Normalizujemy ścieżkę
        path = os.path.abspath(path)

        # Sprawdzamy, czy mamy proces w słowniku
        if path in self.processes:
            return self.processes[path]

        # Sprawdzamy pliki PID
        for pid_file in self.pid_dir.glob(f"{os.path.basename(path)}_*.pid"):
            try:
                # Pobieramy środowisko z nazwy pliku PID
                env = pid_file.stem.split('_')[-1]

                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Sprawdzamy, czy proces nadal działa
                if self.is_running_pid(pid):
                    # Tworzymy wpis w słowniku
                    self.processes[path] = {
                        'process': None,  # Nie mamy obiektu procesu
                        'env': env,
                        'pid': pid,
                        'start_time': os.path.getctime(pid_file)  # Używamy czasu utworzenia pliku PID
                    }
                    return self.processes[path]
            except Exception as e:
                logger.error(f"Błąd podczas pobierania informacji o procesie z pliku PID {pid_file}: {str(e)}")

        return None

    def _format_uptime(self, seconds: float) -> str:
        """
        Formatuje czas działania.

        Args:
            seconds: Czas w sekundach.

        Returns:
            Sformatowany czas działania.
        """
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)


def init_project(path: str = ".", template: str = "default", **kwargs) -> bool:
    """
    Inicjalizuje nowy projekt infrash.

    Args:
        path: Ścieżka do katalogu projektu.
        template: Nazwa szablonu projektu.
        **kwargs: Dodatkowe parametry konfiguracyjne.

    Returns:
        True, jeśli inicjalizacja zakończyła się pomyślnie, False w przeciwnym razie.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)
    logger.info(f"Inicjalizacja projektu w katalogu: {path}")

    # Tworzymy katalog projektu, jeśli nie istnieje
    os.makedirs(path, exist_ok=True)

    # Tworzymy katalog .infrash
    infrash_dir = os.path.join(path, ".infrash")
    os.makedirs(infrash_dir, exist_ok=True)

    # Przygotowujemy domyślną konfigurację
    config = {
        "name": os.path.basename(path),
        "auto_repair": True,
        "diagnostic_level": "basic",
        "environments": {
            "development": {
                "start_command": "python app.py",
                "stop_command": None
            },
            "production": {
                "start_command": "gunicorn -w 4 app:app",
                "stop_command": None
            }
        }
    }

    # Aktualizujemy konfigurację o dodatkowe parametry
    for key, value in kwargs.items():
        if key in config:
            if isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value

    # Zapisujemy konfigurację
    config_path = os.path.join(infrash_dir, "config.yaml")
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania konfiguracji: {str(e)}")
        return False

    # Kopiujemy szablony na podstawie wybranego szablonu
    try:
        # Ścieżka do szablonów
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "data", "templates")

        # Sprawdzamy, czy wybrany szablon istnieje
        template_path = os.path.join(templates_dir, template)
        if not os.path.isdir(template_path):
            # Używamy domyślnego szablonu
            template_path = os.path.join(templates_dir, "default")
            logger.warning(f"Szablon {template} nie istnieje. Używam szablonu domyślnego.")

        # Kopiujemy pliki szablonu do katalogu projektu
        for item in os.listdir(template_path):
            source = os.path.join(template_path, item)
            destination = os.path.join(path, item)

            if os.path.isfile(source):
                shutil.copy2(source, destination)
            elif os.path.isdir(source):
                shutil.copytree(source, destination, dirs_exist_ok=True)
    except Exception as e:
        logger.error(f"Błąd podczas kopiowania szablonów: {str(e)}")
        return False

    logger.info(f"Projekt został pomyślnie zainicjalizowany w katalogu: {path}")
    return True

    # Wywołujemy odpowiednią metodę
    try:
        return command_map[command](**kwargs)
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania polecenia {command}: {str(e)}")
        return False

def start(self,
          path: str = ".",
          env: str = "development",
          diagnostic_level: str = "basic") -> bool:
    """
    Uruchamia aplikację.

    Args:
        path: Ścieżka do projektu.
        env: Środowisko uruchomieniowe (development, production, itp.).
        diagnostic_level: Poziom diagnostyki (none, basic, full).

    Returns:
        True, jeśli aplikacja została uruchomiona pomyślnie, False w przeciwnym razie.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)
    logger.info(f"Uruchamianie aplikacji w katalogu: {path}")

    # Sprawdzamy, czy katalog istnieje
    if not os.path.isdir(path):
        logger.error(f"Katalog nie istnieje: {path}")
        return False

    # Sprawdzamy, czy aplikacja jest już uruchomiona
    if self.is_running(path):
        logger.warning(f"Aplikacja jest już uruchomiona w katalogu: {path}")
        return True

    # Przeprowadzamy diagnostykę przed uruchomieniem (jeśli wybrano)
    if diagnostic_level != "none":
        from infrash.core.diagnostics import Diagnostics
        diagnostics = Diagnostics()
        issues = diagnostics.run(path, level=diagnostic_level)

        # Jeśli znaleziono problemy, próbujemy je naprawić
        if issues and self.config.get('auto_repair', True):
            from infrash.core.repair import Repair
            repair_tool = Repair()

            logger.info(f"Znaleziono {len(issues)} problemów. Próba automatycznej naprawy...")

            for issue in issues:
                if not repair_tool.fix(issue):
                    logger.warning(f"Nie udało się naprawić problemu: {issue.get('title', 'Nieznany problem')}")

                    # Jeśli problem jest krytyczny, nie uruchamiamy aplikacji
                    if issue.get('severity', 'warning') == 'critical':
                        logger.error("Nie można uruchomić aplikacji z nierozwiązanymi problemami krytycznymi.")
                        return False

    # Sprawdzamy, czy mamy polecenie startowe dla wybranego środowiska
    if env not in self.config.get('environments', {}):
        logger.error(f"Nieznane środowisko: {env}")
        return False

    # Pobieramy polecenie startowe
    start_command = self.config['environments'][env].get('start_command')
    if not start_command:
        logger.error(f"Brak polecenia startowego dla środowiska: {env}")
        return False

    # Uruchamiamy aplikację jako proces w tle
    try:
        # Zmieniamy katalog roboczy
        original_dir = os.getcwd()
        os.chdir(path)

        # Przygotowujemy polecenie
        if isinstance(start_command, list):
            cmd = start_command
        else:
            cmd = start_command.split()

        # Uruchamiamy proces
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            preexec_fn=os.setpgrp  # Tworzy nową grupę procesów (tylko Unix)
        )

        # Zapisujemy PID procesu
        pid_file = self.pid_dir / f"{os.path.basename(path)}_{env}.pid"
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))

        # Dodajemy proces do słownika
        self.processes[path] = {
            'process': process,
            'env': env,
            'pid': process.pid,
            'start_time': time.time()
        }

        # Wracamy do oryginalnego katalogu
        os.chdir(original_dir)

        logger.info(f"Aplikacja uruchomiona pomyślnie. PID: {process.pid}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania aplikacji: {str(e)}")

        # Wracamy do oryginalnego katalogu w przypadku błędu
        if 'original_dir' in locals():
            os.chdir(original_dir)

        return False

def stop(self, path: str = ".", force: bool = False) -> bool:
    """
    Zatrzymuje uruchomioną aplikację.

    Args:
        path: Ścieżka do projektu.
        force: Czy wymusić zatrzymanie w przypadku problemów.

    Returns:
        True, jeśli aplikacja została zatrzymana pomyślnie, False w przeciwnym razie.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)
    logger.info(f"Zatrzymywanie aplikacji w katalogu: {path}")

    # Sprawdzamy, czy aplikacja jest uruchomiona
    if not self.is_running(path):
        logger.warning(f"Aplikacja nie jest uruchomiona w katalogu: {path}")
        return True  # Zwracamy True, bo stan końcowy jest zgodny z oczekiwanym

    # Pobieramy informacje o procesie
    process_info = self._get_process_info(path)
    if not process_info:
        logger.error(f"Nie znaleziono informacji o procesie dla katalogu: {path}")
        return False

    # Sprawdzamy, czy mamy polecenie zatrzymania dla wybranego środowiska
    env = process_info.get('env', 'development')
    stop_command = self.config['environments'][env].get('stop_command')

    # Jeśli mamy polecenie zatrzymania, używamy go
    if stop_command:
        try:
            # Zmieniamy katalog roboczy
            original_dir = os.getcwd()
            os.chdir(path)

            # Przygotowujemy polecenie
            if isinstance(stop_command, list):
                cmd = stop_command
            else:
                cmd = stop_command.split()

            # Uruchamiamy polecenie zatrzymania
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Wracamy do oryginalnego katalogu
            os.chdir(original_dir)

            # Sprawdzamy wynik polecenia
            if result.returncode != 0 and not force:
                logger.error(f"Błąd podczas zatrzymywania aplikacji: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Błąd podczas wykonywania polecenia zatrzymania: {str(e)}")

            # Wracamy do oryginalnego katalogu w przypadku błędu
            if 'original_dir' in locals():
                os.chdir(original_dir)

            # Jeśli wymuszono zatrzymanie, kontynuujemy mimo błędu
            if not force:
                return False

    # Zatrzymujemy proces bezpośrednio
    try:
        # Pobieramy PID procesu
        pid = process_info.get('pid')

        # Wysyłamy sygnał SIGTERM
        os.kill(pid, signal.SIGTERM)

        # Czekamy na zakończenie procesu (max 5 sekund)
        wait_count = 0
        while self.is_running_pid(pid) and wait_count < 5:
            time.sleep(1)
            wait_count += 1

        # Jeśli proces nadal działa, a wymuszono zatrzymanie, wysyłamy SIGKILL
        if self.is_running_pid(pid) and force:
            os.kill(pid, signal.SIGKILL)

        # Sprawdzamy, czy proces został zatrzymany
        if self.is_running_pid(pid):
            logger.error(f"Nie udało się zatrzymać procesu o PID: {pid}")
            return False

        # Usuwamy plik PID
        pid_file = self.pid_dir / f"{os.path.basename(path)}_{env}.pid"
        if os.path.isfile(pid_file):
            os.unlink(pid_file)

        # Usuwamy proces ze słownika
        if path in self.processes:
            del self.processes[path]

        logger.info(f"Aplikacja zatrzymana pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas zatrzymywania procesu: {str(e)}")
        return False

def restart(self,
            path: str = ".",
            env: Optional[str] = None,
            force: bool = False) -> bool:
    """
    Restartuje aplikację.

    Args:
        path: Ścieżka do projektu.
        env: Środowisko uruchomieniowe (development, production, itp.).
        force: Czy wymusić restart w przypadku problemów.

    Returns:
        True, jeśli aplikacja została zrestartowana pomyślnie, False w przeciwnym razie.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)
    logger.info(f"Restartowanie aplikacji w katalogu: {path}")

    # Pobieramy środowisko z uruchomionej aplikacji, jeśli nie podano
    if not env and self.is_running(path):
        process_info = self._get_process_info(path)
        if process_info:
            env = process_info.get('env', 'development')

    # Używamy domyślnego środowiska, jeśli nadal nie mamy
    if not env:
        env = "development"

    # Zatrzymujemy aplikację
    stop_result = self.stop(path, force=force)
    if not stop_result and not force:
        logger.error("Nie udało się zatrzymać aplikacji. Restart przerwany.")
        return False

    # Uruchamiamy aplikację ponownie
    return self.start(path, env=env)

def status(self, path: str = ".", detailed: bool = False) -> Dict[str, Any]:
    """
    Zwraca status aplikacji.

    Args:
        path: Ścieżka do projektu.
        detailed: Czy zwrócić szczegółowe informacje.

    Returns:
        Słownik ze statusem aplikacji.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)

    # Podstawowe informacje o statusie
    result = {
        "app": {
            "status": "stopped",
            "details": ""
        }
    }

    # Sprawdzamy, czy aplikacja jest uruchomiona
    if self.is_running(path):
        process_info = self._get_process_info(path)

        if process_info:
            # Obliczamy czas działania
            uptime = time.time() - process_info.get('start_time', time.time())
            uptime_str = self._format_uptime(uptime)

            result["app"] = {
                "status": "running",
                "details": f"PID: {process_info.get('pid')}, Środowisko: {process_info.get('env')}, Czas działania: {uptime_str}"
            }

    # Dodajemy szczegółowe informacje, jeśli wybrano
    if detailed:
        # Informacje o systemie
        result["system"] = {
            "status": "ok",
            "details": f"{self.os_info.get('name', 'Unknown')} {self.os_info.get('version', 'Unknown')}"
        }

        # Informacje o zależnościach
        missing_deps = check_dependencies(path)
        if missing_deps:
            result["dependencies"] = {
                "status": "missing",
                "details": f"Brakujące zależności: {', '.join(missing_deps)}"
            }
        else:
            result["dependencies"] = {
                "status": "ok",
                "details": "Wszystkie zależności zainstalowane"
            }

        # Informacje o repozytorium git (jeśli istnieje)
        if os.path.isdir(os.path.join(path, ".git")):
            try:
                repo_status = self.git.get_status(path)
                branch = self.git.get_current_branch(path)

                if repo_status.get('dirty', False):
                    result["repository"] = {
                        "status": "dirty",
                        "details": f"Gałąź: {branch}, Niezatwierdzone zmiany: {repo_status.get('changes', 0)}"
                    }
                else:
                    result["repository"] = {
                        "status": "clean",
                        "details": f"Gałąź: {branch}, Commit: {repo_status.get('commit', 'Unknown')[:7]}"
                    }
            except Exception as e:
                result["repository"] = {
                    "status": "error",
                    "details": f"Błąd podczas sprawdzania repozytorium: {str(e)}"
                }

    return result

def is_running(self, path: str) -> bool:
    """
    Sprawdza, czy aplikacja jest uruchomiona.

    Args:
        path: Ścieżka do projektu.

    Returns:
        True, jeśli aplikacja jest uruchomiona, False w przeciwnym razie.
    """
    # Normalizujemy ścieżkę
    path = os.path.abspath(path)

    # Sprawdzamy, czy mamy proces w słowniku
    if path in self.processes:
        process = self.processes[path].get('process')
        if process and process.poll() is None:
            return True
        else:
            # Usuwamy proces ze słownika, jeśli już się zakończył
            del self.processes[path]
            return False

    # Sprawdzamy pliki PID
    for pid_file in self.pid_dir.glob(f"{os.path.basename(path)}_*.pid"):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Sprawdzamy, czy proces nadal działa
            if self.is_running_pid(pid):
                return True
            else:
                # Usuwamy nieaktualny plik PID
                os.unlink(pid_file)
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania pliku PID {pid_file}: {str(e)}")
            # Usuwamy uszkodzony plik PID
            try:
                os.unlink(pid_file)
            except:
                pass

    return False