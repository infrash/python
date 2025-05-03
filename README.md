# Infrash

Inteligentny runner do rozwiązywania problemów infrastrukturalnych, zarządzania repozytoriami i automatyzacji wdrożeń.

## Opis

Infrash to narzędzie wiersza poleceń zaprojektowane do automatyzacji i rozwiązywania problemów związanych z infrastrukturą IT. Umożliwia zarządzanie repozytoriami, instalację zależności, diagnostykę i naprawę problemów oraz wdrażanie aplikacji na różnych systemach operacyjnych.

## Architektura systemu

### Ogólna architektura

```mermaid
graph TB
    User([Użytkownik]) --> CLI[CLI]
    CLI --> Runner[Runner]
    CLI --> Diagnostics[Diagnostics]
    CLI --> Orchestrator[Orchestrator]
    
    Runner --> GitManager[Git Manager]
    Runner --> DependencyManager[Dependency Manager]
    Runner --> ProcessManager[Process Manager]
    
    Diagnostics --> NetworkDiagnostics[Network Diagnostics]
    Diagnostics --> SystemDiagnostics[System Diagnostics]
    Diagnostics --> SolutionsDB[(Solutions Database)]
    
    Orchestrator --> ProjectDetector[Project Detector]
    Orchestrator --> NetworkManager[Network Manager]
    Orchestrator --> DiagnosticsEngine[Diagnostics Engine]
    Orchestrator --> RemoteManager[Remote Manager]
    
    GitManager --> Git[(Git Repositories)]
    DependencyManager --> PackageManagers[(Package Managers)]
    ProcessManager --> RunningApps[(Running Applications)]
    
    NetworkManager --> RemoteHosts[(Remote Hosts)]
    
    style CLI fill:#f9f,stroke:#333,stroke-width:2px
    style Runner fill:#bbf,stroke:#333,stroke-width:2px
    style Diagnostics fill:#bfb,stroke:#333,stroke-width:2px
    style Orchestrator fill:#fbf,stroke:#333,stroke-width:2px
```

### Przepływ danych w systemie

```mermaid
sequenceDiagram
    participant User as Użytkownik
    participant CLI
    participant Orchestrator
    participant ProjectDetector
    participant DependencyManager
    participant NetworkManager
    participant DiagnosticsEngine
    participant RemoteManager
    
    User->>CLI: Uruchom komendę
    CLI->>Orchestrator: Przetwórz projekt
    
    Orchestrator->>Orchestrator: Sklonuj repozytorium
    
    Orchestrator->>ProjectDetector: Wykryj typ projektu
    ProjectDetector-->>Orchestrator: Zwróć typy projektu
    
    Orchestrator->>DependencyManager: Zainstaluj zależności
    DependencyManager-->>Orchestrator: Status instalacji
    
    alt Lokalne uruchomienie
        Orchestrator->>Orchestrator: Uruchom aplikację
    else Zdalne wdrożenie
        Orchestrator->>RemoteManager: Wdrożenie zdalne
        RemoteManager->>RemoteHost: Połącz z hostem
        RemoteHost-->>RemoteManager: Status połączenia
        RemoteManager->>RemoteHost: Skonfiguruj środowisko
        RemoteHost-->>RemoteManager: Status konfiguracji
    end
    
    alt Wystąpił błąd
        Orchestrator->>DiagnosticsEngine: Zdiagnozuj problem
        DiagnosticsEngine-->>Orchestrator: Sugestie rozwiązania
        Orchestrator-->>CLI: Wyświetl diagnostykę
    else Sukces
        Orchestrator-->>CLI: Zwróć status sukcesu
    end
    
    CLI-->>User: Wyświetl wynik
```

### Struktura modułów UnitMCP

