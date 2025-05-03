#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - sprawdzanie sieci.
"""

import uuid
import socket
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def _check_networking() -> List[Dict[str, Any]]:
    """
    Sprawdza problemy związane z siecią.

    Returns:
        Lista zidentyfikowanych problemów.
    """
    issues = []

    # Sprawdzamy połączenie z internetem
    try:
        # Próbujemy połączyć się z serwerem Google
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