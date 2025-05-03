"""
repair.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash. Służy do naprawiania zidentyfikowanych problemów
w projektach i środowiskach uruchomieniowych.
"""

import os
import sys
import shutil
import subprocess
import platform
import re
import uuid
import json
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager
from infrash.system.dependency import install_dependency
from infrash.repo.git import GitRepo

# Inicjalizacja loggera
logger = get_logger(__name__)

class Repair:
    """
    Klasa naprawcza do rozwiązywania zidentyfikowanych problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Repair.
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

    def fix(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia zidentyfikowany problem.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        logger.info(f"Próba naprawy problemu: {issue.get('title', 'Nieznany problem')}")

        # Sprawdzamy, czy mamy dedykowaną metodę dla tej kategorii problemu
        category = issue.get("category", "unknown")
        method_name = f"_fix_{category}"

        if hasattr(self, method_name):
            try:
                method = getattr(self, method_name)
                return method(issue)
            except Exception as e:
                logger.error(f"Błąd podczas naprawy problemu ({category}): {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody, szukamy w bazie danych rozwiązań
        solution_id = issue.get("solution_id")
        if solution_id and solution_id in self.solutions_db:
            try:
                solution = self.solutions_db[solution_id]
                return self._apply_solution(solution, issue)
            except Exception as e:
                logger.error(f"Błąd podczas stosowania rozwiązania {solution_id}: {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody ani rozwiązania, zwracamy False
        logger.error(f"Brak metody naprawy dla problemu kategorii: {category}")
        return False

    def _apply_solution(self, solution: Dict[str, Any], issue: Dict[str, Any]) -> bool:
        """
        Stosuje rozwiązanie z bazy danych.

        Args:
            solution: Słownik opisujący rozwiązanie.
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli rozwiązanie zostało zastosowane pomyślnie, False w przeciwnym razie.
        """
        # Typ rozwiązania określa, jak je zastosować
        solution_type = solution.get("type", "unknown")

        if solution_type == "command":
            # Rozwiązanie polega na wykonaniu polecenia
            command = solution.get("command", "")

            # Zastępujemy zmienne w poleceniu
            command = self._replace_variables(command, issue)

            # Wykonujemy polecenie
            return self._run_command(command)

        elif solution_type == "file_modify":
            # Rozwiązanie polega na modyfikacji pliku
            file_path = solution.get("file_path", "")
            pattern = solution.get("pattern", "")
            replacement = solution.get("replacement", "")

            # Zastępujemy zmienne w ścieżce, wzorcu i zastępniku
            file_path = self._replace_variables(file_path, issue)
            pattern = self._replace_variables(pattern, issue)
            replacement = self._replace_variables(replacement, issue)

            # Modyfikujemy plik
            return self._modify_file(file_path, pattern, replacement)

        elif solution_type == "file_create":
            # Rozwiązanie polega na utworzeniu pliku
            file_path = solution.get("file_path", "")
            content = solution.get("content", "")

            # Zastępujemy zmienne w ścieżce i zawartości
            file_path = self._replace_variables(file_path, issue)
            content = self._replace_variables(content, issue)

            # Tworzymy plik
            return self._create_file(file_path, content)

        elif solution_type == "package_install":
            # Rozwiązanie polega na instalacji pakietu
            package_name = solution.get("package_name", "")
            package_manager = solution.get("package_manager", "")

            # Zastępujemy zmienne w nazwie pakietu i menedżerze pakietów
            package_name = self._replace_variables(package_name, issue)
            package_manager = self._replace_variables(package_manager, issue)

            # Instalujemy pakiet
            if not package_manager:
                package_manager = self.package_manager

            return self._install_package(package_name, package_manager)

        elif solution_type == "composite":
            # Rozwiązanie składa się z wielu rozwiązań
            sub_solutions = solution.get("solutions", [])

            # Stosujemy każde rozwiązanie
            success = True
            for sub_solution in sub_solutions:
                if not self._apply_solution(sub_solution, issue):
                    success = False

            return success

        else:
            logger.error(f"Nieznany typ rozwiązania: {solution_type}")
            return False

    def _replace_variables(self, text: str, issue: Dict[str, Any]) -> str:
        """
        Zastępuje zmienne w tekście.

        Args:
            text: Tekst z zmiennymi.
            issue: Słownik opisujący problem.

        Returns:
            Tekst z zastąpionymi zmiennymi.
        """
        # Zastępujemy zmienne w formacie ${nazwa_zmiennej}
        if not text:
            return text

        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})

        # Dodajemy podstawowe zmienne
        variables = {
            "os_name": self.os_info.get("name", "unknown"),
            "os_version": self.os_info.get("version", "unknown"),
            "os_type": self.os_info.get("type", "unknown"),
            "package_manager": self.package_manager,
            "python_version": platform.python_version(),
            "home_dir": os.path.expanduser("~"),
            "temp_dir": tempfile.gettempdir()
        }

        # Dodajemy zmienne z metadanych
        variables.update(metadata)

        # Zastępujemy zmienne
        for key, value in variables.items():
            text = text.replace(f"${{{key}}}", str(value))

        return text

    def _run_command(self, command: str) -> bool:
        """
        Wykonuje polecenie.

        Args:
            command: Polecenie do wykonania.

        Returns:
            True, jeśli polecenie zostało wykonane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Wykonywanie polecenia: {command}")

            # Wykonujemy polecenie
            process = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Polecenie zakończyło się błędem (kod {process.returncode}): {process.stderr}")
                return False

            logger.info(f"Polecenie wykonane pomyślnie.")
            return True

        except Exception as e:
            logger.info(f"Polecenie wykonane pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas wykonywania polecenia: {str(e)}")
            return False

    def _modify_file(self, file_path: str, pattern: str, replacement: str) -> bool:
        """
        Modyfikuje plik, zastępując wzorzec nowym tekstem.

        Args:
            file_path: Ścieżka do pliku.
            pattern: Wzorzec do zastąpienia (wyrażenie regularne).
            replacement: Tekst zastępujący.

        Returns:
            True, jeśli plik został zmodyfikowany pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Modyfikowanie pliku: {file_path}")

            # Sprawdzamy, czy plik istnieje
            if not os.path.isfile(file_path):
                logger.error(f"Plik nie istnieje: {file_path}")
                return False

            # Tworzymy kopię zapasową pliku
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)

            # Odczytujemy zawartość pliku
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Zastępujemy wzorzec
            new_content = re.sub(pattern, replacement, content)

            # Jeśli zawartość nie uległa zmianie, nie zapisujemy pliku
            if new_content == content:
                logger.warning(f"Plik nie został zmodyfikowany (wzorzec nie znaleziony): {file_path}")
                os.unlink(backup_path)  # Usuwamy kopię zapasową
                return False

            # Zapisujemy zmodyfikowaną zawartość
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info(f"Plik został zmodyfikowany pomyślnie: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas modyfikowania pliku: {str(e)}")

            # Przywracamy kopię zapasową, jeśli istnieje
            if 'backup_path' in locals() and os.path.isfile(backup_path):
                try:
                    shutil.copy2(backup_path, file_path)
                    logger.info(f"Przywrócono kopię zapasową pliku: {file_path}")
                except Exception as e2:
                    logger.error(f"Błąd podczas przywracania kopii zapasowej: {str(e2)}")

            return False

    def _create_file(self, file_path: str, content: str) -> bool:
        """
        Tworzy nowy plik z podaną zawartością.

        Args:
            file_path: Ścieżka do pliku.
            content: Zawartość pliku.

        Returns:
            True, jeśli plik został utworzony pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Tworzenie pliku: {file_path}")

            # Tworzymy katalog, jeśli nie istnieje
            directory = os.path.dirname(file_path)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)

            # Zapisujemy zawartość do pliku
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Plik został utworzony pomyślnie: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas tworzenia pliku: {str(e)}")
            return False

    def _install_package(self, package_name: str, package_manager: str = None) -> bool:
        """
        Instaluje pakiet za pomocą menedżera pakietów.

        Args:
            package_name: Nazwa pakietu.
            package_manager: Nazwa menedżera pakietów (opcjonalne).

        Returns:
            True, jeśli pakiet został zainstalowany pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Instalowanie pakietu: {package_name}")

            # Jeśli nie podano menedżera pakietów, używamy domyślnego
            if not package_manager:
                package_manager = self.package_manager

            # Instalujemy pakiet
            result = install_dependency(package_name, package_manager)

            if result:
                logger.info(f"Pakiet został zainstalowany pomyślnie: {package_name}")
                return True
            else:
                logger.error(f"Nie udało się zainstalować pakietu: {package_name}")
                return False

        except Exception as e:
            logger.error(f"Błąd podczas instalacji pakietu: {str(e)}")
            return False

    def _fix_filesystem(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z systemem plików.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak katalogu projektu
        if "Katalog projektu nie istnieje" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Tworzymy katalog
                os.makedirs(path, exist_ok=True)
                logger.info(f"Utworzono katalog projektu: {path}")
                return True
            except Exception as e:
                logger.error(f"Błąd podczas tworzenia katalogu: {str(e)}")
                return False

        # Problem 2: Brak plików konfiguracyjnych
        elif "Brak plików konfiguracyjnych" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Inicjalizujemy projekt
                from infrash.core.runner import init_project
                result = init_project(path)

                if result:
                    logger.info(f"Zainicjalizowano projekt w katalogu: {path}")
                    return True
                else:
                    logger.error(f"Nie udało się zainicjalizować projektu w katalogu: {path}")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas inicjalizacji projektu: {str(e)}")
                return False

        # Problem 3: Mało miejsca na dysku
        elif "Mało miejsca na dysku" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Mało miejsca na dysku' wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z systemem plików: {title}")
        return False

    def _fix_permissions(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z uprawnieniami.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak uprawnień do zapisu
        if "Brak uprawnień do zapisu" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Sprawdzamy, czy jesteśmy właścicielem pliku
                if os.name == "posix":
                    # W systemach Unix używamy chmod
                    cmd = f"chmod u+w {path}"
                    return self._run_command(cmd)
                else:
                    logger.warning(f"Brak metody naprawy uprawnień do zapisu dla systemu {os.name}.")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas naprawy uprawnień do zapisu: {str(e)}")
                return False

        # Problem 2: Brak uprawnień do wykonywania
        elif "Brak uprawnień do wykonywania" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Sprawdzamy, czy jesteśmy właścicielem pliku
                if os.name == "posix":
                    # W systemach Unix używamy chmod
                    cmd = f"chmod u+x {path}"
                    return self._run_command(cmd)
                else:
                    logger.warning(f"Brak metody naprawy uprawnień do wykonywania dla systemu {os.name}.")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas naprawy uprawnień do wykonywania: {str(e)}")
                return False

        # Problem 3: Katalog należy do innego użytkownika
        elif "Katalog należy do innego użytkownika" in title:
            path = metadata.get("path", "")
            current_user = metadata.get("current_user", "")

            if not path or not current_user:
                logger.error("Brak wymaganych metadanych problemu.")
                return False

            try:
                # Zmieniamy właściciela katalogu
                if os.name == "posix":
                    # W systemach Unix używamy chown
                    # Uwaga: wymaga uprawnień roota
                    cmd = f"sudo chown -R {current_user}:{current_user} {path}"
                    return self._run_command(cmd)
                else:
                    logger.warning(f"Brak metody naprawy właściciela katalogu dla systemu {os.name}.")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas naprawy właściciela katalogu: {str(e)}")
                return False

        # Nieznany problem
        logger.error(f"Nieznany problem z uprawnieniami: {title}")
        return False

    def _fix_dependencies(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z zależnościami.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brakujące zależności
        if "Brakujące zależności" in title:
            missing_dependencies = metadata.get("missing_dependencies", [])
            if not missing_dependencies:
                logger.error("Brak listy brakujących zależności w metadanych problemu.")
                return False

            try:
                # Instalujemy brakujące zależności
                success = True
                for dependency in missing_dependencies:
                    result = self._install_package(dependency)
                    if not result:
                        success = False

                return success
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
                return False

        # Problem 2: Niekompatybilna wersja Pythona
        elif "Niekompatybilna wersja Pythona" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Niekompatybilna wersja Pythona' wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z zależnościami: {title}")
        return False

    def _fix_configuration(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z konfiguracją.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak pliku konfiguracyjnego
        if "Brak pliku konfiguracyjnego" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Tworzymy domyślny plik konfiguracyjny
                config_dir = os.path.join(path, ".infrash")
                os.makedirs(config_dir, exist_ok=True)

                config_path = os.path.join(config_dir, "config.yaml")

                # Domyślna konfiguracja
                config_content = """# Konfiguracja infrash
