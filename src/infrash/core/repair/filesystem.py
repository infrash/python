#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - naprawa problemów z systemem plików.
"""

import os
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

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
    # Problem 3: Mało miejsca na dysku
    elif "Mało miejsca na dysku" in title:
        # Tego problemu nie możemy naprawić automatycznie
        logger.warning("Problem 'Mało miejsca na dysku' wymaga ręcznej interwencji.")
        return False

    # Nieznany problem
    logger.error(f"Nieznany problem z systemem plików: {title}")
    return False