```mermaid
classDiagram
    class Orchestrator {
        +project_detector: ProjectDetector
        +dependency_manager: DependencyManager
        +diagnostics: DiagnosticsEngine
        +network: NetworkManager
        +remote: RemoteManager
        +clone_repository()
        +detect_project_type()
        +install_dependencies()
        +setup_environment()
        +run_application()
        +process_project()
    }
    
    class ProjectDetector {
        +detect_project_type()
    }
    
    class DependencyManager {
        +check_tool_available()
        +install_tool()
        +install_dependencies()
    }
    
    class DiagnosticsEngine {
        +error_patterns: Dict
        +analyze_error()
        +check_network_connectivity()
        +check_system_requirements()
        +diagnose_network_issue()
        +diagnose_port_issue()
        +diagnose_git_issue()
    }
    
    class NetworkManager {
        +connect_ssh()
        +setup_remote_environment()
        +run_remote_command()
    }
    
    class RemoteManager {
        +deploy()
        +run_command()
    }
    
    Orchestrator --> ProjectDetector
    Orchestrator --> DependencyManager
    Orchestrator --> DiagnosticsEngine
    Orchestrator --> NetworkManager
    Orchestrator --> RemoteManager
```

### Przepływ diagnostyki

```mermaid
flowchart TD
    Start([Start]) --> DetectError[Wykryj błąd]
    DetectError --> AnalyzeError[Analizuj błąd]
    
    AnalyzeError --> IsNetworkIssue{Problem z siecią?}
    IsNetworkIssue -->|Tak| DiagnoseNetwork[Diagnozuj sieć]
    IsNetworkIssue -->|Nie| IsGitIssue{Problem z Git?}
    
    IsGitIssue -->|Tak| DiagnoseGit[Diagnozuj Git]
    IsGitIssue -->|Nie| IsDependencyIssue{Problem z zależnościami?}
    
    IsDependencyIssue -->|Tak| DiagnoseDependencies[Diagnozuj zależności]
    IsDependencyIssue -->|Nie| DiagnoseOther[Diagnozuj inne problemy]
    
    DiagnoseNetwork --> GenerateSuggestions[Generuj sugestie]
    DiagnoseGit --> GenerateSuggestions
    DiagnoseDependencies --> GenerateSuggestions
    DiagnoseOther --> GenerateSuggestions
    
    GenerateSuggestions --> DisplaySuggestions[Wyświetl sugestie]
    DisplaySuggestions --> CanAutoFix{Możliwa automatyczna naprawa?}
    
    CanAutoFix -->|Tak| AutoFix[Napraw automatycznie]
    CanAutoFix -->|Nie| ManualFix[Sugeruj ręczną naprawę]
    
    AutoFix --> End([Koniec])
    ManualFix --> End
    
    style Start fill:#f96,stroke:#333,stroke-width:2px
    style End fill:#f96,stroke:#333,stroke-width:2px
    style GenerateSuggestions fill:#bbf,stroke:#333,stroke-width:2px
    style AutoFix fill:#bfb,stroke:#333,stroke-width:2px
```

## Główne funkcje

- **Zarządzanie repozytoriami**: klonowanie, aktualizacja, synchronizacja
- **Zarządzanie zależnościami**: automatyczne wykrywanie i instalacja wymaganych pakietów
- **Diagnostyka i naprawa**: inteligentne wykrywanie i rozwiązywanie problemów
- **Automatyzacja wdrożeń**: instalacja, uruchamianie, monitorowanie aplikacji
- **Integracja z CI/CD**: obsługa GitLab CI i GitHub Actions
- **Baza danych rozwiązań**: aktualizowana baza wiedzy dotycząca popularnych problemów
- **Zdalne wdrażanie**: instalacja i konfiguracja aplikacji na zdalnych maszynach (np. Raspberry Pi)
- **Wieloplatformowe wsparcie**: uruchamianie aplikacji w różnych środowiskach (Python, Node.js, PHP, Shell, HTML)

## Zdalne wdrażanie (Remote)

Infrash umożliwia zdalne wdrażanie aplikacji na serwerach i urządzeniach IoT, takich jak Raspberry Pi. Funkcjonalność ta jest dostępna poprzez polecenie `infrash remote`.

### Wdrażanie aplikacji na zdalnych hostach

```bash
infrash remote deploy --host <adres_ip> --user <użytkownik> --repo <url_repozytorium> [--key <ścieżka_do_klucza>] [--branch <gałąź>] [--no-deps]
```

