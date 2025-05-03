#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - rozwiązywanie problemów z połączeniami.
"""

import os
import uuid
import socket
import subprocess
import platform
from typing import Dict, List, Any

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

def fix_connection_issues(error_message: str, host: str, port: int) -> Dict[str, Any]:
    """
    Analizuje i rozwiązuje problemy z połączeniem.

    Args:
        error_message: Komunikat o błędzie.
        host: Adres hosta.
        port: Numer portu.

    Returns:
        Słownik z analizą problemu i rozwiązaniem.
    """
    result = {
        "id": str(uuid.uuid4()),
        "title": "Problem z połączeniem",
        "description": f"Wystąpił problem z połączeniem do {host}:{port}: {error_message}",
        "solution": "Sprawdź, czy serwer jest uruchomiony i czy port jest dostępny.",
        "severity": "error",
        "category": "networking",
        "metadata": {
            "error_message": error_message,
            "host": host,
            "port": port
        }
    }

    # Problem 1: ConnectionRefusedError
    if "ConnectionRefusedError" in error_message:
        result["title"] = "Połączenie odrzucone"
        result["description"] = f"Serwer na {host}:{port} odrzucił połączenie."

        # Sprawdzamy, czy host jest adresem lokalnym
        local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if host in local_hosts:
            # Sprawdzamy, czy port jest używany przez inny proces
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result_code = sock.connect_ex((host, port))
                sock.close()

                if result_code == 0:
                    # Port jest już używany
                    result["description"] = f"Port {port} jest już używany przez inny proces."
                    result["solution"] = f"Użyj innego portu lub zatrzymaj proces używający portu {port}."
                else:
                    # Port nie jest używany - prawdopodobnie serwer nie jest uruchomiony
                    result["solution"] = f"Uruchom serwer na porcie {port} lub sprawdź konfigurację zapory."
            except Exception:
                pass
        else:
            # Host zdalny - sprawdzamy dostępność
            try:
                # Sprawdzamy, czy host jest dostępny
                socket.gethostbyname(host)
                result["solution"] = f"Sprawdź, czy serwer na {host} jest uruchomiony i nasłuchuje na porcie {port}."
            except socket.gaierror:
                result["title"] = "Nie można rozwiązać nazwy hosta"
                result["description"] = f"Nie można rozwiązać nazwy hosta: {host}"
                result["solution"] = "Sprawdź, czy nazwa hosta jest poprawna i czy masz połączenie z internetem."

    # Problem 2: TimeoutError
    elif "TimeoutError" in error_message:
        result["title"] = "Timeout połączenia"
        result["description"] = f"Upłynął limit czasu podczas łączenia się z {host}:{port}."

        # Sprawdzamy, czy host jest dostępny
        try:
            socket.gethostbyname(host)
            result["solution"] = f"Sprawdź, czy host {host} jest dostępny w sieci i czy zapora nie blokuje połączeń na porcie {port}."
        except socket.gaierror:
            result["title"] = "Nie można rozwiązać nazwy hosta"
            result["description"] = f"Nie można rozwiązać nazwy hosta: {host}"
            result["solution"] = "Sprawdź, czy nazwa hosta jest poprawna i czy masz połączenie z internetem."

    # Problem 3: AddressBindingError (możliwe, że próbujemy nasłuchiwać na adresie, który jest już używany)
    elif "Address already in use" in error_message:
        result["title"] = "Adres już w użyciu"
        result["description"] = f"Adres {host}:{port} jest już używany przez inny proces."
        result["solution"] = f"Użyj innego portu lub zatrzymaj proces używający portu {port}."

        # Próbujemy znaleźć proces używający portu
        try:
            if os.name == "posix":
                # W systemach Unix używamy lsof
                process = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process.returncode == 0:
                    output = process.stdout.strip()
                    lines = output.split('\n')
                    if len(lines) > 1:
                        # Pierwsza linia to nagłówek, druga to dane procesu
                        process_info = lines[1].split()
                        if len(process_info) > 1:
                            process_name = process_info[0]
                            process_pid = process_info[1]
                            result["solution"] = f"Zatrzymaj proces {process_name} (PID: {process_pid}) używający portu {port} lub użyj innego portu."
                            result["metadata"]["process_name"] = process_name
                            result["metadata"]["process_pid"] = process_pid

            elif os.name == "nt":
                # W systemach Windows używamy netstat
                process = subprocess.run(
                    ["netstat", "-ano", "|", "findstr", f":{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    shell=True
                )

                if process.returncode == 0:
                    output = process.stdout.strip()
                    lines = output.split('\n')
                    if lines:
                        # Szukamy linii z naszym portem
                        for line in lines:
                            if f":{port}" in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    process_pid = parts[4]
                                    result["solution"] = f"Zatrzymaj proces o PID {process_pid} używający portu {port} lub użyj innego portu."
                                    result["metadata"]["process_pid"] = process_pid
                                break
        except Exception:
            pass

    # Problem 4: Permission denied (gdy próbujemy nasłuchiwać na porcie < 1024 bez uprawnień roota)
    elif "Permission denied" in error_message and port < 1024:
        result["title"] = "Brak uprawnień do nasłuchiwania na porcie"
        result["description"] = f"Brak uprawnień do nasłuchiwania na porcie {port}. Porty poniżej 1024 wymagają uprawnień administratora."
        result["solution"] = f"Użyj portu powyżej 1024 lub uruchom program z uprawnieniami administratora."

    return result