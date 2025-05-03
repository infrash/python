#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie zasobów systemowych.
"""

import uuid
import psutil
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_system_resources() -> List[Dict[str, Any]]:
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