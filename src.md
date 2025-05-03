```
# Struktura pakietu infrash

```
infrash/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # GitHub Actions CI workflow
│       └── publish.yml             # PyPI publikacja
├── src/
│   └── infrash/
│       ├── __init__.py             # Inicjalizacja pakietu
│       ├── __main__.py             # Punkt wejścia do CLI
│       ├── cli.py                  # Interfejs wiersza poleceń
│       ├── core/
│       │   ├── __init__.py
│       │   ├── runner.py           # Główny moduł runnera
│       │   ├── installer.py        # Instalacja i zarządzanie pakietami
│       │   ├── diagnostics.py      # Diagnozowanie problemów
│       │   ├── repair.py           # Naprawa problemów
│       │   └── config.py           # Zarządzanie konfiguracją
│       ├── repo/
│       │   ├── __init__.py
│       │   ├── git.py              # Operacje na repozytoriach git
│       │   ├── updater.py          # Zarządzanie aktualizacjami
│       │   └── clone.py            # Klonowanie repozytoriów
│       ├── system/
│       │   ├── __init__.py
│       │   ├── dependency.py       # Zarządzanie zależnościami
│       │   ├── os_detect.py        # Wykrywanie systemu operacyjnego
│       │   ├── package_manager.py  # Obsługa menedżerów pakietów
│       │   └── service.py          # Zarządzanie usługami systemowymi
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── logger.py           # System logowania
│       │   ├── network.py          # Narzędzia sieciowe
│       │   ├── database.py         # Obsługa bazy danych rozwiązań
│       │   └── ai_solver.py        # Inteligentne rozwiązywanie problemów
│       └── data/
│           ├── __init__.py
│           ├── solutions/          # Baza danych rozwiązań
│           │   ├── __init__.py
│           │   ├── debian.json     # Rozwiązania dla Debian/Ubuntu
│           │   ├── redhat.json     # Rozwiązania dla Red Hat/CentOS/Fedora
│           │   ├── arch.json       # Rozwiązania dla Arch Linux
│           │   └── common.json     # Uniwersalne rozwiązania
│           └── templates/          # Szablony konfiguracyjne
├── tests/
│   ├── __init__.py
│   ├── test_runner.py
│   ├── test_installer.py
│   ├── test_diagnostics.py
│   └── test_repo.py
├── examples/
│   ├── basic_usage.py
│   └── advanced_configuration.py
├── docs/
│   ├── index.md
│   ├── installation.md
│   ├── usage.md
│   └── troubleshooting.md
├── .gitignore
├── LICENSE
├── MANIFEST.in
├── pyproject.toml
├── setup.py
└── README.md
```