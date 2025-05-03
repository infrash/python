#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - naprawa problemów z uprawnieniami.
"""

import os
from typing import Dict, List, Any

from infrash.utils.logger import get_logger
from infrash.system.os_detect import is_admin

# Inicjalizacja loggera
logger = get_logger(__name__)

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