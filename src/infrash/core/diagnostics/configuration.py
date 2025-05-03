#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie konfiguracji.
"""

import os
import json
import yaml
import configparser
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_configuration(path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność plików konfiguracyjnych w projekcie.

    Args:
        path: Ścieżka do katalogu projektu.

    Returns:
        Lista zidentyfikowanych problemów z konfiguracją.
    """
    logger.info(f"Sprawdzanie plików konfiguracyjnych w: {path}")
    issues = []

    # Lista typowych plików konfiguracyjnych do sprawdzenia
    config_files = [
        {"pattern": "*.json", "parser": _check_json_file},
        {"pattern": "*.yaml", "parser": _check_yaml_file},
        {"pattern": "*.yml", "parser": _check_yaml_file},
        {"pattern": "*.ini", "parser": _check_ini_file},
        {"pattern": "*.conf", "parser": _check_ini_file},
        {"pattern": "*.toml", "parser": _check_toml_file},
        {"pattern": "*.env", "parser": _check_env_file},
    ]

    # Sprawdzamy każdy typ pliku konfiguracyjnego
    for config_type in config_files:
        pattern = config_type["pattern"]
        parser = config_type["parser"]
        
        # Znajdujemy pliki pasujące do wzorca
        for root, _, files in os.walk(path):
            for file in files:
                if Path(file).match(pattern):
                    file_path = os.path.join(root, file)
                    # Sprawdzamy plik
                    file_issues = parser(file_path)
                    if file_issues:
                        issues.extend(file_issues)

    return issues

def _check_json_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność pliku JSON.

    Args:
        file_path: Ścieżka do pliku JSON.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Błąd w pliku JSON: {os.path.basename(file_path)}",
            "description": f"Plik {file_path} zawiera nieprawidłowy format JSON: {str(e)}",
            "severity": "error",
            "solution": "Popraw format pliku JSON zgodnie z komunikatem błędu.",
            "file_path": file_path,
            "line": e.lineno,
            "column": e.colno
        })
    except Exception as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Problem z plikiem JSON: {os.path.basename(file_path)}",
            "description": f"Wystąpił problem podczas analizy pliku {file_path}: {str(e)}",
            "severity": "warning",
            "solution": "Sprawdź uprawnienia do pliku i jego zawartość.",
            "file_path": file_path
        })
    return issues

def _check_yaml_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność pliku YAML.

    Args:
        file_path: Ścieżka do pliku YAML.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Błąd w pliku YAML: {os.path.basename(file_path)}",
            "description": f"Plik {file_path} zawiera nieprawidłowy format YAML: {str(e)}",
            "severity": "error",
            "solution": "Popraw format pliku YAML zgodnie z komunikatem błędu.",
            "file_path": file_path
        })
    except Exception as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Problem z plikiem YAML: {os.path.basename(file_path)}",
            "description": f"Wystąpił problem podczas analizy pliku {file_path}: {str(e)}",
            "severity": "warning",
            "solution": "Sprawdź uprawnienia do pliku i jego zawartość.",
            "file_path": file_path
        })
    return issues

def _check_ini_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność pliku INI/CONF.

    Args:
        file_path: Ścieżka do pliku INI/CONF.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    try:
        config = configparser.ConfigParser()
        config.read(file_path)
    except configparser.Error as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Błąd w pliku INI/CONF: {os.path.basename(file_path)}",
            "description": f"Plik {file_path} zawiera nieprawidłowy format INI/CONF: {str(e)}",
            "severity": "error",
            "solution": "Popraw format pliku INI/CONF zgodnie z komunikatem błędu.",
            "file_path": file_path
        })
    except Exception as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Problem z plikiem INI/CONF: {os.path.basename(file_path)}",
            "description": f"Wystąpił problem podczas analizy pliku {file_path}: {str(e)}",
            "severity": "warning",
            "solution": "Sprawdź uprawnienia do pliku i jego zawartość.",
            "file_path": file_path
        })
    return issues

def _check_toml_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność pliku TOML.

    Args:
        file_path: Ścieżka do pliku TOML.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    try:
        # Próbujemy zaimportować moduł toml
        import tomli
        with open(file_path, 'rb') as f:
            tomli.load(f)
    except ImportError:
        # Jeśli nie ma modułu tomli, próbujemy z toml
        try:
            import toml
            with open(file_path, 'r', encoding='utf-8') as f:
                toml.load(f)
        except ImportError:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": "Brak modułu do parsowania TOML",
                "description": "Nie znaleziono modułu tomli ani toml do parsowania plików TOML.",
                "severity": "warning",
                "solution": "Zainstaluj moduł tomli lub toml: pip install tomli",
                "file_path": file_path
            })
            return issues
        except Exception as e:
            issues.append({
                "id": str(uuid.uuid4()),
                "title": f"Błąd w pliku TOML: {os.path.basename(file_path)}",
                "description": f"Plik {file_path} zawiera nieprawidłowy format TOML: {str(e)}",
                "severity": "error",
                "solution": "Popraw format pliku TOML zgodnie z komunikatem błędu.",
                "file_path": file_path
            })
    except Exception as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Problem z plikiem TOML: {os.path.basename(file_path)}",
            "description": f"Wystąpił problem podczas analizy pliku {file_path}: {str(e)}",
            "severity": "warning",
            "solution": "Sprawdź uprawnienia do pliku i jego zawartość.",
            "file_path": file_path
        })
    return issues

def _check_env_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Sprawdza poprawność pliku .env.

    Args:
        file_path: Ścieżka do pliku .env.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Pomijamy puste linie i komentarze
                if not line or line.startswith('#'):
                    continue
                
                # Sprawdzamy, czy linia ma format KEY=VALUE
                if '=' not in line:
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "title": f"Nieprawidłowy format w pliku .env: {os.path.basename(file_path)}",
                        "description": f"Linia {line_num} w pliku {file_path} nie ma formatu KEY=VALUE: '{line}'",
                        "severity": "warning",
                        "solution": "Popraw format pliku .env. Każda linia powinna mieć format KEY=VALUE.",
                        "file_path": file_path,
                        "line": line_num
                    })
    except Exception as e:
        issues.append({
            "id": str(uuid.uuid4()),
            "title": f"Problem z plikiem .env: {os.path.basename(file_path)}",
            "description": f"Wystąpił problem podczas analizy pliku {file_path}: {str(e)}",
            "severity": "warning",
            "solution": "Sprawdź uprawnienia do pliku i jego zawartość.",
            "file_path": file_path
        })
    return issues
