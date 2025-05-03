#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł rozwiązywania problemów z zależnościami.
Zapewnia inteligentne rozwiązywanie konfliktów wersji pakietów,
automatyczne dostosowywanie wersji i obsługę ponownych prób połączenia.
"""

import os
import sys
import re
import time
import json
import tempfile
import subprocess
import pkg_resources
import logging
import requests
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
from packaging import version

from infrash.utils.logger import get_logger

# Inicjalizacja loggera
logger = get_logger(__name__)

# Maksymalna liczba prób połączenia
MAX_RETRIES = 3
# Czas oczekiwania między próbami (w sekundach)
RETRY_DELAY = 5
# Limit czasu dla żądań HTTP (w sekundach)
TIMEOUT = 30

class DependencyResolver:
    """
    Klasa do rozwiązywania problemów z zależnościami.
    """
    
    def __init__(self, remote=False, ssh_client=None):
        """
        Inicjalizacja resolwera zależności.
        
        Args:
            remote: Czy resolver działa na zdalnym urządzeniu
            ssh_client: Klient SSH do komunikacji ze zdalnym urządzeniem (opcjonalne)
        """
        self.remote = remote
        self.ssh_client = ssh_client
        self.pypi_cache = {}  # Cache dla informacji o pakietach z PyPI
        
    def update_pip(self, force=False):
        """
        Aktualizuje pip do najnowszej wersji.
        
        Args:
            force: Czy wymusić aktualizację nawet jeśli pip jest w najnowszej wersji
            
        Returns:
            bool: Status powodzenia operacji
        """
        try:
            if self.remote and self.ssh_client:
                # Wykonaj aktualizację pip na zdalnym urządzeniu
                cmd = "python3 -m pip install --upgrade pip"
                success, stdout, stderr = self._run_remote_command(cmd)
                
                if not success:
                    logger.error(f"Błąd podczas aktualizacji pip na zdalnym urządzeniu: {stderr}")
                    return False
                
                logger.info("Pip został zaktualizowany na zdalnym urządzeniu.")
                return True
            else:
                # Wykonaj aktualizację pip lokalnie
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
                
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                if process.returncode != 0:
                    logger.error(f"Błąd podczas aktualizacji pip: {process.stderr}")
                    return False
                
                logger.info("Pip został zaktualizowany.")
                return True
                
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji pip: {str(e)}")
            return False
    
    def get_available_versions(self, package_name: str) -> List[str]:
        """
        Pobiera dostępne wersje pakietu z PyPI.
        
        Args:
            package_name: Nazwa pakietu
            
        Returns:
            Lista dostępnych wersji pakietu
        """
        # Sprawdź, czy mamy już informacje o tym pakiecie w cache
        if package_name in self.pypi_cache:
            return self.pypi_cache[package_name]
        
        versions = []
        try:
            # Pobierz informacje o pakiecie z PyPI
            for attempt in range(MAX_RETRIES):
                try:
                    url = f"https://pypi.org/pypi/{package_name}/json"
                    response = requests.get(url, timeout=TIMEOUT)
                    
                    if response.status_code == 200:
                        data = response.json()
                        versions = list(data["releases"].keys())
                        # Zapisz do cache
                        self.pypi_cache[package_name] = versions
                        return versions
                    elif response.status_code == 404:
                        logger.warning(f"Pakiet {package_name} nie został znaleziony w PyPI.")
                        return []
                    else:
                        logger.warning(f"Nieoczekiwany kod odpowiedzi z PyPI: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Błąd połączenia z PyPI (próba {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        logger.error(f"Nie udało się połączyć z PyPI po {MAX_RETRIES} próbach.")
                        break
            
            # Jeśli nie udało się pobrać wersji z PyPI, spróbuj użyć pip
            if not versions:
                if self.remote and self.ssh_client:
                    cmd = f"pip index versions {package_name}"
                    success, stdout, stderr = self._run_remote_command(cmd)
                    
                    if success:
                        # Parsuj wyjście pip
                        match = re.search(r"Available versions: (.*)", stdout)
                        if match:
                            versions_str = match.group(1)
                            versions = [v.strip() for v in versions_str.split(",")]
                else:
                    cmd = [sys.executable, "-m", "pip", "index", "versions", package_name]
                    
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    if process.returncode == 0:
                        # Parsuj wyjście pip
                        match = re.search(r"Available versions: (.*)", process.stdout)
                        if match:
                            versions_str = match.group(1)
                            versions = [v.strip() for v in versions_str.split(",")]
            
            # Zapisz do cache
            self.pypi_cache[package_name] = versions
            return versions
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania dostępnych wersji pakietu {package_name}: {str(e)}")
            return []
    
    def find_closest_version(self, package_name: str, requested_version: str) -> Optional[str]:
        """
        Znajduje najbliższą dostępną wersję pakietu.
        
        Args:
            package_name: Nazwa pakietu
            requested_version: Żądana wersja pakietu
            
        Returns:
            Najbliższa dostępna wersja pakietu lub None, jeśli nie znaleziono
        """
        try:
            available_versions = self.get_available_versions(package_name)
            
            if not available_versions:
                logger.warning(f"Brak dostępnych wersji dla pakietu {package_name}")
                return None
            
            # Usuń specyfikatory wersji (np. ==, >=, <=)
            version_pattern = re.compile(r'([<>=!~]+)')
            clean_requested = version_pattern.sub('', requested_version).strip()
            
            # Jeśli żądana wersja jest dostępna, zwróć ją
            if clean_requested in available_versions:
                return clean_requested
            
            # Próbuj znaleźć najbliższą wersję
            try:
                req_version = version.parse(clean_requested)
                
                # Sortuj wersje według bliskości do żądanej wersji
                version_diffs = []
                for ver in available_versions:
                    try:
                        v = version.parse(ver)
                        # Oblicz różnicę między wersjami
                        # Priorytetyzuj wersje z tą samą wersją główną i poboczną
                        if v.major == req_version.major and v.minor == req_version.minor:
                            diff = abs(v.micro - req_version.micro)
                        else:
                            # Duża kara za różnice w wersji głównej lub pobocznej
                            diff = 1000 * abs(v.major - req_version.major) + 100 * abs(v.minor - req_version.minor)
                        
                        version_diffs.append((ver, diff))
                    except (AttributeError, TypeError):
                        # Pomiń wersje, których nie można sparsować
                        continue
                
                if version_diffs:
                    # Sortuj według różnicy (najmniejsza różnica pierwsza)
                    version_diffs.sort(key=lambda x: x[1])
                    return version_diffs[0][0]
                
            except Exception as e:
                logger.warning(f"Błąd podczas parsowania wersji {clean_requested}: {str(e)}")
            
            # Jeśli nie udało się znaleźć najbliższej wersji, zwróć najnowszą
            try:
                sorted_versions = sorted(
                    [v for v in available_versions if v],
                    key=lambda x: version.parse(x),
                    reverse=True
                )
                if sorted_versions:
                    logger.info(f"Używanie najnowszej wersji {sorted_versions[0]} dla pakietu {package_name}")
                    return sorted_versions[0]
            except Exception as e:
                logger.warning(f"Błąd podczas sortowania wersji: {str(e)}")
            
            # Jeśli wszystko zawiedzie, zwróć pierwszą dostępną wersję
            if available_versions:
                return available_versions[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd podczas znajdowania najbliższej wersji dla pakietu {package_name}: {str(e)}")
            return None
    
    def process_requirements_file(self, file_path: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Przetwarza plik requirements.txt, dostosowując niekompatybilne wersje pakietów.
        
        Args:
            file_path: Ścieżka do pliku requirements.txt
            output_path: Ścieżka do pliku wyjściowego (opcjonalne)
            
        Returns:
            Tuple: (Status powodzenia, Ścieżka do przetworzonego pliku)
        """
        if not os.path.isfile(file_path):
            logger.error(f"Plik {file_path} nie istnieje")
            return False, ""
        
        if not output_path:
            # Utwórz tymczasowy plik, jeśli nie podano ścieżki wyjściowej
            fd, output_path = tempfile.mkstemp(suffix='.txt', prefix='requirements_')
            os.close(fd)
        
        try:
            # Odczytaj plik requirements.txt
            with open(file_path, 'r') as f:
                requirements = f.readlines()
            
            processed_requirements = []
            modified = False
            
            # Przetwórz każdą linię
            for req in requirements:
                req = req.strip()
                
                # Pomiń komentarze i puste linie
                if not req or req.startswith('#'):
                    processed_requirements.append(req)
                    continue
                
                # Pomiń opcje edytowalne i URL
                if req.startswith('-e') or req.startswith('--editable') or \
                   req.startswith('http://') or req.startswith('https://') or req.startswith('git+'):
                    processed_requirements.append(req)
                    continue
                
                # Usuń komentarze z linii
                req_no_comment = req.split('#')[0].strip()
                
                # Sprawdź, czy linia zawiera specyfikację wersji
                version_match = re.search(r'([^<>=!~\s]+)\s*([<>=!~]+.*)', req_no_comment)
                
                if version_match:
                    package_name = version_match.group(1).strip()
                    version_spec = version_match.group(2).strip()
                    
                    # Sprawdź, czy wersja jest dokładnie określona (==)
                    exact_version_match = re.search(r'==\s*([^\s,]+)', version_spec)
                    
                    if exact_version_match:
                        requested_version = exact_version_match.group(1).strip()
                        
                        # Sprawdź dostępność wersji
                        available_versions = self.get_available_versions(package_name)
                        
                        if requested_version not in available_versions:
                            # Znajdź najbliższą dostępną wersję
                            closest_version = self.find_closest_version(package_name, requested_version)
                            
                            if closest_version and closest_version != requested_version:
                                # Zastąp wersję w linii
                                new_req = f"{package_name}=={closest_version}"
                                # Dodaj komentarz informujący o zmianie
                                comment = f"# Zmieniono z {requested_version} na {closest_version}"
                                if '#' in req:
                                    # Zachowaj oryginalny komentarz
                                    orig_comment = req.split('#', 1)[1].strip()
                                    comment = f"{comment}; {orig_comment}"
                                
                                processed_requirements.append(f"{new_req} #{comment}")
                                logger.info(f"Zmieniono wersję pakietu {package_name} z {requested_version} na {closest_version}")
                                modified = True
                                continue
                
                # Jeśli nie dokonano zmian, dodaj oryginalną linię
                processed_requirements.append(req)
            
            # Zapisz przetworzony plik
            with open(output_path, 'w') as f:
                f.write('\n'.join(processed_requirements))
            
            if modified:
                logger.info(f"Zapisano przetworzony plik requirements do {output_path}")
            else:
                logger.info(f"Nie znaleziono niekompatybilnych wersji w {file_path}")
            
            return True, output_path
            
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania pliku requirements.txt: {str(e)}")
            return False, ""
    
    def install_requirements_with_retry(self, file_path: str, venv_path: Optional[str] = None, 
                                       max_retries: int = MAX_RETRIES, force: bool = False) -> bool:
        """
        Instaluje zależności z pliku requirements.txt z obsługą ponownych prób.
        
        Args:
            file_path: Ścieżka do pliku requirements.txt
            venv_path: Ścieżka do wirtualnego środowiska (opcjonalne)
            max_retries: Maksymalna liczba prób
            force: Czy wymusić reinstalację istniejących zależności
            
        Returns:
            bool: Status powodzenia operacji
        """
        if not os.path.isfile(file_path):
            logger.error(f"Plik {file_path} nie istnieje")
            return False
        
        # Najpierw aktualizuj pip
        self.update_pip()
        
        # Przetwórz plik requirements.txt
        success, processed_file = self.process_requirements_file(file_path)
        
        if not success:
            logger.error("Nie udało się przetworzyć pliku requirements.txt")
            return False
        
        # Instaluj zależności z obsługą ponownych prób
        for attempt in range(max_retries):
            try:
                if self.remote and self.ssh_client:
                    # Wykonaj instalację na zdalnym urządzeniu
                    venv_activate = f"source {venv_path}/bin/activate && " if venv_path else ""
                    force_option = "--force-reinstall " if force else ""
                    
                    cmd = f"{venv_activate}pip install {force_option}-r {processed_file}"
                    success, stdout, stderr = self._run_remote_command(cmd)
                    
                    if success:
                        logger.info(f"Zależności zostały zainstalowane pomyślnie (próba {attempt+1}/{max_retries})")
                        return True
                    else:
                        logger.error(f"Błąd podczas instalacji zależności (próba {attempt+1}/{max_retries}): {stderr}")
                else:
                    # Wykonaj instalację lokalnie
                    cmd = [sys.executable, "-m", "pip", "install"]
                    
                    if force:
                        cmd.append("--force-reinstall")
                    
                    cmd.extend(["-r", processed_file])
                    
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    if process.returncode == 0:
                        logger.info(f"Zależności zostały zainstalowane pomyślnie (próba {attempt+1}/{max_retries})")
                        return True
                    else:
                        logger.error(f"Błąd podczas instalacji zależności (próba {attempt+1}/{max_retries}): {process.stderr}")
            
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności (próba {attempt+1}/{max_retries}): {str(e)}")
            
            # Jeśli to nie ostatnia próba, poczekaj przed kolejną
            if attempt < max_retries - 1:
                logger.info(f"Ponowna próba za {RETRY_DELAY} sekund...")
                time.sleep(RETRY_DELAY)
        
        logger.error(f"Nie udało się zainstalować zależności po {max_retries} próbach")
        return False
    
    def _run_remote_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Uruchamia polecenie na zdalnym urządzeniu.
        
        Args:
            command: Polecenie do uruchomienia
            
        Returns:
            Tuple: (Status powodzenia, standardowe wyjście, standardowe błędy)
        """
        if not self.ssh_client:
            logger.error("Brak połączenia SSH")
            return False, "", "Brak połączenia SSH"
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=60)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            
            if exit_status != 0:
                logger.error(f"Polecenie zakończone z kodem błędu {exit_status}: {stderr_str}")
                return False, stdout_str, stderr_str
            
            return True, stdout_str, stderr_str
            
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania zdalnego polecenia: {str(e)}")
            return False, "", str(e)
