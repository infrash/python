# Infrash Remote - Dokumentacja

## Przegląd

Moduł `remote` w Infrash umożliwia zdalne wdrażanie aplikacji i wykonywanie poleceń na serwerach i urządzeniach IoT, takich jak Raspberry Pi. Funkcjonalność ta jest zintegrowana z CLI Infrash i dostępna poprzez polecenie `infrash remote`.

## Wymagania

- Python 3.6+
- Infrash zainstalowany (`pip install infrash`)
- Pakiet paramiko (instalowany automatycznie jako zależność Infrash)
- Urządzenie zdalne z włączonym SSH
- Połączenie sieciowe z urządzeniem zdalnym

## Instalacja

Funkcjonalność remote jest dostępna po zainstalowaniu Infrash:

```bash
pip install infrash
```

## Użycie

### Wdrażanie aplikacji na zdalnych hostach

```bash
infrash remote deploy --host <adres_ip> --user <użytkownik> --repo <url_repozytorium> [--key <ścieżka_do_klucza>] [--password <hasło>] [--branch <gałąź>] [--port <port>] [--no-deps]
```

#### Parametry

- `--host`: Adres IP lub nazwa hosta urządzenia zdalnego (wymagane)
- `--user`: Nazwa użytkownika SSH (wymagane)
- `--repo`: URL repozytorium Git do wdrożenia (wymagane)
- `--password`: Hasło SSH (opcjonalne, jeśli używasz uwierzytelniania kluczem)
- `--key`: Ścieżka do pliku klucza prywatnego SSH (opcjonalne)
- `--branch`: Gałąź repozytorium do sklonowania (opcjonalne, domyślnie main)
- `--port`: Port SSH (opcjonalne, domyślnie 22)
- `--no-deps`: Flaga wskazująca, aby nie instalować zależności systemowych (opcjonalne)

#### Przykład

```bash
infrash remote deploy --host 192.168.1.100 --user pi --password raspberry --repo https://github.com/username/myproject.git --branch develop
```

### Uruchamianie poleceń na zdalnych hostach

```bash
infrash remote run --host <adres_ip> --user <użytkownik> --command "<polecenie>" [--key <ścieżka_do_klucza>] [--password <hasło>] [--port <port>]
```

#### Parametry

- `--host`: Adres IP lub nazwa hosta urządzenia zdalnego (wymagane)
- `--user`: Nazwa użytkownika SSH (wymagane)
- `--command`: Polecenie do uruchomienia na zdalnym hoście (wymagane)
- `--password`: Hasło SSH (opcjonalne, jeśli używasz uwierzytelniania kluczem)
- `--key`: Ścieżka do pliku klucza prywatnego SSH (opcjonalne)
- `--port`: Port SSH (opcjonalne, domyślnie 22)

#### Przykład

```bash
infrash remote run --host 192.168.1.100 --user pi --password raspberry --command "ls -la /home/pi"
```

## Co robi moduł Remote

### Polecenie `deploy`

1. Nawiązuje połączenie SSH z hostem zdalnym używając podanych danych uwierzytelniających
2. Aktualizuje system zdalny używając `apt-get update` i instaluje wymagane zależności
3. Klonuje określone repozytorium Git lub aktualizuje istniejące
4. Tworzy środowisko wirtualne Python w sklonowanym repozytorium
5. Instaluje zależności Python z pliku requirements.txt repozytorium

### Polecenie `run`

1. Nawiązuje połączenie SSH z hostem zdalnym używając podanych danych uwierzytelniających
2. Wykonuje określone polecenie na zdalnym hoście
3. Zwraca wynik wykonania polecenia (standardowe wyjście i błędy)

## Logowanie

Wszystkie operacje są logowane zarówno do konsoli, jak i do pliku logów Infrash. Pozwala to na śledzenie procesu wdrażania i rozwiązywanie problemów w przypadku ich wystąpienia.

## Obsługa błędów i diagnostyka

Moduł remote zawiera kompleksową obsługę błędów i diagnostykę, aby wykrywać i raportować problemy podczas:
- Nawiązywania połączenia SSH
- Aktualizacji systemu
- Klonowania repozytorium
- Tworzenia środowiska wirtualnego
- Instalacji pakietów

