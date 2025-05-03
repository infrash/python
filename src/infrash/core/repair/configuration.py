#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - naprawa problemów z konfiguracją.
"""

import os
import yaml
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

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
            import shutil
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