"""
diagnostics.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash. Służy do diagnozowania problemów
w projektach i środowiskach uruchomieniowych.
"""

import os
import sys
import platform
import subprocess
import json
import uuid
import psutil
import yaml
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import check_dependencies
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Diagnostics:
    """
    Klasa diagnostyczna do identyfikowania i raportowania problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Diagnostics.
        """
        self.os_info = detect_os()
        self.package_manager = get_package_manager()
        self.git = GitRepo()

        # Ładujemy bazę danych rozwiązań
        self.solutions_db = self._load_solutions_db()

    def _load_solutions_db(self) -> Dict[str, Any]:
        """
        Ładuje bazę danych rozwiązań.

        Returns:
            Słownik z bazą danych rozwiązań.
        """
        solutions_db = {}

        try:
            # Ścieżka do katalogu z rozwiązaniami
            solutions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "solutions")

            # Ładujemy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_file = os.path.join(solutions_dir, f"{os_type}.json")

            if os.path.isfile(os_specific_file):
                with open(os_specific_file, 'r') as f:
                    os_specific_solutions = json.load(f)
                solutions_db.update(os_specific_solutions)

            # Ładujemy wspólne rozwiązania
            common_file = os.path.join(solutions_dir, "common.json")
            if os.path.isfile(common_file):
                with open(common_file, 'r') as f:
                    common_solutions = json.load(f)
                solutions_db.update(common_solutions)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania bazy danych rozwiązań: {str(e)}")

        return solutions_db

    def run(self, path: str = ".", level: str = "basic") -> List[Dict[str, Any]]:
        """
        Uruchamia diagnostykę dla projektu.

        Args:
            path: Ścieżka do projektu.
            level: Poziom diagnostyki (basic, advanced, full).

        Returns:
            Lista zidentyfikowanych problemów.
        """
        # Normalizujemy ścieżkę
        path = os.path.abspath(path)
        logger.info(f"Uruchamianie diagnostyki dla katalogu: {path} (poziom: {level})")

        # Lista na znalezione problemy
        issues = []

        # Sprawdzamy, czy katalog istnieje
        if not os.path.isdir(path):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Katalog projektu nie istnieje",
                "description": f"Katalog {path} nie istnieje.",
                "solution": "Utwórz katalog projektu lub użyj poprawnej ścieżki.",
                "severity": "critical",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })
            return issues

        # Podstawowe sprawdzenia (dla wszystkich poziomów)
        issues.extend(self._check_filesystem(path))
        issues.extend(self._check_permissions(path))
        issues.extend(self._check_dependencies(path))

        # Zaawansowane sprawdzenia (dla poziomów advanced i full)
        if level in ["advanced", "full"]:
            issues.extend(self._check_configuration(path))
            issues.extend(self._check_repository(path))
            issues.extend(self._check_networking())

        # Pełne sprawdzenia (tylko dla poziomu full)
        if level == "full":
            issues.extend(self._check_system_resources())
            issues.extend(self._check_logs(path))
            issues.extend(self._check_database(path))

        # Sortujemy problemy według ważności
        severity_order = {
            "critical": 0,
            "error": 1,
            "warning": 2,
            "info": 3
        }

        issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 999))

        logger.info(f"Znaleziono {len(issues)} problemów.")
        return issues

    def _check_filesystem(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z systemem plików.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy podstawowe pliki i katalogi istnieją
        essential_files = [
            "infrash.yaml", "infrash.yml",
            ".infrash/config.yaml", ".infrash/config.yml",
            "requirements.txt", "pyproject.toml", "setup.py",
            "Dockerfile", "docker-compose.yml"
        ]

        file_exists = False
        for file in essential_files:
            if os.path.isfile(os.path.join(path, file)):
                file_exists = True
                break

        if not file_exists:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak plików konfiguracyjnych",
                "description": "Nie znaleziono żadnych plików konfiguracyjnych projektu.",
                "solution": "Zainicjalizuj projekt za pomocą 'infrash init'.",
                "severity": "warning",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy jest wystarczająco dużo miejsca na dysku
        try:
            disk_usage = shutil.disk_usage(path)
            free_space_gb = disk_usage.free / (1024 ** 3)

            if free_space_gb < 1.0:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Mało miejsca na dysku",
                    "description": f"Na dysku pozostało tylko {free_space_gb:.2f} GB wolnego miejsca.",
                    "solution": "Zwolnij miejsce na dysku lub użyj innej partycji.",
                    "severity": "warning",
                    "category": "filesystem",
                    "metadata": {
                        "free_space_gb": free_space_gb
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania miejsca na dysku: {str(e)}")

        return issues

    def _check_permissions(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z uprawnieniami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy mamy uprawnienia do zapisu w katalogu projektu
        if not os.access(path, os.W_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do zapisu",
                "description": f"Brak uprawnień do zapisu w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy mamy uprawnienia do wykonywania plików w katalogu projektu
        if not os.access(path, os.X_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do wykonywania",
                "description": f"Brak uprawnień do wykonywania plików w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # W systemach Unix sprawdzamy właściciela i grupę
        if os.name == "posix":
            try:
                owner = os.stat(path).st_uid
                current_user = os.getuid()

                if owner != current_user:
                    import pwd
                    owner_name = pwd.getpwuid(owner).pw_name
                    current_user_name = pwd.getpwuid(current_user).pw_name

                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Katalog należy do innego użytkownika",
                        "description": f"Katalog {path} należy do użytkownika {owner_name}, a aktualny użytkownik to {current_user_name}.",
                        "solution": f"Zmień właściciela katalogu: sudo chown -R {current_user_name}:{current_user_name} {path}",
                        "severity": "warning",
                        "category": "permissions",
                        "metadata": {
                            "path": path,
                            "owner": owner_name,
                            "current_user": current_user_name
                        }
                    })
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania właściciela katalogu: {str(e)}")

        return issues

    def _check_dependencies(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z zależnościami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy wszystkie zależności są zainstalowane
        missing_deps = check_dependencies(path)

        if missing_deps:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brakujące zależności",
                "description": f"Brakujące zależności: {', '.join(missing_deps)}",
                "solution": f"Zainstaluj brakujące zależności: infrash install",
                "severity": "error",
                "category": "dependencies",
                "metadata": {
                    "missing_dependencies": missing_deps
                }
            })

        # Sprawdzamy, czy Python jest w wymaganej wersji
        try:
            # Sprawdzamy, czy istnieje plik z informacją o wymaganej wersji Pythona
            required_version = None

            # Sprawdzamy plik pyproject.toml
            pyproject_path = os.path.join(path, "pyproject.toml")
            if os.path.isfile(pyproject_path):
                with open(pyproject_path, 'r') as f:
                    content = f.read()

                    # Szukamy wymaganej wersji Pythona
                    import re
                    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
                    if match:
                        required_version = match.group(1)

            # Jeśli znaleziono wymaganą wersję, sprawdzamy czy jest kompatybilna
            if required_version:
                import packaging.specifiers
                import packaging.version

                current_version = platform.python_version()
                specifier = packaging.specifiers.SpecifierSet(required_version)

                if not specifier.contains(current_version):
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Niekompatybilna wersja Pythona",
                        "description": f"Aktualna wersja Pythona ({current_version}) nie jest kompatybilna z wymaganą ({required_version}).",
                        "solution": "Zainstaluj kompatybilną wersję Pythona lub użyj wirtualnego środowiska.",
                        "severity": "error",
                        "category": "dependencies",
                        "metadata": {
                            "current_version": current_version,
                            "required_version": required_version
                        }
                    })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wersji Pythona: {str(e)}")

        return issues

    def _check_configuration(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z konfiguracją.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy istnieje plik konfiguracyjny
        config_paths = [
            os.path.join(path, "infrash.yaml"),
            os.path.join(path, "infrash.yml"),
            os.path.join(path, ".infrash", "config.yaml"),
            os.path.join(path, ".infrash", "config.yml")
        ]

        config_file = None
        for config_path in config_paths:
            if os.path.isfile(config_path):
                config_file = config_path
                break

        if not config_file:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak pliku konfiguracyjnego",
                "description": "Nie znaleziono pliku konfiguracyjnego infrash.",
                "solution": "Utwórz plik konfiguracyjny lub zainicjalizuj projekt: infrash init",
                "severity": "warning",
                "category": "configuration",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma pliku konfiguracyjnego

        # Sprawdzamy, czy plik konfiguracyjny jest poprawny
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Sprawdzamy, czy konfiguracja zawiera wymagane pola
            required_fields = ["environments"]

            for field in required_fields:
                if field not in config:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Brak wymaganego pola w konfiguracji",
                        "description": f"W pliku konfiguracyjnym brakuje wymaganego pola: {field}",
                        "solution": f"Dodaj pole {field} do pliku konfiguracyjnego.",
                        "severity": "error",
                        "category": "configuration",
                        "metadata": {
                            "config_file": config_file,
                            "missing_field": field
                        }
                    })

            # Sprawdzamy, czy przynajmniej jedno środowisko jest zdefiniowane
            if "environments" in config and not config["environments"]:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdefiniowanych środowisk",
                    "description": "W pliku konfiguracyjnym nie zdefiniowano żadnych środowisk.",
                    "solution": "Dodaj definicję przynajmniej jednego środowiska do pliku konfiguracyjnego.",
                    "severity": "error",
                    "category": "configuration",
                    "metadata": {
                        "config_file": config_file
                    }
                })

            # Sprawdzamy, czy dla każdego środowiska zdefiniowano polecenie startowe
            if "environments" in config:
                for env_name, env_config in config["environments"].items():
                    if not env_config.get("start_command"):
                        issues.append({
                            "id": str(uuid.uuid4()),
                            "title": f"Brak polecenia startowego dla środowiska {env_name}",
                            "description": f"W konfiguracji środowiska {env_name} nie zdefiniowano polecenia startowego.",
                            "solution": f"Dodaj pole start_command do konfiguracji środowiska {env_name}.",
                            "severity": "error",
                            "category": "configuration",
                            "metadata": {
                                "config_file": config_file,
                                "environment": env_name
                            }
                        })

        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Błąd podczas parsowania pliku konfiguracyjnego",
                "description": f"Wystąpił błąd podczas parsowania pliku konfiguracyjnego: {str(e)}",
                "solution": "Sprawdź składnię pliku konfiguracyjnego i upewnij się, że jest poprawnym plikiem YAML.",
                "severity": "critical",
                "category": "configuration",
                "metadata": {
                    "config_file": config_file,
                    "error": str(e)
                }
            })

        return issues

    def _check_repository(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z repozytorium git.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy katalog jest repozytorium git
        if not os.path.isdir(os.path.join(path, ".git")):
            # To nie jest błąd, ale dodajemy informację
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak repozytorium git",
                "description": "Katalog nie jest repozytorium git.",
                "solution": "Zainicjalizuj repozytorium git: git init",
                "severity": "info",
                "category": "repository",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma repozytorium

        try:
            # Sprawdzamy, czy repozytorium ma niezatwierdzone zmiany
            repo_status = self.git.get_status(path)

            if repo_status.get("dirty", False):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Niezatwierdzone zmiany w repozytorium",
                    "description": f"Repozytorium ma {repo_status.get('changes', 0)} niezatwierdzonych zmian.",
                    "solution": "Zatwierdź zmiany lub cofnij je: git commit lub git reset",
                    "severity": "warning",
                    "category": "repository",
                    "metadata": {
                        "path": path,
                        "changes": repo_status.get("changes", 0)
                    }
                })

            # Sprawdzamy, czy repozytorium ma skonfigurowane zdalne repozytorium
            remote_url = self.git.get_remote_url(path)

            if not remote_url:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdalnego repozytorium",
                    "description": "Repozytorium nie ma skonfigurowanego zdalnego repozytorium.",
                    "solution": "Dodaj zdalne repozytorium: git remote add origin <url>",
                    "severity": "info",
                    "category": "repository",
                    "metadata": {
                        "path": path
                    }
                })

            # Sprawdzamy, czy repozytorium jest aktualne
            is_behind = self.git.is_behind_remote(path)

            if is_behind:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Repozytorium nie jest aktualne",
                    "description": "Lokalne repozytorium jest nieaktualne w stosunku do zdalnego.",
                    "solution": "Zak


                def _find_package_for_module(self, module_name: str) -> Optional[str]:
        """
        Znajduje nazwę pakietu dla podanego modułu.

        Args:
            module_name: Nazwa modułu.

        Returns:
            Nazwa pakietu lub None, jeśli nie znaleziono.
        """
        # Słownik mapowania między nazwami modułów a nazwami pakietów
        # Często nazwa pakietu to nazwa modułu, ale nie zawsze
        module_to_package = {
            "PIL": "pillow",
            "bs4": "beautifulsoup4",
            "sklearn": "scikit-learn",
            "cv2": "opencv-python",
            "yaml": "pyyaml",
            "dotenv": "python-dotenv",
            "jwt": "pyjwt",
            "cairo": "pycairo",
            "gpiozero": "gpiozero",
            "RPi.GPIO": "RPi.GPIO",
            "sqlalchemy": "sqlalchemy",
            "wx": "wxPython",
            "tkinter": "python3-tk",  # Pakiet systemowy
            "pytest": "pytest",
            "numpy": "numpy",
            "pandas": "pandas",
            "matplotlib": "matplotlib",
            "seaborn": "seaborn",
            "scipy": "scipy",
            "asyncpg": "asyncpg",
            "asyncio": "asyncio",
            "aiohttp": "aiohttp",
            "flask": "flask",
            "django": "django",
            "tornado": "tornado",
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "pyaudio": "pyaudio",
            "pydantic": "pydantic",
            "typing_extensions": "typing-extensions",
            "tqdm": "tqdm",
            "click": "click",
            "tabulate": "tabulate",
            "colorama": "colorama",
            "rich": "rich",
            "pymongo": "pymongo",
            "redis": "redis",
            "elasticsearch": "elasticsearch",
            "cassandra": "cassandra-driver",
            "psycopg2": "psycopg2-binary",
            "mysql": "mysql-connector-python",
            "sqlite3": None,  # Wbudowany w Pythona
            "json": None,  # Wbudowany w Pythona
            "os": None,  # Wbudowany w Pythona
            "sys": None,  # Wbudowany w Pythona
            "time": None,  # Wbudowany w Pythona
            "re": None,  # Wbudowany w Pythona
            "random": None,  # Wbudowany w Pythona
            "datetime": None,  # Wbudowany w Pythona
            "logging": None,  # Wbudowany w Pythona
            "argparse": None,  # Wbudowany w Pythona
            "glob": None,  # Wbudowany w Pythona
            "threading": None,  # Wbudowany w Pythona
            "multiprocessing": None,  # Wbudowany w Pythona
            "subprocess": None,  # Wbudowany w Pythona
            "io": None,  # Wbudowany w Pythona
            "shutil": None,  # Wbudowany w Pythona
            "pathlib": None,  # Wbudowany w Pythona
            "urllib": None,  # Wbudowany w Pythona
            "http": None,  # Wbudowany w Pythona
            "socket": None,  # Wbudowany w Pythona
            "email": None,  # Wbudowany w Pythona
            "collections": None,  # Wbudowany w Pythona
            "functools": None,  # Wbudowany w Pythona
            "itertools": None,  # Wbudowany w Pythona
            "operator": None,  # Wbudowany w Pythona
            "math": None,  # Wbudowany w Pythona
            "statistics": None,  # Wbudowany w Pythona
            "uuid": None,  # Wbudowany w Pythona
            "hashlib": None,  # Wbudowany w Pythona
            "base64": None,  # Wbudowany w Pythona
            "pickle": None,  # Wbudowany w Pythona
            "zipfile": None,  # Wbudowany w Pythona
            "tempfile": None,  # Wbudowany w Pythona
            "configparser": None,  # Wbudowany w Pythona
            "xml": None,  # Wbudowany w Pythona
            "html": None,  # Wbudowany w Pythona
            "csv": None,  # Wbudowany w Pythona
            "codecs": None,  # Wbudowany w Pythona
            "inspect": None,  # Wbudowany w Pythona
            "platform": None,  # Wbudowany w Pythona
        }

        # Sprawdzamy, czy mamy mapowanie dla tego modułu
        if module_name in module_to_package:
            return module_to_package[module_name]

        # Sprawdzamy, czy to podmoduł (np. requests.exceptions)
        parts = module_name.split('.')
        if parts[0] in module_to_package:
            return module_to_package[parts[0]]

        # Domyślnie zwracamy nazwę modułu jako nazwę pakietu
        return module_name

    def solve_asyncio_error(self, error_message: str, script_content: str) -> Dict[str, Any]:
        """
        Analizuje i rozwiązuje problemy związane z asyncio.

        Args:
            error_message: Komunikat o błędzie.
            script_content: Zawartość skryptu.

        Returns:
            Słownik z analizą problemu i rozwiązaniem.
        """
        result = {
            "id": str(uuid.uuid4()),
            "title": "Problem z asyncio",
            "description": f"Wystąpił problem związany z asyncio: {error_message}",
            "solution": "Sprawdź poprawność używania asyncio w skrypcie.",
            "severity": "error",
            "category": "asyncio",
            "metadata": {
                "error_message": error_message
            }
        }

        # Problem 1: RuntimeError: asyncio.run() cannot be called from a running event loop
        if "asyncio.run() cannot be called from a running event loop" in error_message:
            result["title"] = "Próba wywołania asyncio.run() z działającej pętli zdarzeń"
            result["description"] = "Funkcja asyncio.run() nie może być wywołana z działającej pętli zdarzeń."
            result["solution"] = "Zamiast asyncio.run(), użyj await na funkcji asynchronicznej lub utwórz nową pętlę zdarzeń."

            # Proponowana poprawka
            fixed_code = script_content.replace("asyncio.run(", "await ")

            if fixed_code == script_content:
                # Jeśli powyższa zamiana nie zadziałała, próbujemy innego rozwiązania
                fixed_code = script_content.replace(
                    "asyncio.run(main(args.host, args.port))",
                    "loop = asyncio.get_event_loop()\nloop.run_until_complete(main(args.host, args.port))"
                )

            result["metadata"]["fixed_code"] = fixed_code

        # Problem 2: RuntimeWarning: coroutine 'function_name' was never awaited
        elif "was never awaited" in error_message:
            import re
            match = re.search(r"coroutine '([^']+)' was never awaited", error_message)

            if match:
                function_name = match.group(1)
                result["title"] = f"Coroutine '{function_name}' nigdy nie została awaited"
                result["description"] = f"Funkcja asynchroniczna '{function_#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash. Służy do diagnozowania problemów
