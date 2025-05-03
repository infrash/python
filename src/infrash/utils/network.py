#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł narzędzi sieciowych. Umożliwia sprawdzanie połączeń, diagnostykę
problemów sieciowych i wykonywanie zapytań HTTP.
"""

import os
import sys
import socket
import subprocess
import requests
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def check_internet_connection() -> bool:
    """
    Sprawdza połączenie z internetem.
    
    Returns:
        True, jeśli połączenie jest dostępne, False w przeciwnym razie.
    """
    try:
        # Próbujemy połączyć się z serwerem Google
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania połączenia z internetem: {str(e)}")
        return False

def check_port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """
    Sprawdza, czy port jest otwarty.
    
    Args:
        host: Adres hosta.
        port: Numer portu.
        timeout: Limit czasu w sekundach (opcjonalnie).
        
    Returns:
        True, jeśli port jest otwarty, False w przeciwnym razie.
    """
    try:
        # Tworzymy gniazdo
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        # Próbujemy połączyć się z hostem i portem
        result = sock.connect_ex((host, port))
        sock.close()

        return result == 0
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania portu {port} na hoście {host}: {str(e)}")
        return False

def ping_host(host: str, count: int = 4, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Pinguje hosta.
    
    Args:
        host: Adres hosta.
        count: Liczba pingów (opcjonalnie).
        timeout: Limit czasu w sekundach (opcjonalnie).
        
    Returns:
        Słownik z wynikami pingowania.
    """
    result = {
        "success": False,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "packet_loss": 100,
        "output": ""
    }

    try:
        # Przygotowujemy polecenie ping w zależności od systemu
        if os.name == "nt":  # Windows
            cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), host]
        else:  # Unix
            cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), host]

        # Wykonujemy polecenie
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Zapisujemy wynik
        result["output"] = process.stdout

        # Sprawdzamy kod wyjścia
        if process.returncode != 0:
            logger.error(f"Błąd podczas pingowania hosta {host}: {process.stderr}")
            return result

        # Przetwarzamy wynik
        if os.name == "nt":  # Windows
            # Przykład: Minimum = 20ms, Maximum = 21ms, Average = 20ms
            match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", process.stdout)
            if match:
                result["min_ms"] = int(match.group(1))
                result["max_ms"] = int(match.group(2))
                result["avg_ms"] = int(match.group(3))
                result["success"] = True

            # Przykład: Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
            match = re.search(r"Lost = \d+ \((\d+)% loss\)", process.stdout)
            if match:
                result["packet_loss"] = int(match.group(1))
        else:  # Unix
            # Przykład: min/avg/max/mdev = 20.123/21.456/22.789/1.234 ms
            match = re.search(r"min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", process.stdout)
            if match:
                result["min_ms"] = float(match.group(1))
                result["avg_ms"] = float(match.group(2))
                result["max_ms"] = float(match.group(3))
                result["success"] = True

            # Przykład: 4 packets transmitted, 4 received, 0% packet loss
            match = re.search(r"(\d+)% packet loss", process.stdout)
            if match:
                result["packet_loss"] = int(match.group(1))

        return result

    except Exception as e:
        logger.error(f"Błąd podczas pingowania hosta {host}: {str(e)}")
        result["output"] = str(e)
        return result

def check_dns_resolution(domain: str) -> Dict[str, Any]:
    """
    Sprawdza rozwiązywanie DNS dla domeny.
    
    Args:
        domain: Nazwa domeny.
        
    Returns:
        Słownik z wynikami rozwiązywania DNS.
    """
    result = {
        "success": False,
        "ip": None,
        "error": None
    }

    try:
        # Próbujemy rozwiązać domenę
        ip = socket.gethostbyname(domain)

        result["success"] = True
        result["ip"] = ip

        return result

    except Exception as e:
        logger.error(f"Błąd podczas rozwiązywania DNS dla domeny {domain}: {str(e)}")
        result["error"] = str(e)
        return result

def traceroute(host: str, max_hops: int = 30, timeout: float = 3.0) -> List[Dict[str, Any]]:
    """
    Wykonuje trasowanie do hosta.
    
    Args:
        host: Adres hosta.
        max_hops: Maksymalna liczba przeskoków (opcjonalnie).
        timeout: Limit czasu w sekundach (opcjonalnie).
        
    Returns:
        Lista słowników z wynikami trasowania.
    """