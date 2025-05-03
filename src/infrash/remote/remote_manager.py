#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł do zarządzania zdalnymi wdrożeniami i operacjami na urządzeniach.
"""

import os
import sys
import time
import logging
import paramiko
from pathlib import Path

from infrash.utils.logger import get_logger
from infrash.system.dependency_resolver import DependencyResolver

logger = get_logger(__name__)

class RemoteManager:
    """
    Klasa zarządzająca zdalnymi operacjami, wdrożeniami i konfiguracją.
    """
    
    def __init__(self):
        """Inicjalizacja menedżera zdalnych operacji."""
        self.ssh_clients = {}
        self.connected_hosts = set()
    
    def connect(self, hostname, username, password=None, key_filename=None, port=22):
        """
        Nawiązuje połączenie SSH z hostem.

        Args:
            hostname: Adres hosta.
            username: Nazwa użytkownika.
            password: Hasło (opcjonalne).
            key_filename: Ścieżka do klucza SSH (opcjonalne).
            port: Port SSH (domyślnie 22).

        Returns:
            Obiekt klienta SSH.
        """
        client_key = f"{username}@{hostname}:{port}"
        
        # Sprawdź, czy już mamy aktywne połączenie
        if client_key in self.ssh_clients:
            try:
                # Sprawdź, czy połączenie jest nadal aktywne
                self.ssh_clients[client_key].exec_command('echo "Testing connection"', timeout=5)
                logger.debug(f"Używam istniejącego połączenia SSH z {client_key}")
                return self.ssh_clients[client_key]
            except Exception:
                # Połączenie nie jest aktywne, usuń je
                logger.debug(f"Istniejące połączenie SSH z {client_key} nie jest aktywne, tworzę nowe")
                del self.ssh_clients[client_key]
        
        # Utwórz nowe połączenie
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Nawiąż połączenie
            if key_filename:
                ssh_client.connect(
                    hostname=hostname,
                    username=username,
                    key_filename=key_filename,
                    port=port
                )
            elif password:
                ssh_client.connect(
                    hostname=hostname,
                    username=username,
                    password=password,
                    port=port
                )
            else:
                # Próba połączenia z kluczem z ~/.ssh/id_rsa
                ssh_client.connect(
                    hostname=hostname,
                    username=username,
                    port=port
                )
            
            # Zapisz połączenie
            self.ssh_clients[client_key] = ssh_client
            return ssh_client
            
        except Exception as e:
            logger.error(f"Błąd podczas nawiązywania połączenia SSH z {client_key}: {str(e)}")
            raise
    
    def run_command(self, ssh_client, command, timeout=60):
        """
        Uruchamia polecenie na zdalnym hoście.
        
        Args:
            ssh_client: Połączony klient SSH
            command: Polecenie do uruchomienia
            timeout: Limit czasu wykonania w sekundach
            
        Returns:
            tuple: (bool, stdout, stderr) - Status wykonania, standardowe wyjście i błędy
        """
        try:
            logger.info(f"Uruchamianie polecenia: {command}")
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            
            if exit_status != 0:
                logger.error(f"Polecenie zakończone z kodem błędu {exit_status}: {stderr_str}")
                return False, stdout_str, stderr_str
            
            return True, stdout_str, stderr_str
            
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania polecenia: {str(e)}")
            return False, "", str(e)
    
    def setup_environment(self, ssh_client, repo_url, branch=None, install_deps=True):
        """
        Konfiguruje środowisko na hoście zdalnym.

        Args:
            ssh_client: Klient SSH.
            repo_url: URL repozytorium Git.
            branch: Gałąź repozytorium (opcjonalne).
            install_deps: Czy instalować zależności (domyślnie True).

        Returns:
            True, jeśli konfiguracja się powiodła, False w przeciwnym razie.
        """
        try:
            if not repo_url:
                logger.error("Nie podano URL repozytorium")
                return False
            
            # Pobierz nazwę repozytorium z URL
            repo_name = repo_url.split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            
            # Aktualizacja systemu i instalacja zależności
            logger.info("Aktualizacja systemu i instalacja zależności...")
            success, stdout, stderr = self.run_command(
                ssh_client,
                'sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv'
            )
            
            if not success:
                logger.warning(f"Błąd podczas aktualizacji systemu: {stderr}")
                # Kontynuuj mimo błędu, ponieważ niektóre pakiety mogą już być zainstalowane
            
            # Klonowanie repozytorium
            logger.info(f"Klonowanie repozytorium {repo_url}...")
            branch_option = f" -b {branch}" if branch else ""
            success, stdout, stderr = self.run_command(
                ssh_client,
                f'git clone{branch_option} {repo_url}'
            )
            
            if not success:
                if "already exists" in stderr:
                    # Repozytorium już istnieje, aktualizuj je
                    logger.info(f"Repozytorium {repo_name} już istnieje, aktualizowanie...")
                    target_branch = branch or "main"
                    success, stdout, stderr = self.run_command(
                        ssh_client,
                        f'cd {repo_name} && git fetch && git reset --hard origin/{target_branch}'
                    )
                    
                    if not success:
                        logger.error(f"Błąd podczas aktualizacji repozytorium: {stderr}")
                        return False
                else:
                    logger.error(f"Błąd podczas klonowania repozytorium: {stderr}")
                    return False
            
            # Konfiguracja środowiska Python
            if install_deps:
                logger.info("Konfiguracja środowiska Python...")
                
                # Sprawdź, czy istnieje plik requirements.txt
                success, stdout, stderr = self.run_command(
                    ssh_client,
                    f'cd {repo_name} && [ -f requirements.txt ] && echo "Requirements found" || echo "No requirements"'
                )
                
                has_requirements = "Requirements found" in stdout
                
                # Tworzenie wirtualnego środowiska
                logger.info("Tworzenie wirtualnego środowiska...")
                success, stdout, stderr = self.run_command(
                    ssh_client,
                    f'cd {repo_name} && python3 -m venv venv'
                )
                
                if not success:
                    logger.error(f"Błąd podczas tworzenia wirtualnego środowiska: {stderr}")
                    return False
                
                if has_requirements:
                    # Lokalizacja pliku requirements.txt
                    req_file_path = f"{repo_name}/requirements.txt"
                    
                    # Sprawdź, czy plik requirements.txt istnieje w podanej ścieżce
                    success, stdout, stderr = self.run_command(
                        ssh_client,
                        f'ls {req_file_path}'
                    )
                    
                    if not success:
                        # Szukaj pliku requirements.txt w całym repozytorium
                        logger.info("Szukanie pliku requirements.txt w repozytorium...")
                        success, stdout, stderr = self.run_command(
                            ssh_client,
                            f'find {repo_name} -name "requirements.txt" -type f'
                        )
                        
                        if success and stdout.strip():
                            req_file_path = stdout.strip().split('\n')[0]
                            logger.info(f"Znaleziono plik requirements.txt: {req_file_path}")
                        else:
                            logger.warning("Nie znaleziono pliku requirements.txt w repozytorium")
                            return True  # Kontynuuj mimo braku pliku requirements.txt
                    
                    # Przetwarzanie i instalacja zależności Python
                    logger.info("Przetwarzanie i instalacja zależności Python...")
                    
                    # Instalacja zależności z obsługą ponownych prób
                    max_retries = 3
                    retry_delay = 5
                    
                    for attempt in range(max_retries):
                        try:
                            success, stdout, stderr = self.run_command(
                                ssh_client,
                                f'cd {repo_name} && source venv/bin/activate && '
                                f'pip install --upgrade pip && '
                                f'pip install -r {req_file_path}'
                            )
                            
                            if success:
                                logger.info("Zależności Python zostały zainstalowane pomyślnie")
                                break
                            else:
                                logger.error(f"Błąd podczas instalacji zależności Python (próba {attempt+1}/{max_retries}): {stderr}")
                                
                                # Jeśli to ostatnia próba, spróbuj alternatywnych podejść
                                if attempt == max_retries - 1:
                                    # Próba instalacji z pominięciem problematycznych pakietów
                                    logger.info("Próba instalacji z pominięciem problematycznych pakietów...")
                                    success, stdout, stderr = self.run_command(
                                        ssh_client,
                                        f'cd {repo_name} && source venv/bin/activate && '
                                        f'pip install --no-deps -r {req_file_path}'
                                    )
                                    
                                    if not success:
                                        logger.error(f"Nie udało się zainstalować zależności Python: {stderr}")
                                        
                                        # Ostatnia próba - instalacja pakietów jeden po drugim
                                        logger.info("Próba instalacji pakietów jeden po drugim...")
                                        success, stdout, stderr = self.run_command(
                                            ssh_client,
                                            f'cat {req_file_path}'
                                        )
                                        
                                        if success:
                                            packages = []
                                            for line in stdout.split('\n'):
                                                line = line.strip()
                                                if line and not line.startswith('#'):
                                                    packages.append(line)
                                            
                                            if packages:
                                                logger.info(f"Instalacja {len(packages)} pakietów jeden po drugim...")
                                                for package in packages:
                                                    success, stdout, stderr = self.run_command(
                                                        ssh_client,
                                                        f'cd {repo_name} && source venv/bin/activate && '
                                                        f'pip install {package} || pip install --no-deps {package}'
                                                    )
                                                    if success:
                                                        logger.info(f"Zainstalowano pakiet {package}")
                                                    else:
                                                        logger.warning(f"Nie udało się zainstalować pakietu {package}: {stderr}")
                                        else:
                                            logger.error(f"Nie udało się odczytać pliku requirements.txt: {stderr}")
                        except Exception as e:
                            logger.error(f"Błąd podczas instalacji zależności Python (próba {attempt+1}/{max_retries}): {str(e)}")
                        
                        # Jeśli to nie ostatnia próba, poczekaj przed kolejną
                        if attempt < max_retries - 1:
                            logger.info(f"Ponowna próba za {retry_delay} sekund...")
                            time.sleep(retry_delay)
            
            logger.info("Środowisko zostało pomyślnie skonfigurowane")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji środowiska: {str(e)}")
            return False
    
    def deploy(self, hostname, username, password=None, key_filename=None, port=22, 
               repo_url=None, branch=None, install_deps=True, max_retries=3):
        """
        Wdraża projekt na zdalnym hoście.
        
        Args:
            hostname: Adres IP lub nazwa hosta
            username: Nazwa użytkownika SSH
            password: Hasło SSH (opcjonalne jeśli używasz klucza)
            key_filename: Ścieżka do pliku klucza prywatnego SSH (opcjonalne)
            port: Port SSH (domyślnie: 22)
            repo_url: URL repozytorium Git do wdrożenia
            branch: Gałąź do sklonowania (opcjonalne)
            install_deps: Czy instalować zależności systemowe
            max_retries: Maksymalna liczba prób połączenia
            
        Returns:
            bool: Status powodzenia operacji
        """
        try:
            # Nawiąż połączenie z hostem z obsługą ponownych prób
            ssh_client = None
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Łączenie z {hostname} jako {username} (próba {attempt+1}/{max_retries})...")
                    ssh_client = self.connect(hostname, username, password, key_filename, port)
                    logger.info(f"Połączenie SSH z {hostname} nawiązane pomyślnie")
                    break
                except Exception as e:
                    logger.error(f"Błąd podczas łączenia z {hostname} (próba {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Ponowna próba za 5 sekund...")
                        time.sleep(5)
                    else:
                        raise
            
            if ssh_client is None:
                logger.error(f"Nie udało się nawiązać połączenia SSH z {hostname} po {max_retries} próbach")
                raise Exception(f"Nie można połączyć się z {hostname}")
            
            # Aktualizacja pip na zdalnym urządzeniu
            logger.info("Aktualizacja pip na zdalnym urządzeniu...")
            success, stdout, stderr = self.run_command(
                ssh_client,
                f'python3 -m pip install --upgrade pip'
            )
            
            if success:
                logger.info("Pip został zaktualizowany na zdalnym urządzeniu.")
            else:
                logger.warning(f"Nie udało się zaktualizować pip: {stderr}")
            
            # Konfiguracja środowiska
            success = self.setup_environment(ssh_client, repo_url, branch, install_deps)
            
            if not success:
                logger.error("Wdrożenie nie powiodło się")
                ssh_client.close()
                raise Exception("Nie udało się skonfigurować środowiska")
            
            logger.info("Wdrożenie zakończone pomyślnie")
            ssh_client.close()
            return True
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Błąd podczas wdrażania: {error_message}")
            
            # Analiza błędu i sugestie rozwiązania
            suggestion = self._analyze_error(error_message, hostname)
            
            # Zwracamy False, aby wskazać, że wdrożenie się nie powiodło
            raise DeploymentError(f"Nie udało się wdrożyć projektu na hoście {hostname}.\n{suggestion}")
    
    def _analyze_error(self, error_message, host):
        """
        Analizuje błąd i zwraca sugestię rozwiązania.
        
        Args:
            error_message: Komunikat błędu.
            host: Adres hosta zdalnego.
            
        Returns:
            Sugestia rozwiązania problemu.
        """
        if "Connection refused" in error_message or "timed out" in error_message or "No route to host" in error_message:
            return f"Problem z połączeniem sieciowym: Nie można połączyć się z {host}.\nSugestia: Sprawdź swoje połączenie internetowe i ustawienia zapory sieciowej."
        elif "Authentication failed" in error_message:
            return "Problem z uwierzytelnianiem: Niepoprawne dane logowania.\nSugestia: Sprawdź nazwę użytkownika, hasło lub klucz SSH."
        elif "Permission denied" in error_message:
            return "Problem z uprawnieniami: Brak wymaganych uprawnień.\nSugestia: Sprawdź uprawnienia użytkownika na zdalnym hoście."
        elif "No space left on device" in error_message:
            return "Problem z przestrzenią dyskową: Brak miejsca na dysku.\nSugestia: Zwolnij miejsce na zdalnym hoście."
        elif "Could not resolve hostname" in error_message:
            return f"Problem z rozwiązywaniem nazw: Nie można rozwiązać nazwy hosta {host}.\nSugestia: Sprawdź poprawność nazwy hosta lub użyj adresu IP."
        else:
            return f"Nieznany problem: {error_message}\nSugestia: Sprawdź logi dla szczegółowych informacji."

class DeploymentError(Exception):
    """
    Wyjątek zgłaszany, gdy wdrożenie się nie powiodło.
    """
    pass

    def close_connections(self):
        """Zamyka wszystkie aktywne połączenia SSH."""
        for client_key, ssh_client in self.ssh_clients.items():
            try:
                ssh_client.close()
                logger.info(f"Zamknięto połączenie {client_key}")
            except Exception as e:
                logger.error(f"Błąd podczas zamykania połączenia {client_key}: {str(e)}")
        
        self.ssh_clients.clear()
        self.connected_hosts.clear()