Przykład:
```bash
infrash remote deploy --host 192.168.1.100 --user pi --repo https://github.com/example/app.git --branch main
```

### Uruchamianie poleceń na zdalnych hostach

```bash
infrash remote run --host <adres_ip> --user <użytkownik> --command "<polecenie>" [--key <ścieżka_do_klucza>]
```

Przykład:
```bash
infrash remote run --host 192.168.1.100 --user pi --command "ls -la /home/pi/app"
```

### Architektura modułu Remote

```mermaid
graph TB
    CLI[CLI] --> RemoteManager[Remote Manager]
    RemoteManager --> SSHClient[SSH Client]
    RemoteManager --> EnvironmentSetup[Environment Setup]
    RemoteManager --> CommandRunner[Command Runner]
    
    SSHClient --> RemoteHost[(Remote Host)]
    EnvironmentSetup --> RemoteHost
    CommandRunner --> RemoteHost
    
    style RemoteManager fill:#f9f,stroke:#333,stroke-width:2px
    style SSHClient fill:#bbf,stroke:#333,stroke-width:2px
    style EnvironmentSetup fill:#bfb,stroke:#333,stroke-width:2px
    style CommandRunner fill:#fbf,stroke:#333,stroke-width:2px
```

### Przepływ zdalnego wdrażania

```mermaid
sequenceDiagram
    participant User as Użytkownik
    participant CLI
    participant RemoteManager
    participant SSHClient
    participant RemoteHost
    
    User->>CLI: infrash remote deploy
    CLI->>RemoteManager: Wywołaj deploy()
    
    RemoteManager->>SSHClient: Nawiąż połączenie SSH
    SSHClient->>RemoteHost: Połącz z hostem
    RemoteHost-->>SSHClient: Połączenie nawiązane
    
    RemoteManager->>RemoteHost: Zainstaluj zależności systemowe
    RemoteHost-->>RemoteManager: Zależności zainstalowane
    
    RemoteManager->>RemoteHost: Sklonuj repozytorium
    RemoteHost-->>RemoteManager: Repozytorium sklonowane
    
    RemoteManager->>RemoteHost: Utwórz środowisko wirtualne
    RemoteHost-->>RemoteManager: Środowisko utworzone
    
    RemoteManager->>RemoteHost: Zainstaluj zależności Python
    RemoteHost-->>RemoteManager: Zależności zainstalowane
    
    RemoteManager-->>CLI: Wdrożenie zakończone
    CLI-->>User: Wyświetl status wdrożenia
```

## Instalacja

### Instalacja z PyPI

```bash
pip install infrash
```

### Instalacja z repozytorium

```bash
git clone https://github.com/infrash/python.git
cd infrash
pip install -e .
```

### Uruchomienie bez instalacji

Repozytorium zawiera skrypt `run.sh`, który automatycznie instaluje pakiet w trybie deweloperskim i uruchamia aplikację:

```bash
./run.sh [komenda] [argumenty]
```

Skrypt ten sprawdzi, czy pakiet `infrash` jest zainstalowany, a jeśli nie, zainstaluje go automatycznie przed uruchomieniem.

## Szybki start

```bash
# Inicjalizacja projektu
infrash init
# lub
./run.sh init

# Klonowanie repozytorium
infrash repo clone https://github.com/username/project.git
# lub
./run.sh repo clone https://github.com/username/project.git

# Instalacja zależności
infrash install
# lub
./run.sh install

# Uruchomienie aplikacji
infrash start
# lub
./run.sh start

# Sprawdzenie statusu
infrash status
# lub
./run.sh status

# Zdiagnozowanie problemów
infrash diagnose
# lub
./run.sh diagnose
```

## Zaawansowane użycie

### Uruchomienie z pełną diagnostyką

```bash
infrash start --diagnostic-level=full
# lub
./run.sh start --diagnostic-level=full
```

### Automatyczna naprawa problemu

```bash
infrash repair --auto
# lub
./run.sh repair --auto
```

### Aktualizacja bazy danych rozwiązań

