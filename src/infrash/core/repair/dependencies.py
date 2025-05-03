#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - naprawa problemów z zależnościami.
"""

from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

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