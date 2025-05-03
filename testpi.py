#!/usr/bin/env python3
import argparse
import logging
import sys
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('git_runner.log')
    ]
)

logger = logging.getLogger(__name__)

from infrash.core.installer import Installer  # Import the Installer class
from gitrunner import GitRunner  # Import our GitRunner class


def handle_exit(signum, frame):
    """Handle termination signals gracefully."""
    logger.info("Zamykanie aplikacji...")
    sys.exit(0)


def main():
    """Main function to handle CLI arguments and run the application."""
    parser = argparse.ArgumentParser(description='Runner do projektów z Git')

    parser.add_argument('--repo', type=str, required=True,
                        help='URL repozytorium Git do pobrania i uruchomienia')
    parser.add_argument('--port', type=int, default=None,
                        help='Port, na którym ma być uruchomiony projekt (opcjonalnie)')
    parser.add_argument('--target', type=str, default=None,
                        help='Katalog docelowy dla repozytorium (opcjonalnie)')
    parser.add_argument('--host', type=str, default=None,
                        help='Adres hosta do zdalnego uruchomienia (opcjonalnie)')
    parser.add_argument('--username', type=str, default=None,
                        help='Nazwa użytkownika dla zdalnego hosta (opcjonalnie)')

    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # If host is provided, run on remote machine
    if args.host:
        logger.info(f"Uruchamianie na zdalnym hoście: {args.host}")

        # This would normally use SSH to connect and run the script on a remote host
        # For now, we'll just simulate it by showing what would be done

        username = args.username or "pi"  # Default to 'pi' for Raspberry Pi

        # Example command that would be sent to the remote machine
        remote_command = (
            f"git clone {args.repo} && "
            f"cd $(basename {args.repo} .git) && "
            f"python3 -m pip install -r requirements.txt && "
            f"python3 app.py"
        )

        logger.info(f"Polecenie do wykonania na zdalnym hoście: {remote_command}")
        logger.info("Symulacja uruchomienia na zdalnym hoście")

        # In a real implementation, you would use paramiko or similar to run this command
        # via SSH on the remote host

    else:
        # Run locally
        logger.info("Uruchamianie lokalnie")

        # Check if required tools are installed
        installer = Installer()
        if not installer.is_package_installed("git"):
            logger.info("Instalacja git...")
            installer.install_package("git")

        # Create GitRunner and process the project
        runner = GitRunner()
        success, process = runner.process_project(args.repo, args.target, args.port)

        if success and process:
            logger.info("Projekt został pomyślnie uruchomiony")

            try:
                # Keep the script running until the user terminates it
                while True:
                    time.sleep(1)

                    # Check if the process is still running
                    if process.poll() is not None:
                        logger.error("Proces zakończył działanie. Kod wyjścia: " + str(process.returncode))
                        break

            except KeyboardInterrupt:
                logger.info("Zatrzymywanie projektu...")
                if process.poll() is None:
                    process.terminate()
        else:
            logger.error("Nie udało się uruchomić projektu")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())