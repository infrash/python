"""
config.py

Moduł zawierający klasę konfiguracyjną dla pakietu infrash.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

class Config:
    """
    Klasa konfiguracyjna dla pakietu infrash.
    
    Przechowuje i zarządza ustawieniami konfiguracyjnymi dla całego pakietu.
    Umożliwia wczytywanie konfiguracji z pliku, zapisywanie zmian oraz
    dostęp do poszczególnych ustawień.
    """
    
    DEFAULT_CONFIG_PATH = os.path.expanduser("~/.infrash/config.json")
    DEFAULT_CONFIG = {
        "log_level": "INFO",
        "data_dir": os.path.expanduser("~/.infrash/data"),
        "cache_dir": os.path.expanduser("~/.infrash/cache"),
        "solutions_db": os.path.expanduser("~/.infrash/solutions.json"),
        "default_timeout": 60,
        "default_retries": 3,
        "package_managers": {
            "apt": {
                "enabled": True,
                "sudo_required": True
            },
            "yum": {
                "enabled": True,
                "sudo_required": True
            },
            "dnf": {
                "enabled": True,
                "sudo_required": True
            },
            "pacman": {
                "enabled": True,
                "sudo_required": True
            },
            "brew": {
                "enabled": True,
                "sudo_required": False
            },
            "pip": {
                "enabled": True,
                "sudo_required": False
            },
            "npm": {
                "enabled": True,
                "sudo_required": False
            }
        },
        "git": {
            "default_branch": "main",
            "clone_depth": 1
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicjalizuje nową instancję Config.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego (opcjonalne).
                         Jeśli nie podano, używana jest domyślna ścieżka.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
        
    def load(self) -> bool:
        """
        Wczytuje konfigurację z pliku.
        
        Returns:
            True, jeśli konfiguracja została wczytana pomyślnie, False w przeciwnym razie.
        """
        try:
            if os.path.isfile(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.debug(f"Konfiguracja wczytana z {self.config_path}")
                return True
            else:
                logger.debug(f"Plik konfiguracyjny {self.config_path} nie istnieje. Używam domyślnej konfiguracji.")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania konfiguracji: {str(e)}")
            return False
            
    def save(self) -> bool:
        """
        Zapisuje konfigurację do pliku.
        
        Returns:
            True, jeśli konfiguracja została zapisana pomyślnie, False w przeciwnym razie.
        """
        try:
            # Upewnij się, że katalog istnieje
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            
            logger.debug(f"Konfiguracja zapisana do {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {str(e)}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość ustawienia konfiguracyjnego.
        
        Args:
            key: Klucz ustawienia.
            default: Domyślna wartość, jeśli ustawienie nie istnieje.
            
        Returns:
            Wartość ustawienia lub wartość domyślna.
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Ustawia wartość ustawienia konfiguracyjnego.
        
        Args:
            key: Klucz ustawienia.
            value: Nowa wartość ustawienia.
        """
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def reset(self) -> None:
        """
        Resetuje konfigurację do wartości domyślnych.
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
    def __getitem__(self, key: str) -> Any:
        """
        Umożliwia dostęp do ustawień za pomocą operatora [].
        
        Args:
            key: Klucz ustawienia.
            
        Returns:
            Wartość ustawienia.
            
        Raises:
            KeyError: Jeśli ustawienie nie istnieje.
        """
        return self.get(key)
        
    def __setitem__(self, key: str, value: Any) -> None:
        """
        Umożliwia ustawianie wartości za pomocą operatora [].
        
        Args:
            key: Klucz ustawienia.
            value: Nowa wartość ustawienia.
        """
        self.set(key, value)
