#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skrypt testowy dla modułu rozwiązywania problemów z zależnościami.
Demonstruje działanie nowego mechanizmu rozwiązywania konfliktów wersji.
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

# Dodajemy ścieżkę do modułów infrash
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrash.system.dependency_resolver import DependencyResolver
from infrash.utils.logger import get_logger

logger = get_logger(__name__)

def create_test_requirements(path, include_problem=True):
    """
    Tworzy testowy plik requirements.txt z problematyczną wersją gpiozero.
    
    Args:
        path: Ścieżka do pliku wyjściowego
        include_problem: Czy dodać problematyczny pakiet
        
    Returns:
        Ścieżka do utworzonego pliku
    """
    requirements = [
        "requests==2.28.1",
        "numpy==1.23.5",
    ]
    
    if include_problem:
        # Dodajemy problematyczną wersję gpiozero
        requirements.append("gpiozero==2.0.1")  # Wersja niedostępna w PyPI
    
    with open(path, 'w') as f:
        f.write('\n'.join(requirements))
    
    logger.info(f"Utworzono testowy plik requirements: {path}")
    return path

def test_dependency_resolver(args):
    """
    Testuje działanie resolwera zależności.
    
    Args:
        args: Argumenty wiersza poleceń
    """
    resolver = DependencyResolver()
    
    # Aktualizacja pip
    if args.update_pip:
        logger.info("Aktualizacja pip...")
        success = resolver.update_pip()
        logger.info(f"Aktualizacja pip: {'Sukces' if success else 'Błąd'}")
    
    # Test pobierania dostępnych wersji
    if args.check_versions:
        package = args.package or "gpiozero"
        logger.info(f"Pobieranie dostępnych wersji pakietu {package}...")
        versions = resolver.get_available_versions(package)
        logger.info(f"Dostępne wersje pakietu {package}: {versions}")
    
    # Test znajdowania najbliższej wersji
    if args.find_closest:
        package = args.package or "gpiozero"
        version = args.version or "2.0.1"
        logger.info(f"Szukanie najbliższej wersji dla {package}=={version}...")
        closest = resolver.find_closest_version(package, version)
        logger.info(f"Najbliższa dostępna wersja: {closest}")
    
    # Test przetwarzania pliku requirements.txt
    if args.process_requirements:
        # Utwórz tymczasowy plik requirements.txt
        if args.requirements:
            requirements_path = args.requirements
        else:
            fd, requirements_path = tempfile.mkstemp(suffix='.txt', prefix='requirements_')
            os.close(fd)
            create_test_requirements(requirements_path, include_problem=True)
        
        logger.info(f"Przetwarzanie pliku requirements.txt: {requirements_path}")
        success, processed_path = resolver.process_requirements_file(requirements_path)
        
        if success:
            logger.info(f"Przetworzony plik: {processed_path}")
            
            # Wyświetl różnice
            with open(requirements_path, 'r') as f:
                original = f.readlines()
            
            with open(processed_path, 'r') as f:
                processed = f.readlines()
            
            logger.info("Oryginalne zależności:")
            for line in original:
                logger.info(f"  {line.strip()}")
            
            logger.info("Przetworzone zależności:")
            for line in processed:
                logger.info(f"  {line.strip()}")
        else:
            logger.error("Nie udało się przetworzyć pliku requirements.txt")
    
    # Test instalacji zależności
    if args.install:
        # Utwórz tymczasowy plik requirements.txt
        if args.requirements:
            requirements_path = args.requirements
        else:
            fd, requirements_path = tempfile.mkstemp(suffix='.txt', prefix='requirements_')
            os.close(fd)
            create_test_requirements(requirements_path, include_problem=True)
        
        logger.info(f"Instalacja zależności z pliku: {requirements_path}")
        success = resolver.install_requirements_with_retry(requirements_path, max_retries=args.retries)
        
        if success:
            logger.info("Instalacja zakończona pomyślnie")
        else:
            logger.error("Instalacja zakończona niepowodzeniem")

def main():
    parser = argparse.ArgumentParser(description="Test resolwera zależności")
    parser.add_argument("--update-pip", action="store_true", help="Aktualizuj pip")
    parser.add_argument("--check-versions", action="store_true", help="Sprawdź dostępne wersje pakietu")
    parser.add_argument("--find-closest", action="store_true", help="Znajdź najbliższą wersję pakietu")
    parser.add_argument("--process-requirements", action="store_true", help="Przetwórz plik requirements.txt")
    parser.add_argument("--install", action="store_true", help="Zainstaluj zależności")
    parser.add_argument("--package", help="Nazwa pakietu do sprawdzenia")
    parser.add_argument("--version", help="Wersja pakietu do sprawdzenia")
    parser.add_argument("--requirements", help="Ścieżka do pliku requirements.txt")
    parser.add_argument("--retries", type=int, default=3, help="Liczba prób instalacji")
    
    args = parser.parse_args()
    
    # Jeśli nie podano żadnych opcji, włącz wszystkie
    if not any([args.update_pip, args.check_versions, args.find_closest, 
                args.process_requirements, args.install]):
        args.update_pip = True
        args.check_versions = True
        args.find_closest = True
        args.process_requirements = True
        args.install = True
    
    test_dependency_resolver(args)

if __name__ == "__main__":
    main()