W przypadku wystąpienia błędu, moduł automatycznie uruchamia diagnostykę, która:
1. Sprawdza połączenie sieciowe z hostem zdalnym
2. Weryfikuje dostępność wymaganych narzędzi (ssh, git)
3. Proponuje rozwiązania wykrytych problemów

## Integracja z innymi modułami Infrash

Moduł remote jest zintegrowany z innymi modułami Infrash, co pozwala na:
- Automatyczną diagnostykę i rozwiązywanie problemów
- Zarządzanie zależnościami
- Monitorowanie wdrożeń
- Integrację z systemami CI/CD

## Przykłady użycia w skryptach

### Przykład skryptu wdrożeniowego

```bash
#!/bin/bash
# Przykładowy skrypt wdrożeniowy używający Infrash Remote

# Wdróż aplikację na Raspberry Pi
infrash remote deploy --host 192.168.1.100 --user pi --password raspberry --repo https://github.com/username/myproject.git

# Uruchom aplikację na Raspberry Pi
infrash remote run --host 192.168.1.100 --user pi --password raspberry --command "cd myproject && source venv/bin/activate && python app.py"
```

### Przykład użycia w CI/CD (GitLab CI)

```yaml
deploy-to-raspberry:
  stage: deploy
  script:
    - pip install infrash
    - infrash remote deploy --host $RPI_HOST --user $RPI_USER --key $SSH_PRIVATE_KEY --repo $CI_REPOSITORY_URL --branch $CI_COMMIT_REF_NAME
  only:
    - main
```

## Rozwiązywanie problemów

### Problem: Nie można połączyć się z hostem zdalnym

**Rozwiązanie**: Sprawdź, czy:
- Host jest dostępny w sieci (ping)
- Usługa SSH jest uruchomiona na hoście
- Poświadczenia SSH są poprawne
- Port SSH jest otwarty w zaporze sieciowej

### Problem: Błąd podczas klonowania repozytorium

**Rozwiązanie**: Sprawdź, czy:
- URL repozytorium jest poprawny
- Masz uprawnienia do repozytorium
- Git jest zainstalowany na hoście zdalnym

### Problem: Błąd podczas instalacji zależności

**Rozwiązanie**: Sprawdź, czy:
- Plik requirements.txt istnieje w repozytorium
- Python i pip są zainstalowane na hoście zdalnym
- Masz wystarczające uprawnienia do instalacji pakietów

## Zaawansowane użycie

### Konfiguracja w pliku YAML

Możesz zdefiniować ustawienia dla zdalnych hostów w pliku konfiguracyjnym Infrash:

```yaml
remote:
  hosts:
    - name: raspberry-pi
      host: 192.168.1.100
      user: pi
      port: 22
    - name: dev-server
      host: dev.example.com
      user: developer
      port: 22
```

Następnie możesz używać nazw hostów zamiast adresów IP:

```bash
infrash remote deploy --host-name raspberry-pi --repo https://github.com/username/myproject.git
```

### Automatyzacja wdrożeń

Możesz zautomatyzować wdrożenia używając harmonogramów lub wyzwalaczy:

```bash
# Wdrażaj codziennie o północy
0 0 * * * infrash remote deploy --host 192.168.1.100 --user pi --key ~/.ssh/id_rsa --repo https://github.com/username/myproject.git
```

## Porównanie z poprzednią wersją (remote.py)

Nowa funkcjonalność `infrash remote` zastępuje i rozszerza możliwości wcześniejszego skryptu `remote.py`. Główne ulepszenia to:

1. Pełna integracja z CLI Infrash
2. Rozszerzona diagnostyka i obsługa błędów
3. Możliwość uruchamiania dowolnych poleceń na zdalnym hoście
4. Automatyczna instalacja brakujących zależności
5. Inteligentne wykrywanie i rozwiązywanie problemów
6. Lepsza integracja z systemami CI/CD
7. Wsparcie dla wielu zdalnych hostów i konfiguracji
