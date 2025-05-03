#!/bin/bash
# Przykładowy skrypt wdrożeniowy dla Infrash
# Demonstruje użycie poleceń Infrash do wdrażania aplikacji

set -e  # Zatrzymaj w przypadku błędu

# Kolory dla lepszej czytelności
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funkcja do wyświetlania komunikatów
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] BŁĄD: $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] UWAGA: $1${NC}"
}

# Sprawdź, czy Infrash jest zainstalowany
if ! command -v infrash &> /dev/null; then
    error "Infrash nie jest zainstalowany. Zainstaluj go używając: pip install infrash"
fi

# Parametry wdrożenia
HOST=${1:-"192.168.1.100"}
USER=${2:-"pi"}
REPO=${3:-"https://github.com/example/app.git"}
BRANCH=${4:-"main"}

log "Rozpoczynam wdrażanie na host: $HOST"
log "Użytkownik: $USER"
log "Repozytorium: $REPO"
log "Gałąź: $BRANCH"

# Uruchom diagnostykę przed wdrożeniem
log "Uruchamiam diagnostykę..."
infrash diagnose || warn "Diagnostyka wykryła problemy, ale kontynuuję wdrażanie"

# Wdróż aplikację na zdalnym hoście
log "Wdrażam aplikację..."
if infrash remote deploy --host "$HOST" --user "$USER" --repo "$REPO" --branch "$BRANCH"; then
    log "Wdrożenie zakończone pomyślnie!"
else
    error "Wdrożenie nie powiodło się"
fi

# Uruchom aplikację na zdalnym hoście
log "Uruchamiam aplikację..."
if infrash remote run --host "$HOST" --user "$USER" --command "cd $(basename $REPO .git) && source venv/bin/activate && python app.py"; then
    log "Aplikacja uruchomiona pomyślnie!"
else
    error "Uruchomienie aplikacji nie powiodło się"
fi

# Sprawdź status aplikacji
log "Sprawdzam status aplikacji..."
if infrash remote run --host "$HOST" --user "$USER" --command "ps aux | grep python"; then
    log "Aplikacja działa poprawnie!"
else
    warn "Nie można sprawdzić statusu aplikacji"
fi

log "Wdrożenie zakończone pomyślnie!"
exit 0
