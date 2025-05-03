"""
Infrash - Inteligentny runner do rozwiązywania problemów infrastrukturalnych.

Moduł ten zawiera narzędzia do automatyzacji zarządzania infrastrukturą,
diagnostyki problemów i wdrażania aplikacji z repozytoriów.
"""

__version__ = "0.1.8"
__author__ = "Twoje Imię"
__email__ = "twoj.email@example.com"

# Uruchom automatyczną diagnostykę przed importowaniem innych modułów
try:
    # Najpierw próbujemy zaimportować i uruchomić auto_diagnostics
    # aby naprawić ewentualne brakujące zależności
    import os
    import sys
    import subprocess
    
    # Sprawdź czy pkg_resources (setuptools) jest dostępne
    try:
        import pkg_resources
    except ImportError:
        print("Brak krytycznej zależności: pkg_resources (setuptools). Instalowanie...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
            import pkg_resources
            print("Pomyślnie zainstalowano setuptools (pkg_resources)")
        except Exception as e:
            print(f"Nie udało się zainstalować setuptools: {e}")
    
    # Teraz możemy bezpiecznie importować pozostałe moduły
    from infrash.system.auto_diagnostics import auto_diagnostics
    auto_diagnostics.run_diagnostics()
except Exception as e:
    # W przypadku błędu podczas diagnostyki, wyświetl informację, ale kontynuuj
    print(f"Ostrzeżenie: Automatyczna diagnostyka nie powiodła się: {e}")
    print("Infrash będzie kontynuować działanie, ale niektóre funkcje mogą być niedostępne.")

# Importy podstawowych komponentów, które powinny być dostępne bezpośrednio z pakietu
from infrash.core.runner import Runner
from infrash.core.config import Config
from infrash.core.diagnostics import Diagnostics
from infrash.core.repair import Repair

# Inicjalizacja domyślnej konfiguracji
config = Config()

# Funkcje wysokopoziomowe dla użytkowników pakietu
def init(path=None, **kwargs):
    """Inicjalizuje nowy projekt infrash."""
    from infrash.core.runner import init_project
    return init_project(path, **kwargs)

def run(command, **kwargs):
    """Uruchamia polecenie infrash."""
    runner = Runner()
    return runner.run(command, **kwargs)

def diagnose(target=None, **kwargs):
    """Przeprowadza diagnostykę systemu lub konkretnego celu."""
    diagnostics = Diagnostics()
    return diagnostics.run(target, **kwargs)

def repair(issue, **kwargs):
    """Naprawia zidentyfikowany problem."""
    repair_tool = Repair()
    return repair_tool.fix(issue, **kwargs)

# Wersjonowanie API
__all__ = [
    "Runner",
    "Config",
    "Diagnostics",
    "Repair",
    "init",
    "run",
    "diagnose",
    "repair",
    "config",
]