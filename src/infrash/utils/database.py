#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł obsługi bazy danych rozwiązań. Umożliwia przechowywanie, aktualizację
i wyszukiwanie rozwiązań problemów.
"""

import os
import sys
import json
import time
import hashlib
import tempfile
import requests
from typing import Dict, List, Any, Optional, Union

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os

# Inicjalizacja loggera
logger = get_logger(__name__)

class SolutionsDB:
    """
    Klasa zarządzająca bazą danych rozwiązań problemów.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Inicjalizuje nową instancję SolutionsDB.
        
        Args:
            db_path: Ścieżka do bazy danych (opcjonalnie).
        """
        self.os_info = detect_os()

        # Określamy ścieżkę do bazy danych
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "solutions"
            )

        # Tworzymy katalog bazy danych, jeśli nie istnieje
        os.makedirs(self.db_path, exist_ok=True)

        # Ładujemy bazę danych
        self.db = self._load_database()

        # Sprawdzamy, czy baza danych wymaga aktualizacji
        if self._should_update():
            self.update()

    def _load_database(self) -> Dict[str, Any]:
        """
        Ładuje bazę danych z plików.
        
        Returns:
            Słownik z bazą danych rozwiązań.
        """
        db = {}

        try:
            # Ładujemy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_file = os.path.join(self.db_path, f"{os_type}.json")

            if os.path.isfile(os_specific_file):
                with open(os_specific_file, 'r') as f:
                    os_specific_solutions = json.load(f)
                db.update(os_specific_solutions)

            # Ładujemy wspólne rozwiązania
            common_file = os.path.join(self.db_path, "common.json")
            if os.path.isfile(common_file):
                with open(common_file, 'r') as f:
                    common_solutions = json.load(f)
                db.update(common_solutions)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania bazy danych rozwiązań: {str(e)}")

        return db

    def _should_update(self) -> bool:
        """
        Sprawdza, czy baza danych wymaga aktualizacji.
        
        Returns:
            True, jeśli baza danych wymaga aktualizacji, False w przeciwnym razie.
        """
        # Sprawdzamy, kiedy ostatnio aktualizowano bazę danych
        last_update_file = os.path.join(self.db_path, "last_update.txt")

        if not os.path.isfile(last_update_file):
            return True

        try:
            with open(last_update_file, 'r') as f:
                last_update = float(f.read().strip())

            # Aktualizujemy bazę co 7 dni
            if time.time() - last_update > 7 * 24 * 60 * 60:
                return True
        except Exception:
            return True

        return False

    def update(self, force: bool = False) -> bool:
        """
        Aktualizuje bazę danych rozwiązań.
        
        Args:
            force: Czy wymusić aktualizację.
            
        Returns:
            True, jeśli baza danych została zaktualizowana pomyślnie, False w przeciwnym razie.
        """
        if not force and not self._should_update():
            logger.info("Baza danych rozwiązań jest aktualna")
            return True

        logger.info("Aktualizacja bazy danych rozwiązań")

        try:
            # Pobieramy aktualne rozwiązania z repozytorium
            solutions_url = "https://raw.githubusercontent.com/infrash/solutions/main"

            # Pobieramy rozwiązania dla konkretnego systemu
            os_type = self.os_info.get("type", "unknown").lower()
            os_specific_url = f"{solutions_url}/{os_type}.json"

            try:
                os_response = requests.get(os_specific_url, timeout=10)

                if os_response.status_code == 200:
                    os_specific_file = os.path.join(self.db_path, f"{os_type}.json")

                    with open(os_specific_file, 'w') as f:
                        f.write(os_response.text)

                    logger.info(f"Zaktualizowano rozwiązania dla systemu {os_type}")
            except Exception as e:
                logger.error(f"Błąd podczas pobierania rozwiązań dla systemu {os_type}: {str(e)}")

            # Pobieramy wspólne rozwiązania
            common_url = f"{solutions_url}/common.json"

            try:
                common_response = requests.get(common_url, timeout=10)

                if common_response.status_code == 200:
                    common_file = os.path.join(self.db_path, "common.json")

                    with open(common_file, 'w') as f:
                        f.write(common_response.text)

                    logger.info("Zaktualizowano wspólne rozwiązania")
            except Exception as e:
                logger.error(f"Błąd podczas pobierania wspólnych rozwiązań: {str(e)}")

            # Zapisujemy czas ostatniej aktualizacji
            last_update_file = os.path.join(self.db_path, "last_update.txt")

            with open(last_update_file, 'w') as f:
                f.write(str(time.time()))

            # Przeładowujemy bazę danych
            self.db = self._load_database()

            logger.info("Baza danych rozwiązań została zaktualizowana pomyślnie")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji bazy danych rozwiązań: {str(e)}")
            return False

    def get_solution(self, solution_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera rozwiązanie o podanym identyfikatorze.
        
        Args:
            solution_id: Identyfikator rozwiązania.
            
        Returns:
            Słownik z rozwiązaniem lub None, jeśli rozwiązanie nie istnieje.
        """
        return self.db.get(solution_id)

    def search_solutions(self, query: str) -> List[Dict[str, Any]]:
        """
        Wyszukuje rozwiązania pasujące do zapytania.
        
        Args:
            query: Zapytanie wyszukiwania.
            
        Returns:
            Lista rozwiązań pasujących do zapytania.
        """
        results = []

        # Normalizujemy zapytanie
        query = query.lower()

        for solution_id, solution in self.db.items():
            # Sprawdzamy, czy zapytanie pasuje do tytułu, opisu lub tagów
            title = solution.get("title", "").lower()
            description = solution.get("description", "").lower()
            tags = [tag.lower() for tag in solution.get("tags", [])]

            if query in title or query in description or query in tags:
                results.append({
                    "id": solution_id,
                    **solution
                })

        return results

    def find_solution_for_error(self, error_message: str) -> Optional[Dict[str, Any]]:
        """
        Wyszukuje rozwiązanie dla podanego komunikatu o błędzie.
        
        Args:
            error_message: Komunikat o błędzie.
            
        Returns:
            Słownik z rozwiązaniem lub None, jeśli nie znaleziono rozwiązania.
        """
        # Normalizujemy komunikat o błędzie
        error_message = error_message.lower()

        # Wyszukujemy rozwiązania pasujące do komunikatu o błędzie
        for solution_id, solution in self.db.items():
            # Sprawdzamy, czy komunikat o błędzie pasuje do wzorców
            patterns = solution.get("error_patterns", [])

            for pattern in patterns:
                if pattern.lower() in error_message:
                    return {
                        "id": solution_id,
                        **solution
                    }

        return None

    def add_solution(self, solution: Dict[str, Any]) -> bool:
        """
        Dodaje nowe rozwiązanie do bazy danych.
        
        Args:
            solution: Słownik z rozwiązaniem.
            
        Returns:
            True, jeśli rozwiązanie zostało dodane pomyślnie, False w przeciwnym razie.
        """
        try:
            # Generujemy identyfikator rozwiązania na podstawie tytułu
            title = solution.get("title", "")
            solution_id = hashlib.md5(title.encode()).hexdigest()

            # Pobieramy kategorię rozwiązania
            category = solution.get("category", "common")

            # Określamy plik, do którego zapisać rozwiązanie
            if category == "common":
                file_path = os.path.join(self.db_path, "common.json")
            else:
                os_type = self.os_info.get("type", "unknown").lower()
                file_path = os.path.join(self.db_path, f"{os_type}.json")

            # Ładujemy istniejące rozwiązania
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    solutions = json.load(f)
            else:
                solutions = {}

            # Dodajemy nowe rozwiązanie
            solutions[solution_id] = solution

            # Zapisujemy rozwiązania
            with open(file_path, 'w') as f:
                json.dump(solutions, f, indent=2)

            # Aktualizujemy bazę danych
            self.db[solution_id] = solution

            logger.info(f"Dodano nowe rozwiązanie: {title}")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas dodawania rozwiązania: {str(e)}")
            return False

    def list(self, filter: Optional[str] = None, os: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Zwraca listę dostępnych rozwiązań.
        
        Args:
            filter: Filtr na podstawie słowa kluczowego (opcjonalnie).
            os: Filtr na podstawie systemu operacyjnego (opcjonalnie).
            
        Returns:
            Lista dostępnych rozwiązań.
        """
        results = []

        for solution_id, solution in self.db.items():
            # Filtrujemy po słowie kluczowym
            if filter:
                filter = filter.lower()
                title = solution.get("title", "").lower()
                description = solution.get("description", "").lower()
                tags = [tag.lower() for tag in solution.get("tags", [])]

                if filter not in title and filter not in description and filter not in tags:
                    continue

            # Filtrujemy po systemie operacyjnym
            if os:
                solution_os = solution.get("os", "all").lower()

                if solution_os != "all" and solution_os != os.lower():
                    continue

            # Dodajemy rozwiązanie do wyników
            results.append({
                "id": solution_id,
                **solution
            })

        return results