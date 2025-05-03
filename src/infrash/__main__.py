"""
__main__.py
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Główny punkt wejścia dla narzędzia wiersza poleceń infrash.
Obsługuje wywołania z poziomu konsoli.
"""

import sys
from infrash.cli import cli
from infrash.system.auto_diagnostics import auto_diagnostics

def main():
    """Funkcja główna dla punktu wejścia pakietu."""
    try:
        # Uruchom automatyczną diagnostykę przed wykonaniem jakiegokolwiek polecenia
        auto_diagnostics.run_diagnostics()
    except Exception as e:
        print(f"Ostrzeżenie: Automatyczna diagnostyka nie powiodła się: {e}")
        print("Infrash będzie kontynuować działanie, ale niektóre funkcje mogą być niedostępne.")
    
    # Umożliwia uruchomienie jako moduł `python -m infrash`
    return cli()

if __name__ == "__main__":
    sys.exit(main())