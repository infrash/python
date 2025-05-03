#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł automatycznej diagnostyki i naprawy problemów z zależnościami.
Uruchamiany automatycznie przy starcie Infrash, aby zapewnić poprawne działanie.
"""

import os
import sys
import subprocess
import importlib
import logging
import time
from typing import List, Dict, Tuple, Optional, Union, Any

from infrash.utils.logger import get_logger

logger = get_logger(__name__)

class AutoDiagnostics:
    """
    Klasa do automatycznej diagnostyki i naprawy problemów z zależnościami.
    Wykrywa i naprawia typowe problemy, takie jak brakujące krytyczne zależności.
    """
    
    def __init__(self):
        """Inicjalizacja diagnostyki."""
        self.critical_packages = [
            "setuptools",  # Zawiera pkg_resources
            "wheel",
            "pip",
            "requests"
        ]
        
    def run_diagnostics(self) -> bool:
        """
        Uruchamia automatyczną diagnostykę i naprawę problemów.
        
        Returns:
            bool: True jeśli wszystkie problemy zostały naprawione, False w przeciwnym razie.
        """
        logger.info("Uruchamianie automatycznej diagnostyki...")
        
        # Sprawdź i napraw krytyczne zależności
        if not self._check_and_fix_critical_dependencies():
            logger.warning("Nie wszystkie krytyczne zależności zostały naprawione")
            return False
            
        # Sprawdź i napraw problemy z pip
        if not self._check_and_fix_pip():
            logger.warning("Problemy z pip nie zostały w pełni naprawione")
            return False
            
        # Sprawdź i napraw problemy z virtualenv
        if self._is_in_virtualenv() and not self._check_and_fix_virtualenv():
            logger.warning("Problemy z virtualenv nie zostały w pełni naprawione")
            return False
            
        logger.info("Automatyczna diagnostyka zakończona pomyślnie")
        return True
        
    def _check_and_fix_critical_dependencies(self, max_retries=3) -> bool:
        """
        Sprawdza i instaluje krytyczne zależności.
        
        Args:
            max_retries: Maksymalna liczba prób instalacji
            
        Returns:
            bool: True jeśli wszystkie krytyczne zależności zostały naprawione, False w przeciwnym razie.
        """
        logger.info("Sprawdzanie krytycznych zależności...")
        success = True
        
        for package in self.critical_packages:
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
                
        return success
        
    def _check_and_fix_pip(self, max_retries=3) -> bool:
        """
        Sprawdza i naprawia problemy z pip.
        
        Args:
            max_retries: Maksymalna liczba prób naprawy
            
        Returns:
            bool: True jeśli wszystkie problemy zostały naprawione, False w przeciwnym razie.
        """
        logger.info("Sprawdzanie pip...")
        
        try:
            # Sprawdź wersję pip
            try:
                import pip
                logger.debug(f"Zainstalowana wersja pip: {pip.__version__}")
            except (ImportError, AttributeError):
                logger.warning("Nie można określić wersji pip, próba aktualizacji...")
                
                for attempt in range(max_retries):
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
                        import pip
                        logger.info(f"Pomyślnie zaktualizowano pip do wersji {pip.__version__}")
                        break
                    except Exception as e:
                        logger.error(f"Próba {attempt+1}/{max_retries} aktualizacji pip nie powiodła się: {e}")
                        
                        if attempt < max_retries - 1:
                            time.sleep(2 * (attempt + 1))
                        else:
                            logger.error(f"Nie udało się zaktualizować pip po {max_retries} próbach")
                            return False
                            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania/naprawy pip: {e}")
            return False
            
    def _check_and_fix_virtualenv(self, max_retries=3) -> bool:
        """
        Sprawdza i naprawia problemy z virtualenv.
        
        Args:
            max_retries: Maksymalna liczba prób naprawy
            
        Returns:
            bool: True jeśli wszystkie problemy zostały naprawione, False w przeciwnym razie.
        """
        logger.info("Sprawdzanie środowiska wirtualnego...")
        
        try:
            # Sprawdź, czy virtualenv jest poprawnie skonfigurowany
            venv_path = os.environ.get('VIRTUAL_ENV')
            
            if not venv_path:
                logger.warning("Zmienna VIRTUAL_ENV nie jest ustawiona, ale wykryto środowisko wirtualne")
                # Próba wykrycia ścieżki virtualenv
                venv_path = self._detect_virtualenv_path()
                
                if venv_path:
                    logger.info(f"Wykryto środowisko wirtualne: {venv_path}")
                else:
                    logger.warning("Nie można wykryć ścieżki środowiska wirtualnego")
                    return False
                    
            # Sprawdź, czy site-packages jest w sys.path
            site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
            
            if not os.path.exists(site_packages):
                # Spróbuj alternatywną ścieżkę dla Windows
                site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
                
            if not os.path.exists(site_packages):
                logger.warning(f"Katalog site-packages nie istnieje: {site_packages}")
                return False
                
            if site_packages not in sys.path:
                logger.warning(f"Katalog site-packages nie jest w sys.path, dodawanie: {site_packages}")
                sys.path.insert(0, site_packages)
                
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania/naprawy virtualenv: {e}")
            return False
            
    def _is_in_virtualenv(self) -> bool:
        """
        Sprawdza, czy kod jest uruchamiany w środowisku wirtualnym.
        
        Returns:
            bool: True jeśli kod jest uruchamiany w środowisku wirtualnym, False w przeciwnym razie.
        """
        return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
    def _detect_virtualenv_path(self) -> Optional[str]:
        """
        Próbuje wykryć ścieżkę do środowiska wirtualnego.
        
        Returns:
            str: Ścieżka do środowiska wirtualnego lub None, jeśli nie można wykryć.
        """
        # Sprawdź, czy sys.prefix wskazuje na środowisko wirtualne
        if self._is_in_virtualenv():
            return sys.prefix
            
        return None


# Inicjalizacja i uruchomienie automatycznej diagnostyki przy importowaniu modułu
auto_diagnostics = AutoDiagnostics()
