#!/bin/bash

# Skrypt uruchamiający infrash z automatyczną instalacją pakietu

# Przejdź do katalogu skryptu
cd "$(dirname "$0")"

# Uruchom wrapper Pythona
python run.py "$@"
