#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł rozwiązywania problemów z zależnościami.
Służy do automatycznego rozwiązywania konfliktów wersji pakietów,
aktualizacji pip i inteligentnej obsługi błędów podczas instalacji.
"""

import os
import sys
import re
import time
import tempfile
import subprocess
import json
import logging
from typing import List, Dict, Tuple, Optional, Union, Any
import requests
from packaging import version

from infrash.utils.logger import get_logger

logger = get_logger(__name__)

class DependencyResolver:
    """
    Klasa do rozwiązywania problemów z zależnościami.
    Obsługuje automatyczne rozwiązywanie konfliktów wersji pakietów,
    aktualizację pip i inteligentną obsługę błędów podczas instalacji.
    """
    
    def __init__(self, remote=False, ssh_client=None):
        """
        Inicjalizuje resolver zależności.
        
        Args:
            remote: Czy resolver działa na zdalnym urządzeniu.
            ssh_client: Klient SSH do komunikacji ze zdalnym urządzeniem.
        """
        self.remote = remote
        self.ssh_client = ssh_client
        self.pypi_url = "https://pypi.org/pypi"
        self.pypi_simple_url = "https://pypi.org/simple"
        self.cache_dir = os.path.expanduser("~/.infrash/cache")
        
        # Utwórz katalog cache, jeśli nie istnieje
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def update_pip(self) -> bool:
        """
        Aktualizuje pip do najnowszej wersji.
        
        Returns:
            True, jeśli aktualizacja się powiodła, False w przeciwnym razie.
        """
        try:
            if self.remote and self.ssh_client:
                # Aktualizacja pip na zdalnym urządzeniu
                stdin, stdout, stderr = self.ssh_client.exec_command(
                    f"{sys.executable} -m pip install --upgrade pip"
                )
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    logger.warning(f"Błąd podczas aktualizacji pip na zdalnym urządzeniu: {stderr.read().decode()}")
                    return False
                logger.info("Pip został zaktualizowany na zdalnym urządzeniu.")
            else:
                # Aktualizacja pip lokalnie
                process = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                if process.returncode != 0:
                    logger.warning(f"Błąd podczas aktualizacji pip: {process.stderr}")
                    return False
                logger.info("Pip został zaktualizowany.")
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji pip: {str(e)}")
            return False
    
    def get_available_versions(self, package_name: str) -> List[str]:
        """
        Pobiera listę dostępnych wersji pakietu z PyPI.
        
        Args:
            package_name: Nazwa pakietu.
            
        Returns:
            Lista dostępnych wersji pakietu.
        """
        cache_file = os.path.join(self.cache_dir, f"{package_name}_versions.json")
        
        # Sprawdź, czy mamy wersje w cache
        if os.path.exists(cache_file):
            # Sprawdź, czy cache nie jest starszy niż 1 dzień
            if time.time() - os.path.getmtime(cache_file) < 86400:  # 24 godziny
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Błąd podczas odczytu cache wersji: {str(e)}")
        
        # Pobierz wersje z PyPI z obsługą ponownych prób
        max_retries = 3
        retry_delay = 2
        versions = []
        
        for attempt in range(max_retries):
            try:
                # Najpierw próbujemy użyć API PyPI
                response = requests.get(f"{self.pypi_url}/{package_name}/json", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    versions = list(data.get('releases', {}).keys())
                else:
                    # Jeśli API nie działa, próbujemy użyć strony simple
                    response = requests.get(f"{self.pypi_simple_url}/{package_name}/", timeout=10)
                    
                    if response.status_code == 200:
                        # Parsowanie HTML strony simple
                        pattern = r'href="[^"]*?/([0-9.]+)/?[^"]*?"'
                        versions = list(set(re.findall(pattern, response.text)))
                
                # Zapisz wersje do cache
                if versions:
                    try:
                        with open(cache_file, 'w') as f:
                            json.dump(versions, f)
                    except Exception as e:
                        logger.warning(f"Błąd podczas zapisywania cache wersji: {str(e)}")
                
                return versions
            except requests.exceptions.RequestException as e:
                logger.warning(f"Błąd podczas pobierania wersji pakietu {package_name} (próba {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Zwiększamy czas oczekiwania przy każdej próbie
        
        # Jeśli wszystkie próby zawiodły, zwracamy pustą listę
        logger.error(f"Nie udało się pobrać wersji pakietu {package_name} po {max_retries} próbach")
        return []
    
    def find_closest_version(self, package_name: str, required_version: str) -> Optional[str]:
        """
        Znajduje najbliższą dostępną wersję pakietu.
        
        Args:
            package_name: Nazwa pakietu.
            required_version: Wymagana wersja pakietu.
            
        Returns:
            Najbliższa dostępna wersja pakietu lub None, jeśli nie znaleziono.
        """
        try:
            # Pobierz dostępne wersje
            available_versions = self.get_available_versions(package_name)
            
            if not available_versions:
                logger.warning(f"Nie znaleziono dostępnych wersji pakietu {package_name}")
                return None
            
            # Sprawdź, czy wymagana wersja jest dostępna
            if required_version in available_versions:
                return required_version
            
            # Usuń specyfikatory wersji (==, >=, <=, >, <, ~=, !=)
            version_pattern = r'^([<>=!~]+)'
            clean_required_version = re.sub(version_pattern, '', required_version)
            
            # Sprawdź, czy oczyszczona wersja jest dostępna
            if clean_required_version in available_versions:
                return clean_required_version
            
            # Parsuj wersję wymaganą i dostępne wersje
            try:
                req_version = version.parse(clean_required_version)
            except Exception:
                logger.warning(f"Nie można sparsować wersji {clean_required_version}")
                return None
            
            # Znajdź najbliższą wersję
            closest_version = None
            min_diff = float('inf')
            
            for ver in available_versions:
                try:
                    v = version.parse(ver)
                    
                    # Oblicz różnicę między wersjami
                    # Priorytetyzujemy wersje o tym samym numerze głównym
                    if isinstance(req_version, version.Version) and isinstance(v, version.Version):
                        if req_version.major == v.major:
                            # Jeśli wersja główna jest taka sama, oblicz różnicę
                            diff = abs(req_version.minor - v.minor) + abs(req_version.micro - v.micro) * 0.1
                            
                            # Preferuj nowsze wersje, ale nie przyszłe
                            if v.minor <= req_version.minor:
                                diff *= 0.8
                            
                            if diff < min_diff:
                                min_diff = diff
                                closest_version = ver
                except Exception:
                    # Ignoruj wersje, których nie można sparsować
                    continue
            
            # Jeśli nie znaleziono wersji z tym samym numerem głównym, wybierz najnowszą dostępną
            if closest_version is None:
                try:
                    # Sortuj wersje semantycznie
                    sorted_versions = sorted(
                        [v for v in available_versions if re.match(r'^[0-9.]+$', v)],
                        key=lambda x: version.parse(x),
                        reverse=True
                    )
                    
                    if sorted_versions:
                        closest_version = sorted_versions[0]
                except Exception as e:
                    logger.warning(f"Błąd podczas sortowania wersji: {str(e)}")
            
            if closest_version:
                logger.info(f"Znaleziono najbliższą wersję {closest_version} dla pakietu {package_name}=={required_version}")
            else:
                logger.warning(f"Nie znaleziono najbliższej wersji dla pakietu {package_name}=={required_version}")
            
            return closest_version
        except Exception as e:
            logger.error(f"Błąd podczas szukania najbliższej wersji dla {package_name}=={required_version}: {str(e)}")
            return None
    
    def process_requirements_file(self, file_path: str, output_path: str = None) -> Tuple[bool, str]:
        """
        Przetwarza plik requirements.txt, dostosowując niekompatybilne wersje.
        
        Args:
            file_path: Ścieżka do pliku requirements.txt.
            output_path: Ścieżka do pliku wyjściowego (opcjonalne).
            
        Returns:
            Tuple (bool, str): Status powodzenia i ścieżka do przetworzonego pliku.
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Plik {file_path} nie istnieje")
                return False, file_path
            
            # Jeśli nie podano ścieżki wyjściowej, utwórz tymczasowy plik
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.txt', prefix='processed_requirements_')
                os.close(fd)
            
            # Odczytaj plik requirements.txt
            with open(file_path, 'r') as f:
                requirements = f.readlines()
            
            processed_requirements = []
            modified = False
            
            # Przetwórz każdą linię
            for line in requirements:
                line = line.strip()
                
                # Pomiń puste linie i komentarze
                if not line or line.startswith('#'):
                    processed_requirements.append(line)
                    continue
                
                # Znajdź nazwę pakietu i wersję
                match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', line)
                
                if match:
                    package_name = match.group(1)
                    operator = match.group(2)
                    package_version = match.group(3)
                    rest = match.group(4)
                    
                    # Sprawdź, czy wersja jest dostępna
                    if operator == '==':
                        closest_version = self.find_closest_version(package_name, package_version)
                        
                        if closest_version and closest_version != package_version:
                            # Dodaj oryginalną wersję jako komentarz
                            processed_requirements.append(f"# Oryginalna wersja: {line}")
                            processed_requirements.append(f"{package_name}=={closest_version}{rest}")
                            logger.info(f"Zmieniono wersję {package_name} z {package_version} na {closest_version}")
                            modified = True
                            continue
                
                # Jeśli nie ma potrzeby modyfikacji, dodaj oryginalną linię
                processed_requirements.append(line)
            
            # Zapisz przetworzony plik
            with open(output_path, 'w') as f:
                f.write('\n'.join(processed_requirements))
            
            if modified:
                logger.info(f"Przetworzono plik requirements.txt i zapisano do {output_path}")
            else:
                logger.info(f"Plik requirements.txt nie wymaga modyfikacji")
            
            return True, output_path
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania pliku requirements.txt: {str(e)}")
            return False, file_path
    
    def install_requirements_with_retry(self, requirements_path: str, venv_path: str = None, max_retries: int = 3) -> bool:
        """
        Instaluje zależności z pliku requirements.txt z obsługą ponownych prób.
        
        Args:
            requirements_path: Ścieżka do pliku requirements.txt.
            venv_path: Ścieżka do wirtualnego środowiska (opcjonalne).
            max_retries: Maksymalna liczba prób.
            
        Returns:
            True, jeśli instalacja się powiodła, False w przeciwnym razie.
        """
        try:
            # Najpierw przetwórz plik requirements.txt
            success, processed_path = self.process_requirements_file(requirements_path)
            
            if not success:
                logger.warning(f"Nie udało się przetworzyć pliku {requirements_path}, używanie oryginalnego pliku")
                processed_path = requirements_path
            
            # Instalacja z obsługą ponownych prób
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    # Przygotuj polecenie instalacji
                    if self.remote and self.ssh_client:
                        # Instalacja na zdalnym urządzeniu
                        if venv_path:
                            cmd = f"source {venv_path}/bin/activate && "
                        else:
                            cmd = ""
                        
                        cmd += f"pip install -r {processed_path}"
                        
                        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                        exit_code = stdout.channel.recv_exit_status()
                        
                        if exit_code == 0:
                            logger.info(f"Zależności zostały zainstalowane pomyślnie (próba {attempt+1}/{max_retries})")
                            return True
                        else:
                            error = stderr.read().decode()
                            logger.error(f"Błąd podczas instalacji zależności (próba {attempt+1}/{max_retries}): {error}")
                    else:
                        # Instalacja lokalnie
                        cmd = [sys.executable, "-m", "pip", "install", "-r", processed_path]
                        
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
                    logger.info(f"Ponowna próba za {retry_delay} sekund...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Zwiększamy czas oczekiwania przy każdej próbie
            
            # Jeśli wszystkie próby zawiodły, spróbuj zainstalować pakiety jeden po drugim
            logger.info("Próba instalacji pakietów jeden po drugim...")
            
            try:
                # Odczytaj plik requirements.txt
                with open(processed_path, 'r') as f:
                    requirements = f.readlines()
                
                packages = []
                for line in requirements:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        packages.append(line)
                
                if not packages:
                    logger.warning("Brak pakietów do zainstalowania")
                    return False
                
                success_count = 0
                
                for package in packages:
                    try:
                        if self.remote and self.ssh_client:
                            # Instalacja na zdalnym urządzeniu
                            if venv_path:
                                cmd = f"source {venv_path}/bin/activate && "
                            else:
                                cmd = ""
                            
                            cmd += f"pip install {package}"
                            
                            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                            exit_code = stdout.channel.recv_exit_status()
                            
                            if exit_code == 0:
                                logger.info(f"Pakiet {package} został zainstalowany pomyślnie")
                                success_count += 1
                            else:
                                error = stderr.read().decode()
                                logger.warning(f"Błąd podczas instalacji pakietu {package}: {error}")
                        else:
                            # Instalacja lokalnie
                            cmd = [sys.executable, "-m", "pip", "install", package]
                            
                            process = subprocess.run(
                                cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True
                            )
                            
                            if process.returncode == 0:
                                logger.info(f"Pakiet {package} został zainstalowany pomyślnie")
                                success_count += 1
                            else:
                                logger.warning(f"Błąd podczas instalacji pakietu {package}: {process.stderr}")
                    except Exception as e:
                        logger.warning(f"Błąd podczas instalacji pakietu {package}: {str(e)}")
                
                # Jeśli zainstalowano przynajmniej połowę pakietów, uznaj to za sukces
                if success_count >= len(packages) / 2:
                    logger.info(f"Zainstalowano {success_count}/{len(packages)} pakietów")
                    return True
                else:
                    logger.error(f"Zainstalowano tylko {success_count}/{len(packages)} pakietów")
                    return False
            except Exception as e:
                logger.error(f"Błąd podczas instalacji pakietów jeden po drugim: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
            return False
    
    def install_packages_one_by_one(self, requirements_path: str, venv_path: str = None) -> bool:
        """
        Instaluje pakiety z pliku requirements.txt jeden po drugim.
        Przydatne, gdy instalacja zbiorcza zawiedzie.
        
        Args:
            requirements_path: Ścieżka do pliku requirements.txt.
            venv_path: Ścieżka do wirtualnego środowiska (opcjonalne).
            
        Returns:
            True, jeśli instalacja większości pakietów się powiodła, False w przeciwnym razie.
        """
        try:
            # Odczytaj plik requirements.txt
            with open(requirements_path, 'r') as f:
                requirements = f.readlines()
            
            packages = []
            for line in requirements:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages.append(line)
            
            if not packages:
                logger.warning("Brak pakietów do zainstalowania")
                return False
            
            logger.info(f"Instalacja {len(packages)} pakietów jeden po drugim...")
            success_count = 0
            
            for package in packages:
                try:
                    if self.remote and self.ssh_client:
                        # Instalacja na zdalnym urządzeniu
                        if venv_path:
                            cmd = f"source {venv_path}/bin/activate && "
                        else:
                            cmd = ""
                        
                        cmd += f"pip install {package}"
                        
                        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                        exit_code = stdout.channel.recv_exit_status()
                        
                        if exit_code == 0:
                            logger.info(f"Pakiet {package} został zainstalowany pomyślnie")
                            success_count += 1
                        else:
                            error = stderr.read().decode()
                            logger.warning(f"Błąd podczas instalacji pakietu {package}: {error}")
                            
                            # Spróbuj znaleźć alternatywną wersję pakietu
                            match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', package)
                            if match:
                                package_name = match.group(1)
                                operator = match.group(2)
                                package_version = match.group(3)
                                rest = match.group(4)
                                
                                if operator == '==':
                                    closest_version = self.find_closest_version(package_name, package_version)
                                    
                                    if closest_version and closest_version != package_version:
                                        alternative_package = f"{package_name}=={closest_version}{rest}"
                                        logger.info(f"Próba instalacji alternatywnej wersji: {alternative_package}")
                                        
                                        cmd = f"pip install {alternative_package}"
                                        if venv_path:
                                            cmd = f"source {venv_path}/bin/activate && {cmd}"
                                        
                                        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                                        exit_code = stdout.channel.recv_exit_status()
                                        
                                        if exit_code == 0:
                                            logger.info(f"Alternatywna wersja pakietu {alternative_package} została zainstalowana pomyślnie")
                                            success_count += 1
                                        else:
                                            error = stderr.read().decode()
                                            logger.warning(f"Błąd podczas instalacji alternatywnej wersji pakietu {alternative_package}: {error}")
                    else:
                        # Instalacja lokalnie
                        cmd = [sys.executable, "-m", "pip", "install", package]
                        
                        process = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True
                        )
                        
                        if process.returncode == 0:
                            logger.info(f"Pakiet {package} został zainstalowany pomyślnie")
                            success_count += 1
                        else:
                            logger.warning(f"Błąd podczas instalacji pakietu {package}: {process.stderr}")
                            
                            # Spróbuj znaleźć alternatywną wersję pakietu
                            match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', package)
                            if match:
                                package_name = match.group(1)
                                operator = match.group(2)
                                package_version = match.group(3)
                                rest = match.group(4)
                                
                                if operator == '==':
                                    closest_version = self.find_closest_version(package_name, package_version)
                                    
                                    if closest_version and closest_version != package_version:
                                        alternative_package = f"{package_name}=={closest_version}{rest}"
                                        logger.info(f"Próba instalacji alternatywnej wersji: {alternative_package}")
                                        
                                        alt_cmd = [sys.executable, "-m", "pip", "install", alternative_package]
                                        
                                        alt_process = subprocess.run(
                                            alt_cmd,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            universal_newlines=True
                                        )
                                        
                                        if alt_process.returncode == 0:
                                            logger.info(f"Alternatywna wersja pakietu {alternative_package} została zainstalowana pomyślnie")
                                            success_count += 1
                                        else:
                                            logger.warning(f"Błąd podczas instalacji alternatywnej wersji pakietu {alternative_package}: {alt_process.stderr}")
                except Exception as e:
                    logger.warning(f"Błąd podczas instalacji pakietu {package}: {str(e)}")
            
            # Jeśli zainstalowano przynajmniej połowę pakietów, uznaj to za sukces
            if success_count >= len(packages) / 2:
                logger.info(f"Zainstalowano {success_count}/{len(packages)} pakietów")
                return True
            else:
                logger.error(f"Zainstalowano tylko {success_count}/{len(packages)} pakietów")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas instalacji pakietów jeden po drugim: {str(e)}")
            return False

    def check_dependencies(self, requirements_path: str, venv_path: str = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Sprawdza, czy wszystkie zależności z pliku requirements.txt są zainstalowane
        i w odpowiednich wersjach.
        
        Args:
            requirements_path: Ścieżka do pliku requirements.txt.
            venv_path: Ścieżka do wirtualnego środowiska (opcjonalne).
            
        Returns:
            Tuple (bool, List[Dict]): Status powodzenia i lista problemów z zależnościami.
            Każdy problem jest słownikiem z kluczami: 'package', 'required_version', 'installed_version', 'status'.
        """
        try:
            # Odczytaj plik requirements.txt
            with open(requirements_path, 'r') as f:
                requirements = f.readlines()
            
            packages = []
            for line in requirements:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages.append(line)
            
            if not packages:
                logger.warning("Brak pakietów do sprawdzenia")
                return True, []
            
            logger.info(f"Sprawdzanie {len(packages)} pakietów...")
            issues = []
            all_ok = True
            
            # Pobierz listę zainstalowanych pakietów
            if self.remote and self.ssh_client:
                # Sprawdzenie na zdalnym urządzeniu
                cmd = "pip list --format=json"
                if venv_path:
                    cmd = f"source {venv_path}/bin/activate && {cmd}"
                
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                exit_code = stdout.channel.recv_exit_status()
                
                if exit_code != 0:
                    error = stderr.read().decode()
                    logger.error(f"Błąd podczas pobierania listy pakietów: {error}")
                    return False, []
                
                installed_packages_json = stdout.read().decode()
                try:
                    installed_packages = json.loads(installed_packages_json)
                    installed_dict = {pkg['name'].lower(): pkg['version'] for pkg in installed_packages}
                except Exception as e:
                    logger.error(f"Błąd podczas parsowania listy pakietów: {str(e)}")
                    return False, []
            else:
                # Sprawdzenie lokalnie
                try:
                    process = subprocess.run(
                        [sys.executable, "-m", "pip", "list", "--format=json"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    if process.returncode != 0:
                        logger.error(f"Błąd podczas pobierania listy pakietów: {process.stderr}")
                        return False, []
                    
                    installed_packages = json.loads(process.stdout)
                    installed_dict = {pkg['name'].lower(): pkg['version'] for pkg in installed_packages}
                except Exception as e:
                    logger.error(f"Błąd podczas parsowania listy pakietów: {str(e)}")
                    return False, []
            
            # Sprawdź każdy pakiet
            for package_spec in packages:
                try:
                    # Parsuj specyfikację pakietu
                    match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', package_spec)
                    
                    if match:
                        package_name = match.group(1)
                        operator = match.group(2)
                        required_version = match.group(3)
                        
                        # Sprawdź, czy pakiet jest zainstalowany
                        if package_name.lower() not in installed_dict:
                            issues.append({
                                'package': package_name,
                                'required_version': required_version,
                                'installed_version': None,
                                'status': 'missing'
                            })
                            all_ok = False
                            continue
                        
                        installed_version = installed_dict[package_name.lower()]
                        
                        # Sprawdź wersję
                        if operator == '==':
                            if installed_version != required_version:
                                issues.append({
                                    'package': package_name,
                                    'required_version': required_version,
                                    'installed_version': installed_version,
                                    'status': 'version_mismatch'
                                })
                                all_ok = False
                            else:
                                issues.append({
                                    'package': package_name,
                                    'required_version': required_version,
                                    'installed_version': installed_version,
                                    'status': 'ok'
                                })
                        elif operator == '>=':
                            try:
                                if version.parse(installed_version) < version.parse(required_version):
                                    issues.append({
                                        'package': package_name,
                                        'required_version': f'>={required_version}',
                                        'installed_version': installed_version,
                                        'status': 'version_too_low'
                                    })
                                    all_ok = False
                                else:
                                    issues.append({
                                        'package': package_name,
                                        'required_version': f'>={required_version}',
                                        'installed_version': installed_version,
                                        'status': 'ok'
                                    })
                            except Exception:
                                # Jeśli nie można porównać wersji, załóż, że jest OK
                                issues.append({
                                    'package': package_name,
                                    'required_version': f'>={required_version}',
                                    'installed_version': installed_version,
                                    'status': 'unknown'
                                })
                        # Dodaj obsługę innych operatorów (<=, >, <, ~=, !=) w podobny sposób
                    else:
                        # Jeśli nie ma specyfikacji wersji, sprawdź tylko, czy pakiet jest zainstalowany
                        package_name = package_spec.split('#')[0].strip()  # Usuń komentarze
                        package_name = re.split(r'[<>=!~]', package_name)[0].strip()  # Usuń operatory
                        
                        if package_name.lower() not in installed_dict:
                            issues.append({
                                'package': package_name,
                                'required_version': 'any',
                                'installed_version': None,
                                'status': 'missing'
                            })
                            all_ok = False
                        else:
                            issues.append({
                                'package': package_name,
                                'required_version': 'any',
                                'installed_version': installed_dict[package_name.lower()],
                                'status': 'ok'
                            })
                except Exception as e:
                    logger.warning(f"Błąd podczas sprawdzania pakietu {package_spec}: {str(e)}")
                    issues.append({
                        'package': package_spec,
                        'required_version': 'unknown',
                        'installed_version': 'unknown',
                        'status': 'error',
                        'error': str(e)
                    })
                    all_ok = False
            
            # Podsumowanie
            missing_count = len([i for i in issues if i['status'] == 'missing'])
            version_mismatch_count = len([i for i in issues if i['status'] in ['version_mismatch', 'version_too_low']])
            
            if missing_count > 0:
                logger.warning(f"Brakuje {missing_count} pakietów")
            
            if version_mismatch_count > 0:
                logger.warning(f"{version_mismatch_count} pakietów ma nieodpowiednią wersję")
            
            if all_ok:
                logger.info("Wszystkie zależności są zainstalowane i w odpowiednich wersjach")
            
            return all_ok, issues
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania zależności: {str(e)}")
            return False, []

    def resolve_dependency_conflicts(self, requirements_path: str, output_path: str = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Automatycznie rozwiązuje konflikty wersji pakietów w pliku requirements.txt.
        
        Args:
            requirements_path: Ścieżka do pliku requirements.txt.
            output_path: Ścieżka do pliku wyjściowego (opcjonalne).
            
        Returns:
            Tuple (bool, str, List[Dict]): Status powodzenia, ścieżka do przetworzonego pliku
            i lista rozwiązanych konfliktów.
        """
        try:
            if not os.path.exists(requirements_path):
                logger.error(f"Plik {requirements_path} nie istnieje")
                return False, requirements_path, []
            
            # Jeśli nie podano ścieżki wyjściowej, utwórz tymczasowy plik
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.txt', prefix='resolved_requirements_')
                os.close(fd)
            
            # Odczytaj plik requirements.txt
            with open(requirements_path, 'r') as f:
                requirements = f.readlines()
            
            processed_requirements = []
            conflicts_resolved = []
            
            # Przetwórz każdą linię
            for line in requirements:
                line = line.strip()
                
                # Pomiń puste linie i komentarze
                if not line or line.startswith('#'):
                    processed_requirements.append(line)
                    continue
                
                # Znajdź nazwę pakietu i wersję
                match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', line)
                
                if match:
                    package_name = match.group(1)
                    operator = match.group(2)
                    package_version = match.group(3)
                    rest = match.group(4)
                    
                    # Sprawdź, czy wersja jest dostępna
                    if operator == '==':
                        available_versions = self.get_available_versions(package_name)
                        
                        if package_version not in available_versions:
                            closest_version = self.find_closest_version(package_name, package_version)
                            
                            if closest_version and closest_version != package_version:
                                # Dodaj oryginalną wersję jako komentarz
                                processed_requirements.append(f"# Oryginalna wersja: {line}")
                                processed_requirements.append(f"{package_name}=={closest_version}{rest}")
                                
                                conflicts_resolved.append({
                                    'package': package_name,
                                    'original_version': package_version,
                                    'resolved_version': closest_version,
                                    'reason': 'version_not_available'
                                })
                                
                                logger.info(f"Zmieniono wersję {package_name} z {package_version} na {closest_version}")
                                continue
                
                # Jeśli nie ma potrzeby modyfikacji, dodaj oryginalną linię
                processed_requirements.append(line)
            
            # Sprawdź zależności między pakietami
            packages_dict = {}
            for line in processed_requirements:
                if not line or line.startswith('#'):
                    continue
                
                match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~]+)([a-zA-Z0-9_.-]+)(.*)$', line)
                if match:
                    package_name = match.group(1)
                    operator = match.group(2)
                    package_version = match.group(3)
                    
                    if package_name not in packages_dict:
                        packages_dict[package_name] = []
                    
                    packages_dict[package_name].append({
                        'operator': operator,
                        'version': package_version,
                        'line': line
                    })
            
            # Znajdź konflikty (pakiety z wieloma wersjami)
            for package_name, versions in packages_dict.items():
                if len(versions) > 1:
                    # Znajdź najnowszą wersję
                    try:
                        exact_versions = [v for v in versions if v['operator'] == '==']
                        
                        if len(exact_versions) > 1:
                            # Sortuj wersje semantycznie
                            sorted_versions = sorted(
                                exact_versions,
                                key=lambda x: version.parse(x['version']),
                                reverse=True
                            )
                            
                            latest_version = sorted_versions[0]['version']
                            
                            # Zastąp wszystkie wersje najnowszą
                            for i, line in enumerate(processed_requirements):
                                for v in exact_versions:
                                    if v['line'] == line and v['version'] != latest_version:
                                        processed_requirements[i] = f"# Konflikt wersji: {line}"
                                        processed_requirements.insert(i + 1, f"{package_name}=={latest_version}")
                                        
                                        conflicts_resolved.append({
                                            'package': package_name,
                                            'original_version': v['version'],
                                            'resolved_version': latest_version,
                                            'reason': 'version_conflict'
                                        })
                                        
                                        logger.info(f"Rozwiązano konflikt wersji {package_name}: {v['version']} -> {latest_version}")
                    except Exception as e:
                        logger.warning(f"Błąd podczas rozwiązywania konfliktu wersji dla {package_name}: {str(e)}")
            
            # Zapisz przetworzony plik
            with open(output_path, 'w') as f:
                f.write('\n'.join(processed_requirements))
            
            if conflicts_resolved:
                logger.info(f"Rozwiązano {len(conflicts_resolved)} konfliktów wersji i zapisano do {output_path}")
            else:
                logger.info(f"Nie znaleziono konfliktów wersji w pliku {requirements_path}")
            
            return True, output_path, conflicts_resolved
        except Exception as e:
            logger.error(f"Błąd podczas rozwiązywania konfliktów wersji: {str(e)}")
            return False, requirements_path, []

    def ensure_critical_dependencies(self, max_retries=3):
        """
        Sprawdza i instaluje krytyczne zależności wymagane do działania Infrash.
        
        Ta funkcja jest wywoływana automatycznie podczas wdrażania, aby zapewnić,
        że wszystkie niezbędne zależności są dostępne zarówno lokalnie, jak i na
        zdalnych systemach.
        
        Args:
            max_retries: Maksymalna liczba prób instalacji
            
        Returns:
            bool: True jeśli wszystkie krytyczne zależności są dostępne lub zostały zainstalowane,
                  False w przypadku niepowodzenia.
        """
        critical_packages = [
            "setuptools",  # Zawiera pkg_resources
            "wheel",
            "pip",
            "requests"
        ]
        
        logger.info("Sprawdzanie krytycznych zależności...")
        success = True
        
        for package in critical_packages:
            logger.debug(f"Sprawdzanie pakietu {package}...")
            
            if self.remote:
                # W trybie zdalnym sprawdzamy i instalujemy pakiety przez SSH
                check_cmd = f"python3 -c 'try: import {package if package != 'setuptools' else 'pkg_resources'}; print(\"OK\"); except ImportError: print(\"MISSING\")'"
                
                for attempt in range(max_retries):
                    try:
                        stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
                        result = stdout.read().decode().strip()
                        
                        if result == "MISSING":
                            logger.warning(f"Brak krytycznej zależności na zdalnym systemie: {package}. Instalowanie...")
                            
                            # Instalacja pakietu
                            install_cmd = f"pip3 install --user {package}"
                            stdin, stdout, stderr = self.ssh_client.exec_command(install_cmd)
                            exit_code = stdout.channel.recv_exit_status()
                            
                            if exit_code == 0:
                                logger.info(f"Pomyślnie zainstalowano {package} na zdalnym systemie")
                                break
                            else:
                                error = stderr.read().decode()
                                logger.error(f"Błąd podczas instalacji {package} na zdalnym systemie: {error}")
                                
                                if attempt < max_retries - 1:
                                    time.sleep(2 * (attempt + 1))
                                else:
                                    success = False
                        else:
                            logger.debug(f"Pakiet {package} jest już zainstalowany na zdalnym systemie")
                            break
                            
                    except Exception as e:
                        logger.error(f"Błąd podczas sprawdzania/instalacji {package} na zdalnym systemie: {str(e)}")
                        
                        if attempt < max_retries - 1:
                            time.sleep(2 * (attempt + 1))
                        else:
                            success = False
            else:
                # W trybie lokalnym sprawdzamy i instalujemy pakiety bezpośrednio
                try:
                    if package == "setuptools":
                        # Specjalny przypadek dla pkg_resources
                        try:
                            import pkg_resources
                            logger.debug("Pakiet pkg_resources (setuptools) jest już zainstalowany")
                        except ImportError:
                            logger.warning("Brak krytycznej zależności: pkg_resources (setuptools). Instalowanie...")
                            
                            for attempt in range(max_retries):
                                try:
                                    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
                                    import pkg_resources  # Próba ponownego importu
                                    logger.info("Pomyślnie zainstalowano setuptools (pkg_resources)")
                                    break
                                except Exception as e:
                                    logger.error(f"Próba {attempt+1}/{max_retries} instalacji setuptools nie powiodła się: {e}")
                                    
                                    if attempt < max_retries - 1:
                                        time.sleep(2 * (attempt + 1))
                                    else:
                                        logger.error(f"Nie udało się zainstalować setuptools po {max_retries} próbach")
                                        success = False
                    else:
                        # Standardowa weryfikacja dla innych pakietów
                        module_name = package.replace("-", "_")
                        try:
                            __import__(module_name)
                            logger.debug(f"Pakiet {package} jest już zainstalowany")
                        except ImportError:
                            logger.warning(f"Brak krytycznej zależności: {package}. Instalowanie...")
                            
                            for attempt in range(max_retries):
                                try:
                                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                                    __import__(module_name)  # Próba ponownego importu
                                    logger.info(f"Pomyślnie zainstalowano {package}")
                                    break
                                except Exception as e:
                                    logger.error(f"Próba {attempt+1}/{max_retries} instalacji {package} nie powiodła się: {e}")
                                    
                                    if attempt < max_retries - 1:
                                        time.sleep(2 * (attempt + 1))
                                    else:
                                        logger.error(f"Nie udało się zainstalować {package} po {max_retries} próbach")
                                        success = False
                except Exception as e:
                    logger.error(f"Błąd podczas weryfikacji zależności {package}: {e}")
                    success = False
        
        if success:
            logger.info("Wszystkie krytyczne zależności są dostępne")
        else:
            logger.warning("Niektóre krytyczne zależności mogą być niedostępne")
            
        return success
