"""
Infrash - Inteligentny runner do rozwiązywania problemów infrastrukturalnych.

Moduł ten zawiera narzędzia do automatyzacji zarządzania infrastrukturą,
diagnostyki problemów i wdrażania aplikacji z repozytoriów.
"""

__version__ = "0.1.1"
__author__ = "Twoje Imię"
__email__ = "twoj.email@example.com"

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