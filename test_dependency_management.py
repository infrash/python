#!/usr/bin/env python3
"""
Skrypt testowy do sprawdzenia ulepszonego zarządzania zależnościami w infrash.
Ten skrypt testuje zarówno lokalną instalację zależności, jak i wdrażanie na zdalnym urządzeniu.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Dodaj katalog src do ścieżki, aby można było importować moduły infrash
sys.path.insert(0, str(Path(__file__).parent / "src"))

from infrash.system.dependency_resolver import DependencyResolver
from infrash.remote.remote_manager import RemoteManager

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dependency_test.log')
    ]
)

logger = logging.getLogger(__name__)

def test_local_dependency_resolver():
    """Testuje lokalny resolver zależności."""
    logger.info("=== Testowanie lokalnego resolvera zależności ===")
    
    # Utwórz tymczasowy plik requirements.txt z kilkoma zależnościami
    test_requirements = """
# Standardowe biblioteki
requests==2.25.1
numpy==1.19.5
pandas==1.2.0

# Biblioteki z potencjalnymi konfliktami
tensorflow==2.4.0
"""
    
    with open("test_requirements.txt", "w") as f:
        f.write(test_requirements)
    
    try:
        # Inicjalizuj resolver zależności
        resolver = DependencyResolver()
        
        # Testuj aktualizację pip
        logger.info("Testowanie aktualizacji pip...")
        success = resolver.update_pip()
        logger.info(f"Aktualizacja pip: {'Sukces' if success else 'Niepowodzenie'}")
        
        # Testuj przetwarzanie pliku requirements.txt
        logger.info("Testowanie przetwarzania pliku requirements.txt...")
        success, processed_path = resolver.process_requirements_file("test_requirements.txt")
        logger.info(f"Przetwarzanie requirements.txt: {'Sukces' if success else 'Niepowodzenie'}")
        
        # Wyświetl zawartość przetworzonego pliku
        if success:
            with open(processed_path, "r") as f:
                processed_content = f.read()
            logger.info(f"Zawartość przetworzonego pliku:\n{processed_content}")
        
        # Testuj pobieranie dostępnych wersji pakietu
        logger.info("Testowanie pobierania dostępnych wersji pakietu...")
        versions = resolver.get_available_versions("numpy")
        logger.info(f"Dostępne wersje numpy: {versions[:5]}... (i więcej)")
        
        # Testuj znajdowanie najbliższej wersji
        logger.info("Testowanie znajdowania najbliższej wersji...")
        closest = resolver.find_closest_version("tensorflow", "2.3.0")
        logger.info(f"Najbliższa wersja tensorflow dla 2.3.0: {closest}")
        
        # Opcjonalnie: testuj instalację zależności
        if "--install" in sys.argv:
            logger.info("Testowanie instalacji zależności...")
            success = resolver.install_requirements_with_retry(processed_path)
            logger.info(f"Instalacja zależności: {'Sukces' if success else 'Niepowodzenie'}")
    
    finally:
        # Usuń tymczasowe pliki
        if os.path.exists("test_requirements.txt"):
            os.remove("test_requirements.txt")
        if 'processed_path' in locals() and os.path.exists(processed_path):
            os.remove(processed_path)

def test_remote_deployment(host, username, password=None, key_filename=None):
    """
    Testuje wdrażanie na zdalnym urządzeniu.
    
    Args:
        host: Adres hosta zdalnego
        username: Nazwa użytkownika
        password: Hasło (opcjonalne)
        key_filename: Ścieżka do klucza SSH (opcjonalne)
    """
    logger.info(f"=== Testowanie wdrażania na zdalnym urządzeniu {host} ===")
    
    # Inicjalizuj menedżera zdalnego
    remote_manager = RemoteManager()
    
    # Testuj połączenie
    logger.info("Testowanie połączenia SSH...")
    ssh_client = remote_manager.connect(
        host, 
        username, 
        password=password, 
        key_filename=key_filename,
        retry_count=3,
        retry_delay=5
    )
    
    if not ssh_client:
        logger.error("Nie udało się nawiązać połączenia SSH")
        return
    
    logger.info("Połączenie SSH nawiązane pomyślnie")
    
    try:
        # Testuj wykonanie prostego polecenia
        logger.info("Testowanie wykonania polecenia...")
        success, stdout, stderr = remote_manager.run_command(ssh_client, "uname -a")
        
        if success:
            logger.info(f"Polecenie wykonane pomyślnie: {stdout}")
        else:
            logger.error(f"Błąd podczas wykonania polecenia: {stderr}")
        
        # Testuj wdrażanie
        if "--deploy" in sys.argv:
            repo_url = "https://github.com/example/test-repo.git"  # Zmień na rzeczywiste repozytorium
            
            logger.info(f"Testowanie wdrażania repozytorium {repo_url}...")
            success = remote_manager.deploy(
                host,
                username,
                password=password,
                key_filename=key_filename,
                repo_url=repo_url,
                install_deps=True,
                retry_count=3
            )
            
            if success:
                logger.info("Wdrażanie zakończone pomyślnie")
            else:
                logger.error("Wdrażanie nie powiodło się")
    
    finally:
        # Zamknij połączenie SSH
        ssh_client.close()
        logger.info("Połączenie SSH zamknięte")

def main():
    """Funkcja główna."""
    parser = argparse.ArgumentParser(description="Test zarządzania zależnościami w infrash")
    parser.add_argument("--local", action="store_true", help="Testuj lokalny resolver zależności")
    parser.add_argument("--remote", action="store_true", help="Testuj wdrażanie na zdalnym urządzeniu")
    parser.add_argument("--install", action="store_true", help="Testuj instalację zależności")
    parser.add_argument("--deploy", action="store_true", help="Testuj wdrażanie repozytorium")
    parser.add_argument("--host", help="Adres hosta zdalnego")
    parser.add_argument("--username", help="Nazwa użytkownika")
    parser.add_argument("--password", help="Hasło")
    parser.add_argument("--key", help="Ścieżka do klucza SSH")
    
    args = parser.parse_args()
    
    if args.local or not (args.local or args.remote):
        test_local_dependency_resolver()
    
    if args.remote:
        if not args.host or not args.username:
            logger.error("Dla testów zdalnych wymagane są argumenty --host i --username")
            return
        
        test_remote_deployment(
            args.host,
            args.username,
            password=args.password,
            key_filename=args.key
        )

if __name__ == "__main__":
    main()
