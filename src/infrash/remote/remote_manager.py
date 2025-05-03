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
from infrash.system.dependency import check_dependencies, install_dependencies
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
    
    def connect(self, hostname, username, password=None, key_filename=None, port=22, retry_count=3, retry_delay=5):
        """
        Nawiązuje połączenie SSH z hostem.

        Args:
            hostname: Adres hosta.
            username: Nazwa użytkownika.
            password: Hasło (opcjonalne).
            key_filename: Ścieżka do klucza SSH (opcjonalne).
            port: Port SSH (domyślnie 22).
            retry_count: Liczba prób połączenia.
            retry_delay: Opóźnienie między próbami w sekundach.

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
    
    def setup_environment(self, ssh_client, repo_url, branch=None, install_deps=True, resolve_deps=False, max_retries=3):
        """
        Konfiguruje środowisko na zdalnym hoście, w tym klonowanie repozytorium i instalację zależności.

        Args:
            ssh_client: Połączenie SSH do zdalnego hosta
            repo_url: URL repozytorium do sklonowania
            branch: Gałąź do sklonowania (opcjonalnie)
            install_deps: Czy instalować zależności
            resolve_deps: Czy automatycznie rozwiązywać konflikty wersji zależności
            max_retries: Maksymalna liczba prób dla operacji sieciowych

        Returns:
            bool: True, jeśli konfiguracja się powiodła, False w przeciwnym razie
        """
        try:
            # Aktualizacja systemu i instalacja podstawowych narzędzi
            logger.info("Aktualizacja systemu i instalacja podstawowych narzędzi...")
            success, stdout, stderr = self.run_command(
                ssh_client, 
                'sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv'
            )
            
            if not success:
                logger.error(f"Błąd podczas aktualizacji systemu: {stderr}")
                return False
            
            # Pobierz nazwę repozytorium z URL
            repo_name = repo_url.split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            
            # Sprawdź, czy repozytorium już istnieje
            success, stdout, stderr = self.run_command(ssh_client, f'ls -la ~/{repo_name}')
            
            if success:
                # Repozytorium już istnieje, aktualizuj je
                logger.info(f"Repozytorium {repo_name} już istnieje, aktualizowanie...")
                
                cmd = f'cd ~/{repo_name} && git pull'
                if branch:
                    cmd = f'cd ~/{repo_name} && git checkout {branch} && git pull'
                
                success, stdout, stderr = self.run_command(ssh_client, cmd)
                
                if not success:
                    logger.error(f"Błąd podczas aktualizacji repozytorium: {stderr}")
                    return False
            else:
                # Klonuj repozytorium
                logger.info(f"Klonowanie repozytorium {repo_url}...")
                
                cmd = f'git clone {repo_url} ~/{repo_name}'
                if branch:
                    cmd = f'git clone -b {branch} {repo_url} ~/{repo_name}'
                
                # Spróbuj kilka razy, w przypadku problemów z siecią
                for attempt in range(max_retries):
                    success, stdout, stderr = self.run_command(ssh_client, cmd)
                    
                    if success:
                        break
                    
                    logger.warning(f"Próba {attempt+1}/{max_retries} klonowania nie powiodła się: {stderr}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Zwiększaj czas oczekiwania z każdą próbą
                
                if not success:
                    logger.error(f"Nie udało się sklonować repozytorium po {max_retries} próbach")
                    return False
            
            # Inicjalizuj resolver zależności
            dependency_resolver = DependencyResolver(remote=True, ssh_client=ssh_client)
            
            # Aktualizuj pip
            logger.info("Aktualizacja pip...")
            dependency_resolver.update_pip()
            
            # Sprawdź i zainstaluj krytyczne zależności
            logger.info("Sprawdzanie krytycznych zależności...")
            if not dependency_resolver.ensure_critical_dependencies(max_retries=max_retries):
                logger.warning("Nie wszystkie krytyczne zależności zostały zainstalowane, ale kontynuujemy wdrażanie")
            
            # Sprawdź, czy istnieje plik requirements.txt
            success, stdout, stderr = self.run_command(
                ssh_client, 
                f'find ~/{repo_name} -name "requirements.txt" | head -1'
            )
            
            if success and stdout.strip():
                requirements_path = stdout.strip()
                logger.info(f"Znaleziono plik requirements.txt: {requirements_path}")
                
                if resolve_deps:
                    # Przetwórz plik requirements.txt, aby rozwiązać konflikty wersji
                    logger.info("Przetwarzanie pliku requirements.txt, aby rozwiązać konflikty wersji...")
                    success, processed_path = dependency_resolver.process_requirements_file(requirements_path)
                    
                    if success:
                        logger.info(f"Plik requirements.txt został przetworzony: {processed_path}")
                        requirements_path = processed_path
                    else:
                        logger.warning("Nie udało się przetworzyć pliku requirements.txt, używam oryginalnego pliku")
                
                # Instaluj zależności z obsługą ponownych prób
                if dependency_resolver.install_requirements_with_retry(
                    requirements_path, 
                    max_retries=max_retries
                ):
                    logger.info("Zależności zostały zainstalowane pomyślnie")
                else:
                    logger.warning("Wystąpiły problemy podczas instalacji zależności")
                    
                    # Spróbuj zainstalować pakiety jeden po drugim
                    logger.info("Próba instalacji pakietów jeden po drugim...")
                    if dependency_resolver.install_packages_one_by_one(requirements_path):
                        logger.info("Zależności zostały zainstalowane pojedynczo")
                    else:
                        logger.warning("Nie udało się zainstalować wszystkich zależności")
                        # Kontynuuj mimo problemów, niektóre pakiety mogły zostać zainstalowane
            else:
                logger.warning("Nie znaleziono pliku requirements.txt")
            
            logger.info("Konfiguracja środowiska zakończona pomyślnie")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji środowiska: {str(e)}")
            return False

    def deploy(self, hostname, username, password=None, key_filename=None, port=22, repo_url=None, 
               branch=None, install_deps=True, resolve_deps=False, max_retries=3):
        """
        Wdraża kod na zdalnym urządzeniu.

        Args:
            hostname: Adres hosta zdalnego
            username: Nazwa użytkownika do logowania
            password: Hasło do logowania (opcjonalnie)
            key_filename: Ścieżka do klucza SSH (opcjonalnie)
            port: Port SSH (domyślnie 22)
            repo_url: URL repozytorium do sklonowania (opcjonalnie)
            branch: Gałąź do sklonowania (opcjonalnie)
            install_deps: Czy instalować zależności
            resolve_deps: Czy automatycznie rozwiązywać konflikty wersji zależności
            max_retries: Liczba prób połączenia i operacji sieciowych

        Returns:
            bool: True, jeśli wdrożenie się powiodło, False w przeciwnym razie
        """
        try:
            # Nawiąż połączenie SSH z obsługą ponownych prób
            retry_delay = 5
            ssh_client = None
            
            for attempt in range(max_retries):
                try:
                    ssh_client = self.connect(
                        hostname, 
                        username, 
                        password=password, 
                        key_filename=key_filename,
                        port=port
                    )
                    break
                except Exception as e:
                    logger.warning(f"Próba {attempt+1}/{max_retries} połączenia nie powiodła się: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Zwiększaj czas oczekiwania z każdą próbą
            
            if not ssh_client:
                logger.error("Nie udało się nawiązać połączenia SSH po wielu próbach")
                return False
            
            try:
                # Skonfiguruj środowisko, jeśli podano URL repozytorium
                if repo_url:
                    if not self.setup_environment(
                        ssh_client, 
                        repo_url, 
                        branch=branch, 
                        install_deps=install_deps,
                        resolve_deps=resolve_deps,
                        max_retries=max_retries
                    ):
                        logger.error("Nie udało się skonfigurować środowiska")
                        ssh_client.close()
                        return False
                
                logger.info("Wdrożenie zakończone pomyślnie")
                return True
                
            finally:
                # Zamknij połączenie SSH
                ssh_client.close()
                
        except Exception as e:
            logger.error(f"Błąd podczas wdrażania: {str(e)}")
            return False

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

class DeploymentError(Exception):
    """
    Wyjątek zgłaszany, gdy wdrożenie się nie powiodło.
    """
    pass
