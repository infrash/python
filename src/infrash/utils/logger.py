"""
Moduł logowania dla infrash. Zapewnia spójny interfejs logowania
dla wszystkich modułów.
"""

import os
import sys
import logging
import tempfile
from datetime import datetime
from typing import Optional

# Domyślne ustawienia logowania
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Słownik przechowujący wszystkie loggery
loggers = {}

def setup_logger(name: Optional[str] = None,
                 level: int = DEFAULT_LOG_LEVEL,
                 log_file: Optional[str] = None,
                 console: bool = True,
                 file_mode: str = 'a') -> logging.Logger:
    """
    Konfiguruje i zwraca logger o podanej nazwie.

    Args:
        name: Nazwa loggera (opcjonalne). Jeśli nie podano, używa nazwę pakietu.
        level: Poziom logowania (opcjonalne). Domyślnie INFO.
        log_file: Ścieżka do pliku logów (opcjonalne). Domyślnie None (tylko konsola).
        console: Czy logować do konsoli (opcjonalne). Domyślnie True.
        file_mode: Tryb otwierania pliku logów (opcjonalne). Domyślnie 'a' (dopisywanie).

    Returns:
        Skonfigurowany logger.
    """
    # Jeśli nie podano nazwy, używamy infrash jako domyślnej
    if name is None:
        name = "infrash"

    # Sprawdzamy, czy logger już istnieje
    if name in loggers:
        return loggers[name]

    # Tworzymy nowy logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Zapobiegamy propagacji logów do loggera nadrzędnego

    # Określamy format logów
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT)

    # Dodajemy handler konsoli, jeśli wybrano
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Dodajemy handler pliku, jeśli podano ścieżkę
    if log_file:
        # Tworzymy katalog dla pliku logów, jeśli nie istnieje
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode=file_mode, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Zapisujemy logger w słowniku
    loggers[name] = logger

    return logger

def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    """
    Zwraca logger dla podanego modułu.

    Args:
        module_name: Nazwa modułu (opcjonalne). Jeśli nie podano, używa nazwę pakietu.

    Returns:
        Logger dla podanego modułu.
    """
    # Jeśli nie podano nazwy modułu, używamy nazwy wywołującego modułu
    if module_name is None:
        # Używamy inspect do pobrania nazwy wywołującego modułu
        import inspect
        frame = inspect.currentframe()
        if frame:
            frame = frame.f_back
            if frame:
                module_name = frame.f_globals.get('__name__', 'infrash')

    # Jeśli nadal nie mamy nazwy modułu, używamy infrash jako domyślnej
    if module_name is None:
        module_name = "infrash"

    # Tworzymy pełną nazwę loggera (infrash.module_name)
    logger_name = module_name
    if not module_name.startswith("infrash"):
        logger_name = f"infrash.{module_name}"

    # Sprawdzamy, czy logger już istnieje
    if logger_name in loggers:
        return loggers[logger_name]

    # Domyślny katalog logów
    log_dir = os.path.join(tempfile.gettempdir(), "infrash", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Nazwa pliku logów
    log_file = os.path.join(log_dir, f"{logger_name.replace('.', '_')}.log")

    # Konfigurujemy i zwracamy logger
    return setup_logger(logger_name, log_file=log_file)

def set_log_level(level: int) -> None:
    """
    Ustawia poziom logowania dla wszystkich loggerów.

    Args:
        level: Poziom logowania.
    """
    for logger in loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)

def get_log_levels() -> dict:
    """
    Zwraca słownik dostępnych poziomów logowania.

    Returns:
        Słownik {nazwa_poziomu: wartość}.
    """
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

def get_log_level_name(level: int) -> str:
    """
    Zwraca nazwę poziomu logowania.

    Args:
        level: Poziom logowania.
                Zwraca nazwę poziomu logowania.

        Args:
            level: Poziom logowania.

        Returns:
            Nazwa poziomu logowania.
        """
    levels = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL"
    }

    return levels.get(level, "UNKNOWN")

def create_rotating_file_handler(log_file: str,
                                 max_bytes: int = 10485760,  # 10 MB
                                 backup_count: int = 5,
                                 level: int = DEFAULT_LOG_LEVEL) -> logging.Handler:
    """
    Tworzy handler z rotacją plików logów.

    Args:
        log_file: Ścieżka do pliku logów.
        max_bytes: Maksymalny rozmiar pliku w bajtach, po którym nastąpi rotacja (opcjonalne).
        backup_count: Liczba kopii zapasowych (opcjonalne).
        level: Poziom logowania (opcjonalne).

    Returns:
        Handler z rotacją plików logów.
    """
    from logging.handlers import RotatingFileHandler

    # Tworzymy katalog dla pliku logów, jeśli nie istnieje
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Tworzymy handler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    # Ustawiamy poziom i format
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT))

    return handler

def add_file_handler(logger_name: str, log_file: str, level: int = DEFAULT_LOG_LEVEL) -> None:
    """
    Dodaje handler pliku do istniejącego loggera.

    Args:
        logger_name: Nazwa loggera.
        log_file: Ścieżka do pliku logów.
        level: Poziom logowania (opcjonalne).
    """
    # Pobieramy logger
    logger = logging.getLogger(logger_name)

    # Tworzymy katalog dla pliku logów, jeśli nie istnieje
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Tworzymy handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT))

    # Dodajemy handler do loggera
    logger.addHandler(file_handler)

def add_console_handler(logger_name: str, level: int = DEFAULT_LOG_LEVEL) -> None:
    """
    Dodaje handler konsoli do istniejącego loggera.

    Args:
        logger_name: Nazwa loggera.
        level: Poziom logowania (opcjonalne).
    """
    # Pobieramy logger
    logger = logging.getLogger(logger_name)

    # Tworzymy handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT))

    # Dodajemy handler do loggera
    logger.addHandler(console_handler)

def remove_handlers(logger_name: str) -> None:
    """
    Usuwa wszystkie handlery z loggera.

    Args:
        logger_name: Nazwa loggera.
    """
    # Pobieramy logger
    logger = logging.getLogger(logger_name)

    # Usuwamy wszystkie handlery
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

def configure_colored_logging() -> None:
    """
    Konfiguruje kolorowe logowanie w konsoli.
    """
    try:
        import colorama
        colorama.init()

        # Kody ANSI kolorów
        COLORS = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m'       # Reset
        }

        # Niestandardowy formatter
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                message = super().format(record)
                return f"{COLORS.get(levelname, '')}{message}{COLORS['RESET']}"

        # Zastosowanie kolorowego formattera do wszystkich handlerów konsoli
        for logger in loggers.values():
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setFormatter(ColoredFormatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT))

    except ImportError:
        # Biblioteka colorama nie jest zainstalowana
        pass#!/usr/bin/env python3
# -*- coding: utf-8 -*-

