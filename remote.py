#!/usr/bin/env python3
import argparse
import logging
import sys
import paramiko
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rpi_installer.log')
    ]
)

logger = logging.getLogger(__name__)


def setup_rpi_environment(ssh_client, repo_url):
    """
    Configure Raspberry Pi environment and install the project.

    Args:
        ssh_client: Connected SSH client
        repo_url: URL of the Git repository to install

    Returns:
        bool: Success or failure
    """
    try:
        # Update system
        logger.info("Aktualizacja systemu Raspberry Pi...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt-get update && sudo apt-get upgrade -y')
        stdout.channel.recv_exit_status()

        # Install dependencies
        logger.info("Instalacja zależności systemowych...")
        stdin, stdout, stderr = ssh_client.exec_command(
            'sudo apt-get install -y git python3 python3-pip python3-venv'
        )
        stdout.channel.recv_exit_status()

        # Clone repository
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        logger.info(f"Klonowanie repozytorium {repo_url}...")
        stdin, stdout, stderr = ssh_client.exec_command(f'git clone {repo_url}')
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            logger.error(f"Błąd podczas klonowania repozytorium: {stderr.read().decode()}")
            return False

        # Create virtual environment
        logger.info("Tworzenie wirtualnego środowiska...")
        stdin, stdout, stderr = ssh_client.exec_command(
            f'cd {repo_name} && python3 -m venv venv'
        )
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            logger.error(f"Błąd podczas tworzenia wirtualnego środowiska: {stderr.read().decode()}")
            return False

        # Install requirements
        logger.info("Instalacja wymagań...")
        stdin, stdout, stderr = ssh_client.exec_command(
            f'cd {repo_name} && source venv/bin/activate && pip install -r requirements.txt'
        )
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            logger.error(f"Błąd podczas instalacji wymagań: {stderr.read().decode()}")
            return False

        return True
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji środowiska: {str(e)}")
        return False


def connect_to_rpi(hostname, username, password=None, key_filename=None, port=22):
    """
    Connect to Raspberry Pi via SSH.

    Args:
        hostname: IP address or hostname of the Raspberry Pi
        username: SSH username
        password: SSH password (optional if using key authentication)
        key_filename: Path to the SSH private key file (optional)
        port: SSH port (default: 22)

    Returns:
        Connected SSH client or None if connection failed
    """
    try:
        logger.info(f"Łączenie z {hostname} jako {username}...")
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

        logger.info("Połączenie SSH nawiązane pomyślnie")
        return ssh_client
    except Exception as e:
        logger.error(f"Błąd podczas łączenia z Raspberry Pi: {str(e)}")
        return None

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description="Installer dla Raspberry Pi")
    parser.add_argument("--host", required=True, help="Adres IP lub nazwa hosta Raspberry Pi")
    parser.add_argument("--user", required=True, help="Nazwa użytkownika SSH")
    parser.add_argument("--password", help="Hasło SSH (opcjonalne jeśli używasz klucza)")
    parser.add_argument("--key", help="Ścieżka do pliku klucza prywatnego SSH")
    parser.add_argument("--port", type=int, default=22, help="Port SSH (domyślnie: 22)")
    parser.add_argument("--repo", required=True, help="URL repozytorium Git do zainstalowania")

    args = parser.parse_args()

    # Connect to the Raspberry Pi
    ssh_client = connect_to_rpi(
        hostname=args.host,
        username=args.user,
        password=args.password,
        key_filename=args.key,
        port=args.port
    )

    if not ssh_client:
        logger.error("Nie udało się połączyć z Raspberry Pi. Kończenie działania.")
        sys.exit(1)

    try:
        # Setup the Raspberry Pi environment
        success = setup_rpi_environment(ssh_client, args.repo)

        if success:
            logger.info("Instalacja na Raspberry Pi zakończona pomyślnie!")
        else:
            logger.error("Instalacja na Raspberry Pi nie powiodła się.")

    finally:
        # Close the SSH connection
        ssh_client.close()
        logger.info("Połączenie SSH zamknięte")

if __name__ == "__main__":
    main()