```bash
infrash solutions update
# lub
./run.sh solutions update
```

### Zdalne wdrażanie na Raspberry Pi

```bash
infrash remote deploy --host 192.168.188.154 --user pi --repo https://github.com/UnitApi/mcp.git
# lub
./run.sh remote deploy --host 192.168.188.154 --user pi --repo https://github.com/UnitApi/mcp.git
```

### Uruchomienie aplikacji z repozytorium Git

```bash
infrash runner --repo https://github.com/username/project.git --type python
# lub
./run.sh runner --repo https://github.com/username/project.git --type python
```

## Orchestrator

Infrash zawiera moduł orchestratora, który umożliwia zarządzanie wieloma wdrożeniami jednocześnie. Orchestrator pozwala na:

- Równoległe wdrażanie na wielu maszynach
- Koordynację aktualizacji między różnymi systemami
- Automatyczne wykrywanie i naprawę problemów
- Monitorowanie stanu wszystkich wdrożeń

Przykłady użycia orchestratora można znaleźć w katalogu `examples/orchestrator/`.

### Architektura Orchestratora

```mermaid
graph TB
    CLI[CLI] --> Orchestrator
    
    subgraph "Orchestrator Module"
        Orchestrator[Orchestrator] --> ProjectDetector
        Orchestrator --> DependencyManager
        Orchestrator --> DiagnosticsEngine
        Orchestrator --> NetworkManager
        Orchestrator --> RemoteManager
        
        ProjectDetector --> FilePatterns[(File Patterns)]
        DependencyManager --> ToolInstaller[Tool Installer]
        DiagnosticsEngine --> ErrorPatterns[(Error Patterns)]
        NetworkManager --> SSHClient[SSH Client]
        RemoteManager --> RemoteHost[(Remote Host)]
        
        ToolInstaller --> SystemPackages[(System Packages)]
        ToolInstaller --> LanguagePackages[(Language Packages)]
    end
    
    Orchestrator --> GitRepos[(Git Repositories)]
    Orchestrator --> RunningApps[(Running Applications)]
    NetworkManager --> RemoteHosts[(Remote Hosts)]
    
    style Orchestrator fill:#f9f,stroke:#333,stroke-width:2px
    style ProjectDetector fill:#bbf,stroke:#333,stroke-width:2px
    style DependencyManager fill:#bfb,stroke:#333,stroke-width:2px
    style DiagnosticsEngine fill:#fbf,stroke:#333,stroke-width:2px
    style NetworkManager fill:#ff9,stroke:#333,stroke-width:2px
    style RemoteManager fill:#ff9,stroke:#333,stroke-width:2px
```

## Zależności

Infrash wymaga następujących pakietów:
- Python 3.8+
- Git
- click>=8.0.0
- GitPython>=3.1.0
- requests>=2.25.0
- rich>=10.0.0
- pyyaml>=6.0
- psutil>=5.9.0
- packaging>=21.0
- Paramiko (dla zdalnych wdrożeń)

Wszystkie zależności zostaną automatycznie zainstalowane podczas instalacji pakietu.

## Rozwiązywanie problemów

### Brak modułu unitmcp

Jeśli napotkasz błąd `No module named 'unitmcp'`, oznacza to, że próbujesz uruchomić funkcje, które wymagają pakietu `unitmcp`. Ten pakiet jest opcjonalny i używany tylko do integracji z projektem UnitMCP. Możesz:

1. Zainstalować pakiet unitmcp, jeśli potrzebujesz tej funkcjonalności:
   ```bash
   pip install unitmcp
   ```

2. Używać tylko funkcji infrash, które nie wymagają unitmcp.

## Licencja



## Autor





[<span style='font-size:20px;'>&#x270D;</span>](git@github.com:UnitApi/python/edit/main/docs/footer.md)
<script type="module">    
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  //import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.8.0/dist/mermaid.min.js';
  mermaid.initialize({
    startOnReady:true,
    theme: 'forest',
    flowchart:{
            useMaxWidth:false,
            htmlLabels:true
        }
  });
  mermaid.init(undefined, '.language-mermaid');
</script>