name: default
auto_repair: true
diagnostic_level: basic
environments:
  development:
    start_command: python app.py
    stop_command: null
  production:
    start_command: gunicorn -w 4 app:app
    stop_command: null
"""

                # Zapisujemy konfigurację
                return self._create_file(config_path, config_content)
            except Exception as e:
                logger.error(f"Błąd podczas tworzenia pliku konfiguracyjnego: {str(e)}")
                return False

        # Problem 2: Błąd podczas parsowania pliku konfiguracyjnego
        elif "Błąd podczas parsowania pliku konfiguracyjnego" in title:
            config_file = metadata.get("config_file", "")
            if not config_file:
                logger.error("Brak ścieżki do pliku konfiguracyjnego w metadanych problemu.")
                return False

            try:
                # Tworzymy kopię zapasową pliku
                backup_path = f"{config_file}.backup"
                shutil.copy2(config_file, backup_path)

                # Tworzymy nowy plik konfiguracyjny
                config_content = """# Konfiguracja infrash
name: default
auto_repair: true
diagnostic_level: basic
environments:
  development:
    start_command: python app.py
    stop_command: null
  production:
    start_command: gunicorn -w 4 app:app
    stop_command: null
"""

                # Zapisujemy nową konfigurację
                result = self._create_file(config_file, config_content)

                if result:
                    logger.info(f"Utworzono nowy plik konfiguracyjny, kopia zapasowa: {backup_path}")

                return result
            except Exception as e:
                logger.error(f"Błąd podczas naprawy pliku konfiguracyjnego: {str(e)}")
                return False

        # Problem 3: Brak wymaganego pola w konfiguracji
        elif "Brak wymaganego pola w konfiguracji" in title:
            config_file = metadata.get("config_file", "")
            missing_field = metadata.get("missing_field", "")

            if not config_file or not missing_field:
                logger.error("Brak wymaganych metadanych problemu.")
                return False

            try:
                # Odczytujemy plik konfiguracyjny
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)

                # Domyślne wartości dla brakujących pól
                default_values = {
                    "environments": {
                        "development": {
                            "start_command": "python app.py",
                            "stop_command": None
                        },
                        "production": {
                            "start_command": "gunicorn -w 4 app:app",
                            "stop_command": None
                        }
                    },
                    "auto_repair": True,
                    "diagnostic_level": "basic",
                    "name": os.path.basename(os.path.dirname(config_file))
                }

                # Dodajemy brakujące pole
                if missing_field not in config:
                    config[missing_field] = default_values.get(missing_field, {})

                # Zapisujemy zaktualizowaną konfigurację
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                logger.info(f"Dodano brakujące pole '{missing_field}' do pliku konfiguracyjnego.")
                return True
            except Exception as e:
                logger.error(f"Błąd podczas dodawania brakującego pola: {str(e)}")
                return False

        # Problem 4: Brak zdefiniowanych środowisk
        elif "Brak zdefiniowanych środowisk" in title:
            config_file = metadata.get("config_file", "")
            if not config_file:
                logger.error("Brak ścieżki do pliku konfiguracyjnego w metadanych problemu.")
                return False

            try:
                # Odczytujemy plik konfiguracyjny
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)

                # Dodajemy domyślne środowiska
                config["environments"] = {
                    "development": {
                        "start_command": "python app.py",
                        "stop_command": None
                    },
                    "production": {
                        "start_command": "gunicorn -w 4 app:app",
                        "stop_command": None
                    }
                }

                # Zapisujemy zaktualizowaną konfigurację
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                logger.info(f"Dodano domyślne środowiska do pliku konfiguracyjnego.")
                return True
            except Exception as e:
                logger.error(f"Błąd podczas dodawania środowisk: {str(e)}")
                return False

        # Problem 5: Brak polecenia startowego dla środowiska
        elif "Brak polecenia startowego dla środowiska" in title:
            config_file = metadata.get("config_file", "")
            environment = metadata.get("environment", "")

            if not config_file or not environment:
                logger.error("Brak wymaganych metadanych problemu.")
                return False

            try:
                # Odczytujemy plik konfiguracyjny
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)

                # Dodajemy domyślne polecenie startowe dla środowiska
                if "environments" not in config:
                    config["environments"] = {}

                if environment not in config["environments"]:
                    config["environments"][environment] = {}

                # Domyślne polecenia startowe dla różnych środowisk
                default_start_commands = {
                    "development": "python app.py",
                    "production": "gunicorn -w 4 app:app",
                    "testing": "pytest",
                    "staging": "gunicorn -w 2 app:app"
                }

                config["environments"][environment]["start_command"] = default_start_commands.get(environment, "python app.py")

                # Zapisujemy zaktualizowaną konfigurację
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                logger.info(f"Dodano polecenie startowe dla środowiska '{environment}'.")
                return True
            except Exception as e:
                logger.error(f"Błąd podczas dodawania polecenia startowego: {str(e)}")
                return False

        # Nieznany problem
        logger.error(f"Nieznany problem z konfiguracją: {title}")
        return False

    def _fix_repository(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z repozytorium git.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak repozytorium git
        if "Brak repozytorium git" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Inicjalizujemy repozytorium git
                return self.git.init(path)
            except Exception as e:
                logger.error(f"Błąd podczas inicjalizacji repozytorium git: {str(e)}")
                return False

        # Problem 2: Niezatwierdzone zmiany w repozytorium
        elif "Niezatwierdzone zmiany w repozytorium" in title:
            # Tego problemu nie naprawiamy automatycznie
            logger.warning("Problem 'Niezatwierdzone zmiany w repozytorium' wymaga ręcznej interwencji.")
            return False

        # Problem 3: Brak zdalnego repozytorium
        elif "Brak zdalnego repozytorium" in title:
            # Tego problemu nie naprawiamy automatycznie
            logger.warning("Problem 'Brak zdalnego repozytorium' wymaga ręcznej interwencji.")
            return False

        # Problem 4: Repozytorium nie jest aktualne
        elif "Repozytorium nie jest aktualne" in title:
            path = metadata.get("path", "")
            if not path:
                logger.error("Brak ścieżki do katalogu w metadanych problemu.")
                return False

            try:
                # Aktualizujemy repozytorium
                return self.git.update(path)
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji repozytorium: {str(e)}")
                return False

        # Nieznany problem
        logger.error(f"Nieznany problem z repozytorium: {title}")
        return False

    def _fix_networking(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z siecią.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak połączenia z internetem
        if "Brak połączenia z internetem" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Brak połączenia z internetem' wymaga ręcznej interwencji.")
            return False

        # Problem 2: Brak lokalnego adresu IP
        elif "Brak lokalnego adresu IP" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Brak lokalnego adresu IP' wymaga ręcznej interwencji.")
            return False

        # Problem 3: Port jest już używany
        elif "jest już używany" in title:
            # Tego problemu nie naprawiamy automatycznie
            logger.warning("Problem z zajętym portem wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z siecią: {title}")
        return False

    def _fix_resources(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z zasobami systemowymi.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Wysokie obciążenie CPU
        if "Wysokie obciążenie CPU" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Wysokie obciążenie CPU' wymaga ręcznej interwencji.")
            return False

        # Problem 2: Mało wolnej pamięci RAM
        elif "Mało wolnej pamięci RAM" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Mało wolnej pamięci RAM' wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z zasobami: {title}")
        return False

    def _fix_logs(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z logami.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Błędy w logach
        if "Błędy w logach" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Błędy w logach' wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z logami: {title}")
        return False

    def _fix_database(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z bazą danych.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brak dostępu do bazy danych
        if "Brak dostępu do bazy danych" in title:
            db_file = metadata.get("db_file", "")
            if not db_file:
                logger.error("Brak ścieżki do pliku bazy danych w metadanych problemu.")
                return False

            try:
                # Zmieniamy uprawnienia do pliku bazy danych
                if os.name == "posix":
                    # W systemach Unix używamy chmod
                    cmd = f"chmod 644 {db_file}"
                    return self._run_command(cmd)
                else:
                    logger.warning(f"Brak metody naprawy uprawnień do pliku bazy danych dla systemu {os.name}.")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas naprawy uprawnień do pliku bazy danych: {str(e)}")
                return False

        # Problem 2: Uszkodzona baza danych
        elif "Uszkodzona baza danych" in title:
            # Tego problemu nie możemy naprawić automatycznie
            logger.warning("Problem 'Uszkodzona baza danych' wymaga ręcznej interwencji.")
            return False

        # Nieznany problem
        logger.error(f"Nieznany problem z bazą danych: {title}")
        return False

    def _fix_process(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia problemy związane z procesami.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})
        title = issue.get("title", "")

        # Problem 1: Brakujący moduł
        if "Brakujący moduł" in title:
            missing_module = metadata.get("missing_module", "")
            if not missing_module:
                logger.error("Brak nazwy brakującego modułu w metadanych problemu.")
                return False

            try:
                # Instalujemy brakujący moduł
                return self._install_package(missing_module)
            except Exception as e:
                logger.error(f"#!/usr/bin/env python3
                             # -*- coding: utf-8 -*-

                             """
                             Moduł naprawczy infrash. Służy do naprawiania zidentyfikowanych problemów
                             w projektach i środowiskach uruchomieniowych.
                             """

                import os
                import sys
                import shutil
                import subprocess
                import platform
                import re
                import uuid
                import json
                import tempfile
                from typing import Dict, List, Any, Optional, Union, Tuple
                from pathlib import Path

                from infrash.utils.logger import get_logger
                from infrash.system.os_detect import detect_os, get_package_manager
                from infrash.system.dependency import install_dependency
                from infrash.repo.git import GitRepo

                # Inicjalizacja loggera
                logger = get_logger(__name__)

class Repair:
    """
    Klasa naprawcza do rozwiązywania zidentyfikowanych problemów.
    """

    def __init__(self):
        """
        Inicjalizuje nową instancję Repair.
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

    def fix(self, issue: Dict[str, Any]) -> bool:
        """
        Naprawia zidentyfikowany problem.

        Args:
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli problem został naprawiony, False w przeciwnym razie.
        """
        logger.info(f"Próba naprawy problemu: {issue.get('title', 'Nieznany problem')}")

        # Sprawdzamy, czy mamy dedykowaną metodę dla tej kategorii problemu
        category = issue.get("category", "unknown")
        method_name = f"_fix_{category}"

        if hasattr(self, method_name):
            try:
                method = getattr(self, method_name)
                return method(issue)
            except Exception as e:
                logger.error(f"Błąd podczas naprawy problemu ({category}): {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody, szukamy w bazie danych rozwiązań
        solution_id = issue.get("solution_id")
        if solution_id and solution_id in self.solutions_db:
            try:
                solution = self.solutions_db[solution_id]
                return self._apply_solution(solution, issue)
            except Exception as e:
                logger.error(f"Błąd podczas stosowania rozwiązania {solution_id}: {str(e)}")
                return False

        # Jeśli nie mamy dedykowanej metody ani rozwiązania, zwracamy False
        logger.error(f"Brak metody naprawy dla problemu kategorii: {category}")
        return False

    def _apply_solution(self, solution: Dict[str, Any], issue: Dict[str, Any]) -> bool:
        """
        Stosuje rozwiązanie z bazy danych.

        Args:
            solution: Słownik opisujący rozwiązanie.
            issue: Słownik opisujący problem.

        Returns:
            True, jeśli rozwiązanie zostało zastosowane pomyślnie, False w przeciwnym razie.
        """
        # Typ rozwiązania określa, jak je zastosować
        solution_type = solution.get("type", "unknown")

        if solution_type == "command":
            # Rozwiązanie polega na wykonaniu polecenia
            command = solution.get("command", "")

            # Zastępujemy zmienne w poleceniu
            command = self._replace_variables(command, issue)

            # Wykonujemy polecenie
            return self._run_command(command)

        elif solution_type == "file_modify":
            # Rozwiązanie polega na modyfikacji pliku
            file_path = solution.get("file_path", "")
            pattern = solution.get("pattern", "")
            replacement = solution.get("replacement", "")

            # Zastępujemy zmienne w ścieżce, wzorcu i zastępniku
            file_path = self._replace_variables(file_path, issue)
            pattern = self._replace_variables(pattern, issue)
            replacement = self._replace_variables(replacement, issue)

            # Modyfikujemy plik
            return self._modify_file(file_path, pattern, replacement)

        elif solution_type == "file_create":
            # Rozwiązanie polega na utworzeniu pliku
            file_path = solution.get("file_path", "")
            content = solution.get("content", "")

            # Zastępujemy zmienne w ścieżce i zawartości
            file_path = self._replace_variables(file_path, issue)
            content = self._replace_variables(content, issue)

            # Tworzymy plik
            return self._create_file(file_path, content)

        elif solution_type == "package_install":
            # Rozwiązanie polega na instalacji pakietu
            package_name = solution.get("package_name", "")
            package_manager = solution.get("package_manager", "")

            # Zastępujemy zmienne w nazwie pakietu i menedżerze pakietów
            package_name = self._replace_variables(package_name, issue)
            package_manager = self._replace_variables(package_manager, issue)

            # Instalujemy pakiet
            if not package_manager:
                package_manager = self.package_manager

            return self._install_package(package_name, package_manager)

        elif solution_type == "composite":
            # Rozwiązanie składa się z wielu rozwiązań
            sub_solutions = solution.get("solutions", [])

            # Stosujemy każde rozwiązanie
            success = True
            for sub_solution in sub_solutions:
                if not self._apply_solution(sub_solution, issue):
                    success = False

            return success

        else:
            logger.error(f"Nieznany typ rozwiązania: {solution_type}")
            return False

    def _replace_variables(self, text: str, issue: Dict[str, Any]) -> str:
        """
        Zastępuje zmienne w tekście.

        Args:
            text: Tekst z zmiennymi.
            issue: Słownik opisujący problem.

        Returns:
            Tekst z zastąpionymi zmiennymi.
        """
        # Zastępujemy zmienne w formacie ${nazwa_zmiennej}
        if not text:
            return text

        # Pobieramy metadane z problemu
        metadata = issue.get("metadata", {})

        # Dodajemy podstawowe zmienne
        variables = {
            "os_name": self.os_info.get("name", "unknown"),
            "os_version": self.os_info.get("version", "unknown"),
            "os_type": self.os_info.get("type", "unknown"),
            "package_manager": self.package_manager,
            "python_version": platform.python_version(),
            "home_dir": os.path.expanduser("~"),
            "temp_dir": tempfile.gettempdir()
        }

        # Dodajemy zmienne z metadanych
        variables.update(metadata)

        # Zastępujemy zmienne
        for key, value in variables.items():
            text = text.replace(f"${{{key}}}", str(value))

        return text

    def _run_command(self, command: str) -> bool:
        """
        Wykonuje polecenie.

        Args:
            command: Polecenie do wykonania.

        Returns:
            True, jeśli polecenie zostało wykonane pomyślnie, False w przeciwnym razie.
        """
        try:
            logger.info(f"Wykonywanie polecenia: {command}")

            # Wykonujemy polecenie
            process = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Sprawdzamy kod wyjścia
            if process.returncode != 0:
                logger.error(f"Polecenie zakończyło się błędem (kod {process.returncode}): {process.stderr}")
                return False

            logger.info(f"Polecenie wykonane pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Bł