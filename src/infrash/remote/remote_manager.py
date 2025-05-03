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
        Nawiązuje połączenie SSH z hostem zdalnym.
        
        Args:
            hostname: Adres IP lub nazwa hosta
            username: Nazwa użytkownika SSH
            password: Hasło SSH (opcjonalne jeśli używasz klucza)
            key_filename: Ścieżka do pliku klucza prywatnego SSH (opcjonalne)
            port: Port SSH (domyślnie: 22)
            
        Returns:
            tuple: (bool, SSHClient or None) - Status połączenia i klient SSH lub None
        """
        try:
            logger.info(f"Łączenie z {hostname} jako {username}...")
            
            # Sprawdź, czy już mamy połączenie z tym hostem
            client_key = f"{username}@{hostname}:{port}"
            if client_key in self.ssh_clients:
                # Sprawdź, czy połączenie jest nadal aktywne
                try:
                    self.ssh_clients[client_key].exec_command('echo "Testing connection"')
                    logger.info(f"Używanie istniejącego połączenia z {hostname}")
                    return True, self.ssh_clients[client_key]
                except Exception:
                    # Połączenie nieaktywne, zamknij je i utwórz nowe
                    logger.info(f"Istniejące połączenie z {hostname} nieaktywne, tworzenie nowego...")
                    try:
                        self.ssh_clients[client_key].close()
                    except Exception:
                        pass
            
            # Utwórz nowe połączenie
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh_client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=10
            )
            
            # Zapisz klienta do słownika
            self.ssh_clients[client_key] = ssh_client
            self.connected_hosts.add(hostname)
            
            logger.info(f"Połączenie SSH z {hostname} nawiązane pomyślnie")
            return True, ssh_client
            
        except paramiko.AuthenticationException:
            logger.error(f"Błąd uwierzytelniania podczas łączenia z {hostname}")
            return False, None
        except paramiko.SSHException as e:
            logger.error(f"Błąd SSH podczas łączenia z {hostname}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas łączenia z {hostname}: {str(e)}")
            return False, None
    
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
        Konfiguruje środowisko na zdalnym hoście i instaluje projekt.
        
        Args:
            ssh_client: Połączony klient SSH
            repo_url: URL repozytorium Git do zainstalowania
            branch: Gałąź do sklonowania (opcjonalne)
            install_deps: Czy instalować zależności systemowe
            
        Returns:
            bool: Status powodzenia operacji
        """
        try:
            # Aktualizacja systemu i instalacja zależności
            if install_deps:
                logger.info("Aktualizacja systemu i instalacja zależności...")
                success, stdout, stderr = self.run_command(
                    ssh_client, 
                    'sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv'
                )
                
                if not success:
                    logger.error(f"Błąd podczas instalacji zależności: {stderr}")
                    return False
            
            # Klonowanie repozytorium
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            logger.info(f"Klonowanie repozytorium {repo_url}...")
            
            clone_cmd = f'git clone {repo_url}'
            if branch:
                clone_cmd += f' -b {branch}'
            
            success, stdout, stderr = self.run_command(ssh_client, clone_cmd)
            
            if not success:
                # Sprawdź, czy katalog już istnieje
                if "already exists" in stderr:
                    logger.info(f"Repozytorium {repo_name} już istnieje, aktualizowanie...")
                    
                    # Aktualizuj istniejące repozytorium
                    update_cmd = f'cd {repo_name} && git fetch && git reset --hard'
                    if branch:
                        update_cmd += f' origin/{branch}'
                    else:
                        update_cmd += ' origin/main'
                    
                    success, stdout, stderr = self.run_command(ssh_client, update_cmd)
                    if not success:
                        logger.error(f"Błąd podczas aktualizacji repozytorium: {stderr}")
                        return False
                else:
                    logger.error(f"Błąd podczas klonowania repozytorium: {stderr}")
                    return False
            
            # Tworzenie wirtualnego środowiska i instalacja zależności
            logger.info("Konfiguracja środowiska Python...")
            
            # Sprawdź, czy istnieje plik requirements.txt
            success, stdout, stderr = self.run_command(
                ssh_client,
                f'cd {repo_name} && [ -f requirements.txt ] && echo "Requirements found" || echo "No requirements"'
            )
            
            if "Requirements found" in stdout:
                # Instalacja zależności Python
                logger.info("Instalacja zależności Python...")
                success, stdout, stderr = self.run_command(
                    ssh_client,
                    f'cd {repo_name} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt'
                )
                
                if not success:
                    logger.error(f"Błąd podczas instalacji zależności Python: {stderr}")
                    return False
            
            logger.info("Środowisko zostało pomyślnie skonfigurowane")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji środowiska: {str(e)}")
            return False
    
    def deploy(self, hostname, username, password=None, key_filename=None, port=22, 
               repo_url=None, branch=None, install_deps=True):
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
            
        Returns:
            bool: Status powodzenia operacji
        """
        # Nawiąż połączenie z hostem
        success, ssh_client = self.connect(
            hostname=hostname,
            username=username,
            password=password,
            key_filename=key_filename,
            port=port
        )
        
        if not success or ssh_client is None:
            logger.error(f"Nie udało się połączyć z hostem {hostname}")
            return False
        
        try:
            # Skonfiguruj środowisko i zainstaluj projekt
            if repo_url:
                success = self.setup_environment(
                    ssh_client=ssh_client,
                    repo_url=repo_url,
                    branch=branch,
                    install_deps=install_deps
                )
                
                if not success:
                    logger.error("Wdrożenie nie powiodło się")
                    return False
                
                logger.info("Wdrożenie zakończone pomyślnie")
                return True
            else:
                logger.error("Nie podano URL repozytorium do wdrożenia")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas wdrażania: {str(e)}")
            return False
        finally:
            # Nie zamykamy połączenia, aby można było je ponownie wykorzystać
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
