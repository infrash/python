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

def main():
    """Funkcja główna dla punktu wejścia pakietu."""
    # Umożliwia uruchomienie jako moduł `python -m infrash`
    return cli()

if __name__ == "__main__":
    sys.exit(main())