w projektach i środowiskach uruchomieniowych.
"""

import os
import sys
import platform
import subprocess
import json
import uuid
import psutil
import yaml
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import check_dependencies
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Diagnostics:
    """
    Klasa diagnostyczna do identyfikowania i raportowania problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Diagnostics.
        """
        self.os_info = detect_os()
        self.package_manager = get_package_manager()
        self.git = GitRepo()

        # Ładujemy bazę danych rozwiązań
        self.solutions_db = self._load_solutions_db()

    def _load_solutions_db(self) -> Dict[str, Any]:
        """
        Ładuje bazę danych rozwiązań.

        Returns:
            Słownik z bazą danych rozwiązań.
        """
        solutions_db = {}

        try:
            # Ścieżka do katalogu z rozwiązaniami
            solutions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "solutions")

            # Ładujemy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_file = os.path.join(solutions_dir, f"{os_type}.json")

            if os.path.isfile(os_specific_file):
                with open(os_specific_file, 'r') as f:
                    os_specific_solutions = json.load(f)
                solutions_db.update(os_specific_solutions)

            # Ładujemy wspólne rozwiązania
            common_file = os.path.join(solutions_dir, "common.json")
            if os.path.isfile(common_file):
                with open(common_file, 'r') as f:
                    common_solutions = json.load(f)
                solutions_db.update(common_solutions)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania bazy danych rozwiązań: {str(e)}")

        return solutions_db

    def run(self, path: str = ".", level: str = "basic") -> List[Dict[str, Any]]:
        """
        Uruchamia diagnostykę dla projektu.

        Args:
            path: Ścieżka do projektu.
            level: Poziom diagnostyki (basic, advanced, full).

        Returns:
            Lista zidentyfikowanych problemów.
        """
        # Normalizujemy ścieżkę
        path = os.path.abspath(path)
        logger.info(f"Uruchamianie diagnostyki dla katalogu: {path} (poziom: {level})")

        # Lista na znalezione problemy
        issues = []

        # Sprawdzamy, czy katalog istnieje
        if not os.path.isdir(path):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Katalog projektu nie istnieje",
                "description": f"Katalog {path} nie istnieje.",
                "solution": "Utwórz katalog projektu lub użyj poprawnej ścieżki.",
                "severity": "critical",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })
            return issues

        # Podstawowe sprawdzenia (dla wszystkich poziomów)
        issues.extend(self._check_filesystem(path))
        issues.extend(self._check_permissions(path))
        issues.extend(self._check_dependencies(path))

        # Zaawansowane sprawdzenia (dla poziomów advanced i full)
        if level in ["advanced", "full"]:
            issues.extend(self._check_configuration(path))
            issues.extend(self._check_repository(path))
            issues.extend(self._check_networking())

        # Pełne sprawdzenia (tylko dla poziomu full)
        if level == "full":
            issues.extend(self._check_system_resources())
            issues.extend(self._check_logs(path))
            issues.extend(self._check_database(path))

        # Sortujemy problemy według ważności
        severity_order = {
            "critical": 0,
            "error": 1,
            "warning": 2,
            "info": 3
        }

        issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 999))

        logger.info(f"Znaleziono {len(issues)} problemów.")
        return issues

    def _check_filesystem(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z systemem plików.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy podstawowe pliki i katalogi istnieją
        essential_files = [
            "infrash.yaml", "infrash.yml",
            ".infrash/config.yaml", ".infrash/config.yml",
            "requirements.txt", "pyproject.toml", "setup.py",
            "Dockerfile", "docker-compose.yml"
        ]

        file_exists = False
        for file in essential_files:
            if os.path.isfile(os.path.join(path, file)):
                file_exists = True
                break

        if not file_exists:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak plików konfiguracyjnych",
                "description": "Nie znaleziono żadnych plików konfiguracyjnych projektu.",
                "solution": "Zainicjalizuj projekt za pomocą 'infrash init'.",
                "severity": "warning",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy jest wystarczająco dużo miejsca na dysku
        try:
            disk_usage = shutil.disk_usage(path)
            free_space_gb = disk_usage.free / (1024 ** 3)

            if free_space_gb < 1.0:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Mało miejsca na dysku",
                    "description": f"Na dysku pozostało tylko {free_space_gb:.2f} GB wolnego miejsca.",
                    "solution": "Zwolnij miejsce na dysku lub użyj innej partycji.",
                    "severity": "warning",
                    "category": "filesystem",
                    "metadata": {
                        "free_space_gb": free_space_gb
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania miejsca na dysku: {str(e)}")

        return issues

    def _check_permissions(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z uprawnieniami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy mamy uprawnienia do zapisu w katalogu projektu
        if not os.access(path, os.W_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do zapisu",
                "description": f"Brak uprawnień do zapisu w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy mamy uprawnienia do wykonywania plików w katalogu projektu
        if not os.access(path, os.X_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do wykonywania",
                "description": f"Brak uprawnień do wykonywania plików w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # W systemach Unix sprawdzamy właściciela i grupę
        if os.name == "posix":
            try:
                owner = os.stat(path).st_uid
                current_user = os.getuid()

                if owner != current_user:
                    import pwd
                    owner_name = pwd.getpwuid(owner).pw_name
                    current_user_name = pwd.getpwuid(current_user).pw_name

                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Katalog należy do innego użytkownika",
                        "description": f"Katalog {path} należy do użytkownika {owner_name}, a aktualny użytkownik to {current_user_name}.",
                        "solution": f"Zmień właściciela katalogu: sudo chown -R {current_user_name}:{current_user_name} {path}",
                        "severity": "warning",
                        "category": "permissions",
                        "metadata": {
                            "path": path,
                            "owner": owner_name,
                            "current_user": current_user_name
                        }
                    })
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania właściciela katalogu: {str(e)}")

        return issues

    def _check_dependencies(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z zależnościami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy wszystkie zależności są zainstalowane
        missing_deps = check_dependencies(path)

        if missing_deps:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brakujące zależności",
                "description": f"Brakujące zależności: {', '.join(missing_deps)}",
                "solution": f"Zainstaluj brakujące zależności: infrash install",
                "severity": "error",
                "category": "dependencies",
                "metadata": {
                    "missing_dependencies": missing_deps
                }
            })

        # Sprawdzamy, czy Python jest w wymaganej wersji
        try:
            # Sprawdzamy, czy istnieje plik z informacją o wymaganej wersji Pythona
            required_version = None

            # Sprawdzamy plik pyproject.toml
            pyproject_path = os.path.join(path, "pyproject.toml")
            if os.path.isfile(pyproject_path):
                with open(pyproject_path, 'r') as f:
                    content = f.read()

                    # Szukamy wymaganej wersji Pythona
                    import re
                    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
                    if match:
                        required_version = match.group(1)

            # Jeśli znaleziono wymaganą wersję, sprawdzamy czy jest kompatybilna
            if required_version:
                import packaging.specifiers
                import packaging.version

                current_version = platform.python_version()
                specifier = packaging.specifiers.SpecifierSet(required_version)

                if not specifier.contains(current_version):
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Niekompatybilna wersja Pythona",
                        "description": f"Aktualna wersja Pythona ({current_version}) nie jest kompatybilna z wymaganą ({required_version}).",
                        "solution": "Zainstaluj kompatybilną wersję Pythona lub użyj wirtualnego środowiska.",
                        "severity": "error",
                        "category": "dependencies",
                        "metadata": {
                            "current_version": current_version,
                            "required_version": required_version
                        }
                    })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wersji Pythona: {str(e)}")

        return issues

    def _check_configuration(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z konfiguracją.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy istnieje plik konfiguracyjny
        config_paths = [
            os.path.join(path, "infrash.yaml"),
            os.path.join(path, "infrash.yml"),
            os.path.join(path, ".infrash", "config.yaml"),
            os.path.join(path, ".infrash", "config.yml")
        ]

        config_file = None
        for config_path in config_paths:
            if os.path.isfile(config_path):
                config_file = config_path
                break

        if not config_file:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak pliku konfiguracyjnego",
                "description": "Nie znaleziono pliku konfiguracyjnego infrash.",
                "solution": "Utwórz plik konfiguracyjny lub zainicjalizuj projekt: infrash init",
                "severity": "warning",
                "category": "configuration",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma pliku konfiguracyjnego

        # Sprawdzamy, czy plik konfiguracyjny jest poprawny
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Sprawdzamy, czy konfiguracja zawiera wymagane pola
            required_fields = ["environments"]

            for field in required_fields:
                if field not in config:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Brak wymaganego pola w konfiguracji",
                        "description": f"W pliku konfiguracyjnym brakuje wymaganego pola: {field}",
                        "solution": f"Dodaj pole {field} do pliku konfiguracyjnego.",
                        "severity": "error",
                        "category": "configuration",
                        "metadata": {
                            "config_file": config_file,
                            "missing_field": field
                        }
                    })

            # Sprawdzamy, czy przynajmniej jedno środowisko jest zdefiniowane
            if "environments" in config and not config["environments"]:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdefiniowanych środowisk",
                    "description": "W pliku konfiguracyjnym nie zdefiniowano żadnych środowisk.",
                    "solution": "Dodaj definicję przynajmniej jednego środowiska do pliku konfiguracyjnego.",
                    "severity": "error",
                    "category": "configuration",
                    "metadata": {
                        "config_file": config_file
                    }
                })

            # Sprawdzamy, czy dla każdego środowiska zdefiniowano polecenie startowe
            if "environments" in config:
                for env_name, env_config in config["environments"].items():
                    if not env_config.get("start_command"):
                        issues.append({
                            "id": str(uuid.uuid4()),
                            "title": f"Brak polecenia startowego dla środowiska {env_name}",
                            "description": f"W konfiguracji środowiska {env_name} nie zdefiniowano polecenia startowego.",
                            "solution": f"Dodaj pole start_command do konfiguracji środowiska {env_name}.",
                            "severity": "error",
                            "category": "configuration",
                            "metadata": {
                                "config_file": config_file,
                                "environment": env_name
                            }
                        })

        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Błąd podczas parsowania pliku konfiguracyjnego",
                "description": f"Wystąpił błąd podczas parsowania pliku konfiguracyjnego: {str(e)}",
                "solution": "Sprawdź składnię pliku konfiguracyjnego i upewnij się, że jest poprawnym plikiem YAML.",
                "severity": "critical",
                "category": "configuration",
                "metadata": {
                    "config_file": config_file,
                    "error": str(e)
                }
            })

        return issues

    def _check_repository(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z repozytorium git.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy katalog jest repozytorium git
        if not os.path.isdir(os.path.join(path, ".git")):
            # To nie jest błąd, ale dodajemy informację
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak repozytorium git",
                "description": "Katalog nie jest repozytorium git.",
                "solution": "Zainicjalizuj repozytorium git: git init",
                "severity": "info",
                "category": "repository",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma repozytorium

        try:
            # Sprawdzamy, czy repozytorium ma niezatwierdzone zmiany
            repo_status = self.git.get_status(path)

            if repo_status.get("dirty", False):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Niezatwierdzone zmiany w repozytorium",
                    "description": f"Repozytorium ma {repo_status.get('changes', 0)} niezatwierdzonych zmian.",
                    "solution": "Zatwierdź zmiany lub cofnij je: git commit lub git reset",
                    "severity": "warning",
                    "category": "repository",
                    "metadata": {
                        "path": path,
                        "changes": repo_status.get("changes", 0)
                    }
                })

            # Sprawdzamy, czy repozytorium ma skonfigurowane zdalne repozytorium
            remote_url = self.git.get_remote_url(path)

            if not remote_url:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdalnego repozytorium",
                    "description": "Repozytorium nie ma skonfigurowanego zdalnego repozytorium.",
                    "solution": "Dodaj zdalne repozytorium: git remote add origin <url>",
                    "severity": "info",
                    "category": "repository",
                    "metadata": {
                        "path": path
                    }
                })

            # Sprawdzamy, czy repozytorium jest aktualne
            is_behind = self.git.is_behind_remote(path)

            if is_behind:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Repozytorium nie jest aktualne",
                    "description": "Lokalne repozytorium jest nieaktualne w stosunku do zdalnego.",
                    "solution": "Zaktualizuj repozytorium: git pull",
                    "severity": "warning",
                    "category": "repository",
                    "metadata": {
                        "path": path,
                        "commits_behind": self.git.get_commits_behind(path)
                    }
                })

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania repozytorium: {str(e)}")

        return issues

    def _check_networking(self) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z siecią.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy połączenie z internetem
        try:
            # Próbujemy połączyć się z serwerem Google
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak połączenia z internetem",
                "description": f"Nie można nawiązać połączenia z internetem: {str(e)}",
                "solution": "Sprawdź połączenie sieciowe i ustawienia zapory.",
                "severity": "error",
                "category": "networking",
                "metadata": {
                    "error": str(e)
                }
            })

        # Sprawdzamy lokalną sieć
        try:
            # Pobieramy adres IP hosta
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)

            # Sprawdzamy, czy to nie jest adres loopback
            if ip.startswith("127."):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak lokalnego adresu IP",
                    "description": f"Host ma tylko adres loopback: {ip}",
                    "solution": "Sprawdź połączenie sieciowe i ustawienia interfejsu.",
                    "severity": "warning",
                    "category": "networking",
                    "metadata": {
                        "hostname": hostname,
                        "ip": ip
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania lokalnego adresu IP: {str(e)}")

        # Sprawdzamy otwarte porty
        try:
            # Sprawdzamy popularne porty, które mogą być potrzebne
            common_ports = {
                80: "HTTP",
                443: "HTTPS",
                22: "SSH",
                5000: "Flask",
                8000: "Django/Web",
                8080: "Alternate HTTP"
            }

            # Sprawdzamy, czy porty są zajęte
            for port, service in common_ports.items():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()

                # Jeśli port jest otwarty (0 oznacza sukces), dodajemy informację
                if result == 0:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": f"Port {port} ({service}) jest już używany",
                        "description": f"Port {port}, który może być potrzebny dla serwisu {service}, jest już używany przez inny proces.",
                        "solution": f"Zmień port w konfiguracji lub zatrzymaj proces używający portu {port}.",
                        "severity": "info",
                        "category": "networking",
                        "metadata": {
                            "port": port,
                            "service": service
                        }
                    })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania portów: {str(e)}")

        return issues

    def _check_system_resources(self) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z zasobami systemowymi.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy użycie CPU
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent > 90:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Wysokie obciążenie CPU",
                    "description": f"Obciążenie CPU wynosi {cpu_percent}%, co może spowodować problemy z wydajnością.",
                    "solution": "Zamknij niepotrzebne procesy lub przełącz się na mocniejszą maszynę.",
                    "severity": "warning",
                    "category": "resources",
                    "metadata": {
                        "cpu_percent": cpu_percent
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania obciążenia CPU: {str(e)}")

        # Sprawdzamy użycie pamięci
        try:
            memory = psutil.virtual_memory()

            if memory.percent > 90:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Mało wolnej pamięci RAM",
                    "description": f"Wykorzystanie pamięci RAM wynosi {memory.percent}%, pozostało tylko {memory.available / (1024**2):.1f} MB wolnej pamięci.",
                    "solution": "Zamknij niepotrzebne procesy lub zwiększ ilość pamięci RAM.",
                    "severity": "warning",
                    "category": "resources",
                    "metadata": {
                        "memory_percent": memory.percent,
                        "memory_available_mb": memory.available / (1024**2)
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania pamięci RAM: {str(e)}")

        return issues

    def _check_logs(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza logi w poszukiwaniu problemów.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Katalogi, w których mogą znajdować się logi
        log_dirs = [
            os.path.join(path, "logs"),
            os.path.join(path, "log"),
            os.path.join(path, ".logs"),
            os.path.join(path, ".infrash", "logs")
        ]

        # Słowa kluczowe, które mogą wskazywać na problemy
        error_keywords = [
            "error", "exception", "failed", "failure", "fatal", "panic", "critical"
        ]

        # Sprawdzamy każdy katalog z logami
        for log_dir in log_dirs:
            if not os.path.isdir(log_dir):
                continue

            # Szukamy plików logów
            log_files = []
            for root, _, files in os.walk(log_dir):
                for file in files:
                    if file.endswith(".log") or file.endswith(".txt"):
                        log_files.append(os.path.join(root, file))

            # Sprawdzamy każdy plik logów
            for log_file in log_files:
                try:
                    # Otwieramy plik i szukamy problemów
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # Czytamy ostatnie 100 linii (lub mniej, jeśli plik jest krótszy)
                        lines = f.readlines()[-100:]

                        # Szukamy linii z błędami
                        error_lines = []
                        for i, line in enumerate(lines):
                            if any(keyword in line.lower() for keyword in error_keywords):
                                error_lines.append((i, line.strip()))

                        # Jeśli znaleziono błędy, dodajemy problem
                        if error_lines:
                            # Wybieramy ostatni błąd
                            last_error = error_lines[-1][1]

                            issues.append({
                                "id": str(uuid.uuid4()),
                                "title": "Błędy w logach",
                                "description": f"Znaleziono {len(error_lines)} linii z błędami w pliku {os.path.basename(log_file)}. Ostatni błąd: {last_error[:100]}...",
                                "solution": "Sprawdź logi, aby zidentyfikować przyczynę błędów.",
                                "severity": "warning",
                                "category": "logs",
                                "metadata": {
                                    "log_file": log_file,
                                    "error_count": len(error_lines),
                                    "last_error": last_error
                                }
                            })
                except Exception as e:
                    logger.error(f"Błąd podczas sprawdzania pliku logu {log_file}: {str(e)}")

        return issues

    def _check_database(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z bazą danych.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy projekt używa bazy danych
        db_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".db") or file.endswith(".sqlite") or file.endswith(".sqlite3"):
                    db_files.append(os.path.join(root, file))

        # Jeśli nie znaleziono plików bazy danych, kończymy
        if not db_files:
            return issues

        # Sprawdzamy każdy plik bazy danych
        for db_file in db_files:
            try:
                # Sprawdzamy, czy plik bazy danych jest dostępny do odczytu
                if not os.access(db_file, os.R_OK):
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Brak dostępu do bazy danych",
                        "description": f"Brak uprawnień do odczytu pliku bazy danych: {os.path.basename(db_file)}",
                        "solution": "Zmień uprawnienia do pliku bazy danych.",
                        "severity": "error",
                        "category": "database",
                        "metadata": {
                            "db_file": db_file
                        }
                    })
                    continue

                # Sprawdzamy, czy plik bazy danych jest uszkodzony
                import sqlite3
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Sprawdzamy, czy możemy wykonać prostą operację
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]

                if result != "ok":
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Uszkodzona baza danych",
                        "description": f"Plik bazy danych {os.path.basename(db_file)} jest uszkodzony: {result}",
                        "solution": "Przywróć bazę danych z kopii zapasowej lub napraw ją.",
                        "severity": "critical",
                        "category": "database",
                        "metadata": {
                            "db_file": db_file,
                            "integrity_check": result
                        }
                    })

                conn.close()
            except Exception as e:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Problem z bazą danych",
                    "description": f"Wystąpił problem z bazą danych {os.path.basename(db_file)}: {str(e)}",
                    "solution": "Sprawdź plik bazy danych i upewnij się, że jest poprawny.",
                    "severity": "error",
                    "category": "database",
                    "metadata": {
                        "db_file": db_file,
                        "error": str(e)
                    }
                })

        return issues

    def _check_process_handling(self, path: str, script_path: str, command: str) -> Dict[str, Any]:
        """
        Analizuje błędy związane z uruchamianiem procesów i skryptów.

        Args:
            path: Ścieżka do projektu.
            script_path: Ścieżka do skryptu.
            command: Polecenie, które spowodowało błąd.

        Returns:
            Słownik z analizą problemu i rozwiązaniem.
        """
        # Podstawowy wynik
        result = {
            "id": str(uuid.uuid4()),
            "title": "Problem z uruchomieniem procesu",
            "description": f"Wystąpił problem podczas uruchamiania polecenia: {command}",
            "solution": "Sprawdź składnię polecenia i upewnij się, że wszystkie wymagane pakiety są zainstalowane.",
            "severity": "error",
            "category": "process",
            "metadata": {
                "command": command,
                "script_path": script_path
            }
        }

        try:
            # Wykonujemy polecenie z przechwyceniem wyjścia
            process = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=path,
                timeout=5  # Maksymalny czas wykonania
            )

            # Jeśli polecenie zakończyło się błędem, analizujemy wyjście
            if process.returncode != 0:
                stderr = process.stderr.strip()

                # Analizujemy różne typy błędów
                if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                    # Próbujemy znaleźć nazwę brakującego modułu
                    import re
                    match = re.search(r"No module named '([^']+)'", stderr)

                    if match:
                        module_name = match.group(1)
                        result["title"] = f"Brakujący moduł: {module_name}"
                        result["description"] = f"Nie można zaimportować modułu {module_name}."
                        result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"
                        result["metadata"]["missing_module"] = module_name

                elif "SyntaxError" in stderr:
                    result["title"] = "Błąd składni"
                    result["description"] = f"Skrypt zawiera błąd składni: {stderr}"
                    result["solution"] = "Popraw błąd składni w skrypcie."

                elif "PermissionError" in stderr:
                    result["title"] = "Błąd uprawnień"
                    result["description"] = f"Brak odpowiednich uprawnień: {stderr}"
                    result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

                elif "FileNotFoundError" in stderr:
                    # Próbujemy znaleźć nazwę brakującego pliku
                    import re
                    match = re.search(r"No such file or directory: '([^']+)'", stderr)

                    if match:
                        file_name = match.group(1)
                        result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
                        result["description"] = f"Nie można znaleźć pliku: {file_name}"
                        result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
                        result["metadata"]["missing_file"] = file_name

                else:
                    # Ogólny błąd
                    result["description"] = f"Polecenie zakończyło się błędem (kod {process.returncode}): {stderr}"

        except subprocess.TimeoutExpired:
            result["title"] = "Timeout podczas wykonywania polecenia"
            result["description"] = f"Polecenie nie zakończyło się w wyznaczonym czasie: {command}"
            result["solution"] = "Sprawdź, czy polecenie nie zawiesza się lub nie wymaga interakcji użytkownika."
            result["severity"] = "warning"

        except Exception as e:
            result["description"] = f"Wystąpił nieoczekiwany błąd podczas analizy polecenia: {str(e)}"

        return result

    def analyze_script_error(self, script_path: str, error_message: str) -> Dict[str, Any]:
        """
        Analizuje błąd wykonania skryptu Python.

        Args:
            script_path: Ścieżka do skryptu.
            error_message: Komunikat o błędzie.

        Returns:
            Słownik z analizą problemu i rozwiązaniem.
        """
        # Podstawowy wynik
        result = {
            "id": str(uuid.uuid4()),
            "title": "Błąd wykonania skryptu",
            "description": f"Wystąpił błąd podczas wykonywania skryptu {os.path.basename(script_path)}: {error_message}",
            "solution": "Debuguj skrypt, aby znaleźć przyczynę błędu.",
            "severity": "error",
            "category": "script",
            "metadata": {
                "script_path": script_path,
                "error_message": error_message
            }
        }

        # Analizujemy różne typy błędów
        if "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            # Próbujemy znaleźć nazwę brakującego modułu
            import re
            match = re.search(r"No module named '([^']+)'", error_message)

            if match:
                module_name = match.group(1)
                result["title"] = f"Brakujący moduł: {module_name}"
                result["description"] = f"Nie można zaimportować modułu {module_name}."

                # Szukamy odpowiedniego pakietu dla modułu
                package_name = self._find_package_for_module(module_name)

                if package_name:
                    result["solution"] = f"Zainstaluj brakujący moduł: pip install {package_name}"
                else:
                    result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"

                result["metadata"]["missing_module"] = module_name
                result["metadata"]["package_name"] = package_name

        elif "SyntaxError" in error_message:
            # Próbujemy znaleźć linię z błędem
            import re
            match = re.search(r"line (\d+)", error_message)

            if match:
                line_number = match.group(1)
                result["title"] = f"Błąd składni w linii {line_number}"
                result["description"] = f"Skrypt zawiera błąd składni w linii {line_number}: {error_message}"
                result["solution"] = f"Popraw błąd składni w linii {line_number} skryptu."
                result["metadata"]["line_number"] = line_number

        elif "PermissionError" in error_message:
            result["title"] = "Błąd uprawnień"
            result["description"] = f"Brak odpowiednich uprawnień: {error_message}"
            result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

        elif "FileNotFoundError" in error_message:
            # Próbujemy znaleźć nazwę brakującego pliku
            import re
            match = re.search(r"No such file or directory: '([^']+)'", error_message)

            if match:
                file_name = match.group(1)
                result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
                result["description"] = f"Nie można znaleźć pliku: {file_name}"
                result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
                result["metadata"]["missing_file"] = file_name

        elif "ConnectionRefusedError" in error_message or "ConnectionError" in error_message:
            result["title"] = "Błąd połączenia"
            result["description"] = f"Nie można nawiązać połączenia: {error_message}"
            result["solution"] = "Sprawdź, czy serwer jest uruchomiony i dostępny."
            result["category"] = "networking"

        elif "TimeoutError" in error_message:
            result["title"] = "Timeout połączenia"
            result["description"] = f"Upłynął limit czasu połączenia: {error_message}"
            result["solution"] = "Sprawdź, czy serwer jest dostępny i czy limit czasu jest wystarczający."
            result["category"] = "networking"

        return result

function_name = match.group(1)
result["title"] = f"Coroutine '{function_name}' nigdy nie została awaited"
result["description"] = f"Funkcja asynchroniczna '{function_name}' została wywołana, ale nie została awaited."
result["solution"] = f"Dodaj 'await' przed wywołaniem funkcji '{function_name}' lub użyj asyncio.run()."

# Proponowana poprawka
fixed_code = script_content.replace(f"{function_name}(", f"await {function_name}(")
result["metadata"]["fixed_code"] = fixed_code

# Problem 3: SyntaxError: 'await' outside async function
elif "'await' outside async function" in error_message:
result["title"] = "'await' poza funkcją asynchroniczną"
result["description"] = "Operator 'await' może być używany tylko wewnątrz funkcji asynchronicznej."
result["solution"] = "Przekształć funkcję na asynchroniczną (async def) lub użyj asyncio.run()."

# Proponowana poprawka - znajdujemy funkcję, która zawiera await
import re
lines = script_content.split('\n')

# Szukamy linii z await
await_lines = []
for i, line in enumerate(lines):
    if "await" in line:
        await_lines.append(i)

if await_lines:
    # Dla każdej linii z await, szukamy najbliższej definicji funkcji
    for line_num in await_lines:
        # Szukamy wstecz do definicji funkcji
        for i in range(line_num, -1, -1):
            if re.search(r"def\s+\w+\s*\(", lines[i]):
                # Znaleziono definicję funkcji - dodajemy async
                if "async def" not in lines[i]:
                    lines[i] = lines[i].replace("def", "async def")
                break

    fixed_code = '\n'.join(lines)
    result["metadata"]["fixed_code"] = fixed_code

# Problem 4: SyntaxError: 'yield' inside async function
elif "'yield' inside async function" in error_message:
result["title"] = "'yield' wewnątrz funkcji asynchronicznej"
result["description"] = "W Pythonie 3.5-3.6 nie można używać 'yield' wewnątrz funkcji asynchronicznej (async def)."
result["solution"] = "Przekształć funkcję na zwykłą (def) lub zaktualizuj Python do wersji 3.7+ i użyj 'async for'."

# Proponowana poprawka
import re
fixed_code = re.sub(r"async\s+def", "def", script_content)
result["metadata"]["fixed_code"] = fixed_code

# Problem 5: AttributeError: module 'asyncio' has no attribute 'run'
elif "module 'asyncio' has no attribute 'run'" in error_message:
result["title"] = "Funkcja asyncio.run() nie jest dostępna"
result["description"] = "Funkcja asyncio.run() została wprowadzona w Pythonie 3.7. Używasz starszej wersji Pythona."
result["solution"] = "Zaktualizuj Python do wersji 3.7+ lub użyj alternatywnej metody uruchamiania coroutines."

# Proponowana poprawka
fixed_code = script_content.replace(
    "asyncio.run(main(args.host, args.port))",
    "loop = asyncio.get_event_loop()\nloop.run_until_complete(main(args.host, args.port))\nloop.close()"
)
result["metadata"]["fixed_code"] = fixed_code

return result

def fix_connection_issues(self, error_message: str, host: str, port: int) -> Dict[str, Any]:
    """
    Analizuje i rozwiązuje problemy z połączeniem.

    Args:
        error_message: Komunikat o błędzie.
        host: Adres hosta.
        port: Numer portu.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    result = {
        "id": str(uuid.uuid4()),
        "title": "Problem z połączeniem",
        "description": f"Wystąpił problem z połączeniem do {host}:{port}: {error_message}",
        "solution": "Sprawdź, czy serwer jest uruchomiony i czy port jest dostępny.",
        "severity": "error",
        "category": "networking",
        "metadata": {
            "error_message": error_message,
            "host": host,
            "port": port
        }
    }

    # Problem 1: ConnectionRefusedError
    if "ConnectionRefusedError" in error_message:
        result["title"] = "Połączenie odrzucone"
        result["description"] = f"Serwer na {host}:{port} odrzucił połączenie."

        # Sprawdzamy, czy host jest adresem lokalnym
        local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if host in local_hosts:
            # Sprawdzamy, czy port jest używany przez inny proces
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result_code = sock.connect_ex((host, port))
                sock.close()

                if result_code == 0:
                    # Port jest już używany
                    result["description"] = f"Port {port} jest już używany przez inny proces."
                    result["solution"] = f"Użyj innego portu lub zatrzymaj proces używający portu {port}."
                else:
                    # Port nie jest używany - prawdopodobnie serwer nie jest uruchomiony
                    result["solution"] = f"Uruchom serwer na porcie {port} lub sprawdź konfigurację zapory."
            except Exception:
                pass
        else:
            # Host zdalny - sprawdzamy dostępność
            try:
                import socket
                # Sprawdzamy, czy host jest dostępny
                socket.gethostbyname(host)
                result["solution"] = f"Sprawdź, czy serwer na {host} jest uruchomiony i nasłuchuje na porcie {port}."
            except socket.gaierror:
                result["title"] = "Nie można rozwiązać nazwy hosta"
                result["description"] = f"Nie można rozwiązać nazwy hosta: {host}"
                result["solution"] = "Sprawdź, czy nazwa hosta jest poprawna i czy masz połączenie z internetem."

    # Problem 2: TimeoutError
    elif "TimeoutError" in error_message:
        result["title"] = "Timeout połączenia"
        result["description"] = f"Upłynął limit czasu podczas łączenia się z {host}:{port}."

        # Sprawdzamy, czy host jest dostępny
        try:
            import socket
            socket.gethostbyname(host)
            result["solution"] = f"Sprawdź, czy host {host} jest dostępny w sieci i czy zapora nie blokuje połączeń na porcie {port}."
        except socket.gaierror:
            result["title"] = "Nie można rozwiązać nazwy hosta"
            result["description"] = f"Nie można rozwiązać nazwy hosta: {host}"
            result["solution"] = "Sprawdź, czy nazwa hosta jest poprawna i czy masz połączenie z internetem."

    # Problem 3: AddressBindingError (możliwe, że próbujemy nasłuchiwać na adresie, który jest już używany)
    elif "Address already in use" in error_message:
        result["title"] = "Adres już w użyciu"
        result["description"] = f"Adres {host}:{port} jest już używany przez inny proces."
        result["solution"] = f"Użyj innego portu lub zatrzymaj proces używający portu {port}."

        # Próbujemy znaleźć proces używający portu
        try:
            if os.name == "posix":
                # W systemach Unix używamy lsof
                import subprocess
                process = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process.returncode == 0:
                    output = process.stdout.strip()
                    lines = output.split('\n')
                    if len(lines) > 1:
                        # Pierwsza linia to nagłówek, druga to dane procesu
                        process_info = lines[1].split()
                        if len(process_info) > 1:
                            process_name = process_info[0]
                            process_pid = process_info[1]
                            result["solution"] = f"Zatrzymaj proces {process_name} (PID: {process_pid}) używający portu {port} lub użyj innego portu."
                            result["metadata"]["process_name"] = process_name
                            result["metadata"]["process_pid"] = process_pid

            elif os.name == "nt":
                # W systemach Windows używamy netstat
                import subprocess
                process = subprocess.run(
                    ["netstat", "-ano", "|", "findstr", f":{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    shell=True
                )

                if process.returncode == 0:
                    output = process.stdout.strip()
                    lines = output.split('\n')
                    if lines:
                        # Szukamy linii z naszym portem
                        for line in lines:
                            if f":{port}" in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    process_pid = parts[4]
                                    result["solution"] = f"Zatrzymaj proces o PID {process_pid} używający portu {port} lub użyj innego portu."
                                    result["metadata"]["process_pid"] = process_pid
                                break
        except Exception:
            pass

    # Problem 4: Permission denied (gdy próbujemy nasłuchiwać na porcie < 1024 bez uprawnień roota)
    elif "Permission denied" in error_message and port < 1024:
        result["title"] = "Brak uprawnień do nasłuchiwania na porcie"
        result["description"] = f"Brak uprawnień do nasłuchiwania na porcie {port}. Porty poniżej 1024 wymagają uprawnień administratora."
        result["solution"] = f"Użyj portu powyżej 1024 lub uruchom program z uprawnieniami administratora."

    return result

def analyze_hardware_issues(self, error_message: str, hardware_type: str) -> Dict[str, Any]:
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

    return result    def _find_package_for_module(self, module_name: str) -> Optional[str]:
        """
        Znajduje nazwę pakietu dla podanego modułu.

        Args:
            module_name: Nazwa modułu.

        Returns:
            Nazwa pakietu lub None, jeśli nie znaleziono.
        """
    # Słownik mapowania między nazwami modułów a nazwami pakietów
    # Często nazwa pakietu to nazwa modułu, ale nie zawsze
    module_to_package = {
        "PIL": "pillow",
        "bs4": "beautifulsoup4",
        "sklearn": "scikit-learn",
        "cv2": "opencv-python",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "jwt": "pyjwt",
        "cairo": "pycairo",
        "gpiozero": "gpiozero",
        "RPi.GPIO": "RPi.GPIO",
        "sqlalchemy": "sqlalchemy",
        "wx": "wxPython",
        "tkinter": "python3-tk",  # Pakiet systemowy
        "pytest": "pytest",
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "scipy": "scipy",
        "asyncpg": "asyncpg",
        "asyncio": "asyncio",
        "aiohttp": "aiohttp",
        "flask": "flask",
        "django": "django",
        "tornado": "tornado",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pyaudio": "pyaudio",
        "pydantic": "pydantic",
        "typing_extensions": "typing-extensions",
        "tqdm": "tqdm",
        "click": "click",
        "tabulate": "tabulate",
        "colorama": "colorama",
        "rich": "rich",
        "pymongo": "pymongo",
        "redis": "redis",
        "elasticsearch": "elasticsearch",
        "cassandra": "cassandra-driver",
        "psycopg2": "psycopg2-binary",
        "mysql": "mysql-connector-python",
        "sqlite3": None,  # Wbudowany w Pythona
        "json": None,  # Wbudowany w Pythona
        "os": None,  # Wbudowany w Pythona
        "sys": None,  # Wbudowany w Pythona
        "time": None,  # Wbudowany w Pythona
        "re": None,  # Wbudowany w Pythona
        "random": None,  # Wbudowany w Pythona
        "datetime": None,  # Wbudowany w Pythona
        "logging": None,  # Wbudowany w Pythona
        "argparse": None,  # Wbudowany w Pythona
        "glob": None,  # Wbudowany w Pythona
        "threading": None,  # Wbudowany w Pythona
        "multiprocessing": None,  # Wbudowany w Pythona
        "subprocess": None,  # Wbudowany w Pythona
        "io": None,  # Wbudowany w Pythona
        "shutil": None,  # Wbudowany w Pythona
        "pathlib": None,  # Wbudowany w Pythona
        "urllib": None,  # Wbudowany w Pythona
        "http": None,  # Wbudowany w Pythona
        "socket": None,  # Wbudowany w Pythona
        "email": None,  # Wbudowany w Pythona
        "collections": None,  # Wbudowany w Pythona
        "functools": None,  # Wbudowany w Pythona
        "itertools": None,  # Wbudowany w Pythona
        "operator": None,  # Wbudowany w Pythona
        "math": None,  # Wbudowany w Pythona
        "statistics": None,  # Wbudowany w Pythona
        "uuid": None,  # Wbudowany w Pythona
        "hashlib": None,  # Wbudowany w Pythona
        "base64": None,  # Wbudowany w Pythona
        "pickle": None,  # Wbudowany w Pythona
        "zipfile": None,  # Wbudowany w Pythona
        "tempfile": None,  # Wbudowany w Pythona
        "configparser": None,  # Wbudowany w Pythona
        "xml": None,  # Wbudowany w Pythona
        "html": None,  # Wbudowany w Pythona
        "csv": None,  # Wbudowany w Pythona
        "codecs": None,  # Wbudowany w Pythona
        "inspect": None,  # Wbudowany w Pythona
        "platform": None,  # Wbudowany w Pythona
    }

    # Sprawdzamy, czy mamy mapowanie dla tego modułu
    if module_name in module_to_package:
        return module_to_package[module_name]

    # Sprawdzamy, czy to podmoduł (np. requests.exceptions)
    parts = module_name.split('.')
    if parts[0] in module_to_package:
        return module_to_package[parts[0]]

    # Domyślnie zwracamy nazwę modułu jako nazwę pakietu
    return module_name

def solve_asyncio_error(self, error_message: str, script_content: str) -> Dict[str, Any]:
    """
    Analizuje i rozwiązuje problemy związane z asyncio.

    Args:
        error_message: Komunikat o błędzie.
        script_content: Zawartość skryptu.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    result = {
        "id": str(uuid.uuid4()),
        "title": "Problem z asyncio",
        "description": f"Wystąpił problem związany z asyncio: {error_message}",
        "solution": "Sprawdź poprawność używania asyncio w skrypcie.",
        "severity": "error",
        "category": "asyncio",
        "metadata": {
            "error_message": error_message
        }
    }

    # Problem 1: RuntimeError: asyncio.run() cannot be called from a running event loop
    if "asyncio.run() cannot be called from a running event loop" in error_message:
        result["title"] = "Próba wywołania asyncio.run() z działającej pętli zdarzeń"
        result["description"] = "Funkcja asyncio.run() nie może być wywołana z działającej pętli zdarzeń."
        result["solution"] = "Zamiast asyncio.run(), użyj await na funkcji asynchronicznej lub utwórz nową pętlę zdarzeń."

        # Proponowana poprawka
        fixed_code = script_content.replace("asyncio.run(", "await ")

        if fixed_code == script_content:
            # Jeśli powyższa zamiana nie zadziałała, próbujemy innego rozwiązania
            fixed_code = script_content.replace(
                "asyncio.run(main(args.host, args.port))",
                "loop = asyncio.get_event_loop()\nloop.run_until_complete(main(args.host, args.port))"
            )

        result["metadata"]["fixed_code"] = fixed_code

    # Problem 2: RuntimeWarning: coroutine 'function_name' was never awaited
    elif "was never awaited" in error_message:
        import re
        match = re.search(r"coroutine '([^']+)' was never awaited", error_message)

        if match:
            function_name = match.group(1)
            result["title"] = f"Coroutine '{function_name}' nigdy nie została awaited"
            result["description"] = f"Funkcja asynchroniczna '{function_#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash. Służy do diagnozowania problemów
w projektach i środowiskach uruchomieniowych.
"""

import os
import sys
import platform
import subprocess
import json
import uuid
import psutil
import yaml
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import check_dependencies
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Diagnostics:
    """
    Klasa diagnostyczna do identyfikowania i raportowania problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Diagnostics.
        """
        self.os_info = detect_os()
        self.package_manager = get_package_manager()
        self.git = GitRepo()

        # Ładujemy bazę danych rozwiązań
        self.solutions_db = self._load_solutions_db()

    def _load_solutions_db(self) -> Dict[str, Any]:
        """
        Ładuje bazę danych rozwiązań.

        Returns:
            Słownik z bazą danych rozwiązań.
        """
        solutions_db = {}

        try:
            # Ścieżka do katalogu z rozwiązaniami
            solutions_dir = os.path.join(os.path.dirname(__file__), "..", "data", "solutions")

            # Ładujemy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_file = os.path.join(solutions_dir, f"{os_type}.json")

            if os.path.isfile(os_specific_file):
                with open(os_specific_file, 'r') as f:
                    os_specific_solutions = json.load(f)
                solutions_db.update(os_specific_solutions)

            # Ładujemy wspólne rozwiązania
            common_file = os.path.join(solutions_dir, "common.json")
            if os.path.isfile(common_file):
                with open(common_file, 'r') as f:
                    common_solutions = json.load(f)
                solutions_db.update(common_solutions)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania bazy danych rozwiązań: {str(e)}")

        return solutions_db

    def run(self, path: str = ".", level: str = "basic") -> List[Dict[str, Any]]:
        """
        Uruchamia diagnostykę dla projektu.

        Args:
            path: Ścieżka do projektu.
            level: Poziom diagnostyki (basic, advanced, full).

        Returns:
            Lista zidentyfikowanych problemów.
        """
        # Normalizujemy ścieżkę
        path = os.path.abspath(path)
        logger.info(f"Uruchamianie diagnostyki dla katalogu: {path} (poziom: {level})")

        # Lista na znalezione problemy
        issues = []

        # Sprawdzamy, czy katalog istnieje
        if not os.path.isdir(path):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Katalog projektu nie istnieje",
                "description": f"Katalog {path} nie istnieje.",
                "solution": "Utwórz katalog projektu lub użyj poprawnej ścieżki.",
                "severity": "critical",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })
            return issues

        # Podstawowe sprawdzenia (dla wszystkich poziomów)
        issues.extend(self._check_filesystem(path))
        issues.extend(self._check_permissions(path))
        issues.extend(self._check_dependencies(path))

        # Zaawansowane sprawdzenia (dla poziomów advanced i full)
        if level in ["advanced", "full"]:
            issues.extend(self._check_configuration(path))
            issues.extend(self._check_repository(path))
            issues.extend(self._check_networking())

        # Pełne sprawdzenia (tylko dla poziomu full)
        if level == "full":
            issues.extend(self._check_system_resources())
            issues.extend(self._check_logs(path))
            issues.extend(self._check_database(path))

        # Sortujemy problemy według ważności
        severity_order = {
            "critical": 0,
            "error": 1,
            "warning": 2,
            "info": 3
        }

        issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 999))

        logger.info(f"Znaleziono {len(issues)} problemów.")
        return issues

    def _check_filesystem(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z systemem plików.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy podstawowe pliki i katalogi istnieją
        essential_files = [
            "infrash.yaml", "infrash.yml",
            ".infrash/config.yaml", ".infrash/config.yml",
            "requirements.txt", "pyproject.toml", "setup.py",
            "Dockerfile", "docker-compose.yml"
        ]

        file_exists = False
        for file in essential_files:
            if os.path.isfile(os.path.join(path, file)):
                file_exists = True
                break

        if not file_exists:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak plików konfiguracyjnych",
                "description": "Nie znaleziono żadnych plików konfiguracyjnych projektu.",
                "solution": "Zainicjalizuj projekt za pomocą 'infrash init'.",
                "severity": "warning",
                "category": "filesystem",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy jest wystarczająco dużo miejsca na dysku
        try:
            disk_usage = shutil.disk_usage(path)
            free_space_gb = disk_usage.free / (1024 ** 3)

            if free_space_gb < 1.0:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Mało miejsca na dysku",
                    "description": f"Na dysku pozostało tylko {free_space_gb:.2f} GB wolnego miejsca.",
                    "solution": "Zwolnij miejsce na dysku lub użyj innej partycji.",
                    "severity": "warning",
                    "category": "filesystem",
                    "metadata": {
                        "free_space_gb": free_space_gb
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania miejsca na dysku: {str(e)}")

        return issues

    def _check_permissions(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z uprawnieniami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy mamy uprawnienia do zapisu w katalogu projektu
        if not os.access(path, os.W_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do zapisu",
                "description": f"Brak uprawnień do zapisu w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # Sprawdzamy, czy mamy uprawnienia do wykonywania plików w katalogu projektu
        if not os.access(path, os.X_OK):
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak uprawnień do wykonywania",
                "description": f"Brak uprawnień do wykonywania plików w katalogu {path}.",
                "solution": "Zmień uprawnienia do katalogu lub użyj innej ścieżki.",
                "severity": "critical",
                "category": "permissions",
                "metadata": {
                    "path": path
                }
            })

        # W systemach Unix sprawdzamy właściciela i grupę
        if os.name == "posix":
            try:
                owner = os.stat(path).st_uid
                current_user = os.getuid()

                if owner != current_user:
                    import pwd
                    owner_name = pwd.getpwuid(owner).pw_name
                    current_user_name = pwd.getpwuid(current_user).pw_name

                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Katalog należy do innego użytkownika",
                        "description": f"Katalog {path} należy do użytkownika {owner_name}, a aktualny użytkownik to {current_user_name}.",
                        "solution": f"Zmień właściciela katalogu: sudo chown -R {current_user_name}:{current_user_name} {path}",
                        "severity": "warning",
                        "category": "permissions",
                        "metadata": {
                            "path": path,
                            "owner": owner_name,
                            "current_user": current_user_name
                        }
                    })
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania właściciela katalogu: {str(e)}")

        return issues

    def _check_dependencies(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z zależnościami.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy wszystkie zależności są zainstalowane
        missing_deps = check_dependencies(path)

        if missing_deps:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brakujące zależności",
                "description": f"Brakujące zależności: {', '.join(missing_deps)}",
                "solution": f"Zainstaluj brakujące zależności: infrash install",
                "severity": "error",
                "category": "dependencies",
                "metadata": {
                    "missing_dependencies": missing_deps
                }
            })

        # Sprawdzamy, czy Python jest w wymaganej wersji
        try:
            # Sprawdzamy, czy istnieje plik z informacją o wymaganej wersji Pythona
            required_version = None

            # Sprawdzamy plik pyproject.toml
            pyproject_path = os.path.join(path, "pyproject.toml")
            if os.path.isfile(pyproject_path):
                with open(pyproject_path, 'r') as f:
                    content = f.read()

                    # Szukamy wymaganej wersji Pythona
                    import re
                    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
                    if match:
                        required_version = match.group(1)

            # Jeśli znaleziono wymaganą wersję, sprawdzamy czy jest kompatybilna
            if required_version:
                import packaging.specifiers
                import packaging.version

                current_version = platform.python_version()
                specifier = packaging.specifiers.SpecifierSet(required_version)

                if not specifier.contains(current_version):
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Niekompatybilna wersja Pythona",
                        "description": f"Aktualna wersja Pythona ({current_version}) nie jest kompatybilna z wymaganą ({required_version}).",
                        "solution": "Zainstaluj kompatybilną wersję Pythona lub użyj wirtualnego środowiska.",
                        "severity": "error",
                        "category": "dependencies",
                        "metadata": {
                            "current_version": current_version,
                            "required_version": required_version
                        }
                    })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wersji Pythona: {str(e)}")

        return issues

    def _check_configuration(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z konfiguracją.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy istnieje plik konfiguracyjny
        config_paths = [
            os.path.join(path, "infrash.yaml"),
            os.path.join(path, "infrash.yml"),
            os.path.join(path, ".infrash", "config.yaml"),
            os.path.join(path, ".infrash", "config.yml")
        ]

        config_file = None
        for config_path in config_paths:
            if os.path.isfile(config_path):
                config_file = config_path
                break

        if not config_file:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak pliku konfiguracyjnego",
                "description": "Nie znaleziono pliku konfiguracyjnego infrash.",
                "solution": "Utwórz plik konfiguracyjny lub zainicjalizuj projekt: infrash init",
                "severity": "warning",
                "category": "configuration",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma pliku konfiguracyjnego

        # Sprawdzamy, czy plik konfiguracyjny jest poprawny
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Sprawdzamy, czy konfiguracja zawiera wymagane pola
            required_fields = ["environments"]

            for field in required_fields:
                if field not in config:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Brak wymaganego pola w konfiguracji",
                        "description": f"W pliku konfiguracyjnym brakuje wymaganego pola: {field}",
                        "solution": f"Dodaj pole {field} do pliku konfiguracyjnego.",
                        "severity": "error",
                        "category": "configuration",
                        "metadata": {
                            "config_file": config_file,
                            "missing_field": field
                        }
                    })

            # Sprawdzamy, czy przynajmniej jedno środowisko jest zdefiniowane
            if "environments" in config and not config["environments"]:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdefiniowanych środowisk",
                    "description": "W pliku konfiguracyjnym nie zdefiniowano żadnych środowisk.",
                    "solution": "Dodaj definicję przynajmniej jednego środowiska do pliku konfiguracyjnego.",
                    "severity": "error",
                    "category": "configuration",
                    "metadata": {
                        "config_file": config_file
                    }
                })

            # Sprawdzamy, czy dla każdego środowiska zdefiniowano polecenie startowe
            if "environments" in config:
                for env_name, env_config in config["environments"].items():
                    if not env_config.get("start_command"):
                        issues.append({
                            "id": str(uuid.uuid4()),
                            "title": f"Brak polecenia startowego dla środowiska {env_name}",
                            "description": f"W konfiguracji środowiska {env_name} nie zdefiniowano polecenia startowego.",
                            "solution": f"Dodaj pole start_command do konfiguracji środowiska {env_name}.",
                            "severity": "error",
                            "category": "configuration",
                            "metadata": {
                                "config_file": config_file,
                                "environment": env_name
                            }
                        })

        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Błąd podczas parsowania pliku konfiguracyjnego",
                "description": f"Wystąpił błąd podczas parsowania pliku konfiguracyjnego: {str(e)}",
                "solution": "Sprawdź składnię pliku konfiguracyjnego i upewnij się, że jest poprawnym plikiem YAML.",
                "severity": "critical",
                "category": "configuration",
                "metadata": {
                    "config_file": config_file,
                    "error": str(e)
                }
            })

        return issues

    def _check_repository(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z repozytorium git.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy katalog jest repozytorium git
        if not os.path.isdir(os.path.join(path, ".git")):
            # To nie jest błąd, ale dodajemy informację
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak repozytorium git",
                "description": "Katalog nie jest repozytorium git.",
                "solution": "Zainicjalizuj repozytorium git: git init",
                "severity": "info",
                "category": "repository",
                "metadata": {
                    "path": path
                }
            })
            return issues  # Nie ma sensu kontynuować, jeśli nie ma repozytorium

        try:
            # Sprawdzamy, czy repozytorium ma niezatwierdzone zmiany
            repo_status = self.git.get_status(path)

            if repo_status.get("dirty", False):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Niezatwierdzone zmiany w repozytorium",
                    "description": f"Repozytorium ma {repo_status.get('changes', 0)} niezatwierdzonych zmian.",
                    "solution": "Zatwierdź zmiany lub cofnij je: git commit lub git reset",
                    "severity": "warning",
                    "category": "repository",
                    "metadata": {
                        "path": path,
                        "changes": repo_status.get("changes", 0)
                    }
                })

            # Sprawdzamy, czy repozytorium ma skonfigurowane zdalne repozytorium
            remote_url = self.git.get_remote_url(path)

            if not remote_url:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak zdalnego repozytorium",
                    "description": "Repozytorium nie ma skonfigurowanego zdalnego repozytorium.",
                    "solution": "Dodaj zdalne repozytorium: git remote add origin <url>",
                    "severity": "info",
                    "category": "repository",
                    "metadata": {
                        "path": path
                    }
                })

            # Sprawdzamy, czy repozytorium jest aktualne
            is_behind = self.git.is_behind_remote(path)

            if is_behind:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Repozytorium nie jest aktualne",
                    "description": "Lokalne repozytorium jest nieaktualne w stosunku do zdalnego.",
                    "solution": "Zaktualizuj repozytorium: git pull",
                    "severity": "warning",
                    "category": "repository",
                    "metadata": {
                        "path": path,
                        "commits_behind": self.git.get_commits_behind(path)
                    }
                })

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania repozytorium: {str(e)}")

        return issues

    def _check_networking(self) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z siecią.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy połączenie z internetem
        try:
            # Próbujemy połączyć się z serwerem Google
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak połączenia z internetem",
                "description": f"Nie można nawiązać połączenia z internetem: {str(e)}",
                "solution": "Sprawdź połączenie sieciowe i ustawienia zapory.",
                "severity": "error",
                "category": "networking",
                "metadata": {
                    "error": str(e)
                }
            })

        # Sprawdzamy lokalną sieć
        try:
            # Pobieramy adres IP hosta
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)

            # Sprawdzamy, czy to nie jest adres loopback
            if ip.startswith("127."):
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Brak lokalnego adresu IP",
                    "description": f"Host ma tylko adres loopback: {ip}",
                    "solution": "Sprawdź połączenie sieciowe i ustawienia interfejsu.",
                    "severity": "warning",
                    "category": "networking",
                    "metadata": {
                        "hostname": hostname,
                        "ip": ip
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania lokalnego adresu IP: {str(e)}")

        # Sprawdzamy otwarte porty
        try:
            # Sprawdzamy popularne porty, które mogą być potrzebne
            common_ports = {
                80: "HTTP",
                443: "HTTPS",
                22: "SSH",
                5000: "Flask",
                8000: "Django/Web",
                8080: "Alternate HTTP"
            }

            # Sprawdzamy, czy porty są zajęte
            for port, service in common_ports.items():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()

                # Jeśli port jest otwarty (0 oznacza sukces), dodajemy informację
                if result == 0:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": f"Port {port} ({service}) jest już używany",
                        "description": f"Port {port}, który może być potrzebny dla serwisu {service}, jest już używany przez inny proces.",
                        "solution": f"Zmień port w konfiguracji lub zatrzymaj proces używający portu {port}.",
                        "severity": "info",
                        "category": "networking",
                        "metadata": {
                            "port": port,
                            "service": service
                        }
                    })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania portów: {str(e)}")

        return issues

    def _check_system_resources(self) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z zasobami systemowymi.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy użycie CPU
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent > 90:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Wysokie obciążenie CPU",
                    "description": f"Obciążenie CPU wynosi {cpu_percent}%, co może spowodować problemy z wydajnością.",
                    "solution": "Zamknij niepotrzebne procesy lub przełącz się na mocniejszą maszynę.",
                    "severity": "warning",
                    "category": "resources",
                    "metadata": {
                        "cpu_percent": cpu_percent
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania obciążenia CPU: {str(e)}")

        # Sprawdzamy użycie pamięci
        try:
            memory = psutil.virtual_memory()

            if memory.percent > 90:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Mało wolnej pamięci RAM",
                    "description": f"Wykorzystanie pamięci RAM wynosi {memory.percent}%, pozostało tylko {memory.available / (1024**2):.1f} MB wolnej pamięci.",
                    "solution": "Zamknij niepotrzebne procesy lub zwiększ ilość pamięci RAM.",
                    "severity": "warning",
                    "category": "resources",
                    "metadata": {
                        "memory_percent": memory.percent,
                        "memory_available_mb": memory.available / (1024**2)
                    }
                })
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania pamięci RAM: {str(e)}")

        return issues

    def _check_logs(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza logi w poszukiwaniu problemów.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Katalogi, w których mogą znajdować się logi
        log_dirs = [
            os.path.join(path, "logs"),
            os.path.join(path, "log"),
            os.path.join(path, ".logs"),
            os.path.join(path, ".infrash", "logs")
        ]

        # Słowa kluczowe, które mogą wskazywać na problemy
        error_keywords = [
            "error", "exception", "failed", "failure", "fatal", "panic", "critical"
        ]

        # Sprawdzamy każdy katalog z logami
        for log_dir in log_dirs:
            if not os.path.isdir(log_dir):
                continue

            # Szukamy plików logów
            log_files = []
            for root, _, files in os.walk(log_dir):
                for file in files:
                    if file.endswith(".log") or file.endswith(".txt"):
                        log_files.append(os.path.join(root, file))

            # Sprawdzamy każdy plik logów
            for log_file in log_files:
                try:
                    # Otwieramy plik i szukamy problemów
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # Czytamy ostatnie 100 linii (lub mniej, jeśli plik jest krótszy)
                        lines = f.readlines()[-100:]

                        # Szukamy linii z błędami
                        error_lines = []
                        for i, line in enumerate(lines):
                            if any(keyword in line.lower() for keyword in error_keywords):
                                error_lines.append((i, line.strip()))

                        # Jeśli znaleziono błędy, dodajemy problem
                        if error_lines:
                            # Wybieramy ostatni błąd
                            last_error = error_lines[-1][1]

                            issues.append({
                                "id": str(uuid.uuid4()),
                                "title": "Błędy w logach",
                                "description": f"Znaleziono {len(error_lines)} linii z błędami w pliku {os.path.basename(log_file)}. Ostatni błąd: {last_error[:100]}...",
                                "solution": "Sprawdź logi, aby zidentyfikować przyczynę błędów.",
                                "severity": "warning",
                                "category": "logs",
                                "metadata": {
                                    "log_file": log_file,
                                    "error_count": len(error_lines),
                                    "last_error": last_error
                                }
                            })
                except Exception as e:
                    logger.error(f"Błąd podczas sprawdzania pliku logu {log_file}: {str(e)}")

        return issues

    def _check_database(self, path: str) -> List[Dict[str, Any]]:
        """
        Sprawdza problemy związane z bazą danych.

        Args:
            path: Ścieżka do projektu.

        Returns:
            Lista zidentyfikowanych problemów.
        """
        issues = []

        # Sprawdzamy, czy projekt używa bazy danych
        db_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".db") or file.endswith(".sqlite") or file.endswith(".sqlite3"):
                    db_files.append(os.path.join(root, file))

        # Jeśli nie znaleziono plików bazy danych, kończymy
        if not db_files:
            return issues

        # Sprawdzamy każdy plik bazy danych
        for db_file in db_files:
            try:
                # Sprawdzamy, czy plik bazy danych jest dostępny do odczytu
                if not os.access(db_file, os.R_OK):
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Brak dostępu do bazy danych",
                        "description": f"Brak uprawnień do odczytu pliku bazy danych: {os.path.basename(db_file)}",
                        "solution": "Zmień uprawnienia do pliku bazy danych.",
                        "severity": "error",
                        "category": "database",
                        "metadata": {
                            "db_file": db_file
                        }
                    })
                    continue

                # Sprawdzamy, czy plik bazy danych jest uszkodzony
                import sqlite3
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Sprawdzamy, czy możemy wykonać prostą operację
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]

                if result != "ok":
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": "Uszkodzona baza danych",
                        "description": f"Plik bazy danych {os.path.basename(db_file)} jest uszkodzony: {result}",
                        "solution": "Przywróć bazę danych z kopii zapasowej lub napraw ją.",
                        "severity": "critical",
                        "category": "database",
                        "metadata": {
                            "db_file": db_file,
                            "integrity_check": result
                        }
                    })

                conn.close()
            except Exception as e:
                issues.append({
                    "id": str(uuid.uuid4()),
                    "title": "Problem z bazą danych",
                    "description": f"Wystąpił problem z bazą danych {os.path.basename(db_file)}: {str(e)}",
                    "solution": "Sprawdź plik bazy danych i upewnij się, że jest poprawny.",
                    "severity": "error",
                    "category": "database",
                    "metadata": {
                        "db_file": db_file,
                        "error": str(e)
                    }
                })

        return issues

    def _check_process_handling(self, path: str, script_path: str, command: str) -> Dict[str, Any]:
        """
        Analizuje błędy związane z uruchamianiem procesów i skryptów.

        Args:
            path: Ścieżka do projektu.
            script_path: Ścieżka do skryptu.
            command: Polecenie, które spowodowało błąd.

        Returns:
            Słownik z analizą problemu i rozwiązaniem.
        """
        # Podstawowy wynik
        result = {
            "id": str(uuid.uuid4()),
            "title": "Problem z uruchomieniem procesu",
            "description": f"Wystąpił problem podczas uruchamiania polecenia: {command}",
            "solution": "Sprawdź składnię polecenia i upewnij się, że wszystkie wymagane pakiety są zainstalowane.",
            "severity": "error",
            "category": "process",
            "metadata": {
                "command": command,
                "script_path": script_path
            }
        }

        try:
            # Wykonujemy polecenie z przechwyceniem wyjścia
            process = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=path,
                timeout=5  # Maksymalny czas wykonania
            )

            # Jeśli polecenie zakończyło się błędem, analizujemy wyjście
            if process.returncode != 0:
                stderr = process.stderr.strip()

                # Analizujemy różne typy błędów
                if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                    # Próbujemy znaleźć nazwę brakującego modułu
                    import re
                    match = re.search(r"No module named '([^']+)'", stderr)

                    if match:
                        module_name = match.group(1)
                        result["title"] = f"Brakujący moduł: {module_name}"
                        result["description"] = f"Nie można zaimportować modułu {module_name}."
                        result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"
                        result["metadata"]["missing_module"] = module_name

                elif "SyntaxError" in stderr:
                    result["title"] = "Błąd składni"
                    result["description"] = f"Skrypt zawiera błąd składni: {stderr}"
                    result["solution"] = "Popraw błąd składni w skrypcie."

                elif "PermissionError" in stderr:
                    result["title"] = "Błąd uprawnień"
                    result["description"] = f"Brak odpowiednich uprawnień: {stderr}"
                    result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

                elif "FileNotFoundError" in stderr:
                    # Próbujemy znaleźć nazwę brakującego pliku
                    import re
                    match = re.search(r"No such file or directory: '([^']+)'", stderr)

                    if match:
                        file_name = match.group(1)
                        result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
                        result["description"] = f"Nie można znaleźć pliku: {file_name}"
                        result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
                        result["metadata"]["missing_file"] = file_name

                else:
                    # Ogólny błąd
                    result["description"] = f"Polecenie zakończyło się błędem (kod {process.returncode}): {stderr}"

        except subprocess.TimeoutExpired:
            result["title"] = "Timeout podczas wykonywania polecenia"
            result["description"] = f"Polecenie nie zakończyło się w wyznaczonym czasie: {command}"
            result["solution"] = "Sprawdź, czy polecenie nie zawiesza się lub nie wymaga interakcji użytkownika."
            result["severity"] = "warning"

        except Exception as e:
            result["description"] = f"Wystąpił nieoczekiwany błąd podczas analizy polecenia: {str(e)}"

        return result

    def analyze_script_error(self, script_path: str, error_message: str) -> Dict[str, Any]:
        """
        Analizuje błąd wykonania skryptu Python.

        Args:
            script_path: Ścieżka do skryptu.
            error_message: Komunikat o błędzie.

        Returns:
            Słownik z analizą problemu i rozwiązaniem.
        """
        # Podstawowy wynik
        result = {
            "id": str(uuid.uuid4()),
            "title": "Błąd wykonania skryptu",
            "description": f"Wystąpił błąd podczas wykonywania skryptu {os.path.basename(script_path)}: {error_message}",
            "solution": "Debuguj skrypt, aby znaleźć przyczynę błędu.",
            "severity": "error",
            "category": "script",
            "metadata": {
                "script_path": script_path,
                "error_message": error_message
            }
        }

        # Analizujemy różne typy błędów
        if "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            # Próbujemy znaleźć nazwę brakującego modułu
            import re
            match = re.search(r"No module named '([^']+)'", error_message)

            if match:
                module_name = match.group(1)
                result["title"] = f"Brakujący moduł: {module_name}"
                result["description"] = f"Nie można zaimportować modułu {module_name}."

                # Szukamy odpowiedniego pakietu dla modułu
                package_name = self._find_package_for_module(module_name)

                if package_name:
                    result["solution"] = f"Zainstaluj brakujący moduł: pip install {package_name}"
                else:
                    result["solution"] = f"Zainstaluj brakujący moduł: pip install {module_name}"

                result["metadata"]["missing_module"] = module_name
                result["metadata"]["package_name"] = package_name

        elif "SyntaxError" in error_message:
            # Próbujemy znaleźć linię z błędem
            import re
            match = re.search(r"line (\d+)", error_message)

            if match:
                line_number = match.group(1)
                result["title"] = f"Błąd składni w linii {line_number}"
                result["description"] = f"Skrypt zawiera błąd składni w linii {line_number}: {error_message}"
                result["solution"] = f"Popraw błąd składni w linii {line_number} skryptu."
                result["metadata"]["line_number"] = line_number

        elif "PermissionError" in error_message:
            result["title"] = "Błąd uprawnień"
            result["description"] = f"Brak odpowiednich uprawnień: {error_message}"
            result["solution"] = "Zmień uprawnienia do plików lub uruchom z wyższymi uprawnieniami."

        elif "FileNotFoundError" in error_message:
            # Próbujemy znaleźć nazwę brakującego pliku
            import re
            match = re.search(r"No such file or directory: '([^']+)'", error_message)

            if match:
                file_name = match.group(1)
                result["title"] = f"Brakujący plik: {os.path.basename(file_name)}"
                result["description"] = f"Nie można znaleźć pliku: {file_name}"
                result["solution"] = f"Upewnij się, że plik {os.path.basename(file_name)} istnieje i ścieżka jest poprawna."
                result["metadata"]["missing_file"] = file_name

        elif "ConnectionRefusedError" in error_message or "ConnectionError" in error_message:
            result["title"] = "Błąd połączenia"
            result["description"] = f"Nie można nawiązać połączenia: {error_message}"
            result["solution"] = "Sprawdź, czy serwer jest uruchomiony i dostępny."
            result["category"] = "networking"

        elif "TimeoutError" in error_message:
            result["title"] = "Timeout połączenia"
            result["description"] = f"Upłynął limit czasu połączenia: {error_message}"
            result["solution"] = "Sprawdź, czy serwer jest dostępny i czy limit czasu jest wystarczający."
            result["category"] = "networking"

        return result