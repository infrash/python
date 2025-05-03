import os
import sys
import subprocess
import logging
import json
import platform
import shutil
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class GitRunner:
    """
    Klasa do pobierania, instalowania i uruchamiania projektów z repozytoriów Git.
    Obsługuje projekty: Python, Node.js, PHP, Ruby, Rust i statyczne HTML.
    """

    def __init__(self, working_dir: str = None):
        """
        Inicjalizacja GitRunnera.

        Args:
            working_dir: Folder roboczy (opcjonalnie)
        """
        self.working_dir = working_dir or os.path.join(os.path.expanduser("~"), "git_projects")
        os.makedirs(self.working_dir, exist_ok=True)

        # Wykrywanie dostępnych narzędzi
        self.available_tools = self._detect_tools()

    def _detect_tools(self) -> Dict[str, bool]:
        """Wykrywa dostępne narzędzia w systemie."""
        tools = {
            "git": self._is_command_available("git"),
            "python": self._is_command_available("python") or self._is_command_available("python3"),
            "pip": self._is_command_available("pip") or self._is_command_available("pip3"),
            "node": self._is_command_available("node"),
            "npm": self._is_command_available("npm"),
            "php": self._is_command_available("php"),
            "composer": self._is_command_available("composer"),
            "ruby": self._is_command_available("ruby"),
            "bundle": self._is_command_available("bundle"),
            "cargo": self._is_command_available("cargo"),
            "rustc": self._is_command_available("rustc")
        }
        return tools

    def _is_command_available(self, command: str) -> bool:
        """Sprawdza, czy polecenie jest dostępne w systemie."""
        try:
            subprocess.run(
                [command, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            return False

    def clone_repository(self, repo_url: str, target_dir: str = None) -> Tuple[bool, str]:
        """
        Klonuje repozytorium Git.

        Args:
            repo_url: URL repozytorium Git
            target_dir: Katalog docelowy (opcjonalnie)

        Returns:
            Tuple (success, path): Czy operacja się powiodła i ścieżka do sklonowanego repo
        """
        if not self.available_tools["git"]:
            logger.error("Git nie jest zainstalowany w systemie")
            return False, ""

        try:
            # Pobieramy nazwę repozytorium z URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")

            # Ustalamy katalog docelowy
            target_path = target_dir or os.path.join(self.working_dir, repo_name)

            # Sprawdzamy, czy katalog już istnieje
            if os.path.exists(target_path):
                logger.info(f"Repozytorium {repo_name} już istnieje, aktualizuję...")
                subprocess.run(
                    ["git", "pull"],
                    cwd=target_path,
                    check=True
                )
            else:
                logger.info(f"Klonuję repozytorium {repo_url}...")
                subprocess.run(
                    ["git", "clone", repo_url, target_path],
                    check=True
                )

            logger.info(f"Repozytorium zostało sklonowane do {target_path}")
            return True, target_path

        except subprocess.SubprocessError as e:
            logger.error(f"Błąd podczas klonowania repozytorium: {str(e)}")
            return False, ""

    def detect_project_type(self, project_path: str) -> List[str]:
        """
        Wykrywa typ projektu na podstawie zawartości folderu.

        Args:
            project_path: Ścieżka do projektu

        Returns:
            Lista typów projektu (python, node, php, ruby, rust, static)
        """
        project_types = []

        # Sprawdzamy Python
        if os.path.exists(os.path.join(project_path, "requirements.txt")) or \
                os.path.exists(os.path.join(project_path, "setup.py")) or \
                os.path.exists(os.path.join(project_path, "pyproject.toml")):
            project_types.append("python")

        # Sprawdzamy Node.js
        if os.path.exists(os.path.join(project_path, "package.json")):
            project_types.append("node")

        # Sprawdzamy PHP
        if os.path.exists(os.path.join(project_path, "composer.json")):
            project_types.append("php")
        elif any(f.endswith(".php") for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            project_types.append("php")

        # Sprawdzamy Ruby
        if os.path.exists(os.path.join(project_path, "Gemfile")):
            project_types.append("ruby")

        # Sprawdzamy Rust
        if os.path.exists(os.path.join(project_path, "Cargo.toml")):
            project_types.append("rust")

        # Sprawdzamy statyczne HTML
        if any(f.endswith((".html", ".htm")) for f in os.listdir(project_path) if
               os.path.isfile(os.path.join(project_path, f))):
            project_types.append("static")

        return project_types or ["unknown"]

    def install_dependencies(self, project_path: str, project_type: str) -> bool:
        """
        Instaluje zależności dla danego typu projektu.

        Args:
            project_path: Ścieżka do projektu
            project_type: Typ projektu (python, node, php, ruby, rust)

        Returns:
            Czy instalacja się powiodła
        """
        logger.info(f"Instalacja zależności dla projektu typu {project_type}...")

        try:
            if project_type == "python":
                if not self.available_tools["pip"]:
                    logger.error("Pip nie jest zainstalowany w systemie")
                    return False

                # Sprawdzamy, czy używamy virtualenv
                venv_path = os.path.join(project_path, "venv")
                if not os.path.exists(venv_path):
                    # Tworzymy virtualenv
                    if self.available_tools["python"]:
                        subprocess.run(
                            ["python", "-m", "venv", venv_path],
                            check=True
                        )

                # Ustalamy ścieżkę do interpretera Python
                python_cmd = os.path.join(venv_path, "bin", "python") if os.path.exists(venv_path) else "python"
                if platform.system() == "Windows" and os.path.exists(venv_path):
                    python_cmd = os.path.join(venv_path, "Scripts", "python.exe")

                # Instalujemy zależności
                if os.path.exists(os.path.join(project_path, "requirements.txt")):
                    subprocess.run(
                        [python_cmd, "-m", "pip", "install", "-r", "requirements.txt"],
                        cwd=project_path,
                        check=True
                    )
                elif os.path.exists(os.path.join(project_path, "setup.py")):
                    subprocess.run(
                        [python_cmd, "-m", "pip", "install", "-e", "."],
                        cwd=project_path,
                        check=True
                    )
                elif os.path.exists(os.path.join(project_path, "pyproject.toml")):
                    subprocess.run(
                        [python_cmd, "-m", "pip", "install", "-e", "."],
                        cwd=project_path,
                        check=True
                    )

            elif project_type == "node":
                if not self.available_tools["npm"]:
                    logger.error("NPM nie jest zainstalowany w systemie")
                    return False

                subprocess.run(
                    ["npm", "install"],
                    cwd=project_path,
                    check=True
                )

            elif project_type == "php":
                if os.path.exists(os.path.join(project_path, "composer.json")):
                    if not self.available_tools["composer"]:
                        logger.error("Composer nie jest zainstalowany w systemie")
                        return False

                    subprocess.run(
                        ["composer", "install"],
                        cwd=project_path,
                        check=True
                    )

            elif project_type == "ruby":
                if not self.available_tools["bundle"]:
                    logger.error("Bundler nie jest zainstalowany w systemie")
                    return False

                subprocess.run(
                    ["bundle", "install"],
                    cwd=project_path,
                    check=True
                )

            elif project_type == "rust":
                if not self.available_tools["cargo"]:
                    logger.error("Cargo nie jest zainstalowany w systemie")
                    return False

                subprocess.run(
                    ["cargo", "build"],
                    cwd=project_path,
                    check=True
                )

            return True

        except subprocess.SubprocessError as e:
            logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
            return False

    def setup_env_file(self, project_path: str) -> bool:
        """
        Konfiguruje plik .env, prosząc użytkownika o wprowadzenie wartości.

        Args:
            project_path: Ścieżka do projektu

        Returns:
            Czy konfiguracja się powiodła
        """
        env_example_paths = [
            os.path.join(project_path, ".env.example"),
            os.path.join(project_path, ".env.sample"),
            os.path.join(project_path, "env.example")
        ]

        env_file = os.path.join(project_path, ".env")

        # Sprawdzamy, czy .env już istnieje
        if os.path.exists(env_file):
            logger.info("Plik .env już istnieje")
            return True

        # Szukamy pliku przykładowego
        example_file = None
        for path in env_example_paths:
            if os.path.exists(path):
                example_file = path
                break

        if not example_file:
            logger.info("Nie znaleziono pliku .env.example")
            return True

        logger.info(f"Konfiguracja pliku .env na podstawie {os.path.basename(example_file)}")

        try:
            # Odczytujemy przykładowy plik
            with open(example_file, 'r') as f:
                env_content = f.read()

            # Tworzymy nowy plik .env
            with open(env_file, 'w') as f:
                for line in env_content.splitlines():
                    # Pomijamy komentarze i puste linie
                    if line.strip().startswith('#') or not line.strip():
                        f.write(line + '\n')
                        continue

                    # Sprawdzamy, czy linia zawiera zmienną
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()

                        # Pytamy użytkownika o wartość
                        user_value = input(f"Podaj wartość dla {key} [{value}]: ")

                        # Używamy wartości podanej przez użytkownika lub domyślnej
                        final_value = user_value if user_value else value
                        f.write(f"{key}={final_value}\n")
                    else:
                        f.write(line + '\n')

            logger.info("Plik .env został skonfigurowany")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji pliku .env: {str(e)}")
            return False

    def run_project(self, project_path: str, project_type: str, port: int = None) -> Tuple[
        bool, Optional[subprocess.Popen]]:
        """
        Uruchamia projekt.

        Args:
            project_path: Ścieżka do projektu
            project_type: Typ projektu (python, node, php, ruby, rust, static)
            port: Port na którym ma być uruchomiony projekt (opcjonalnie)

        Returns:
            Tuple (success, process): Czy uruchomienie się powiodło i obiekt procesu
        """
        logger.info(f"Uruchamianie projektu typu {project_type}...")

        try:
            if project_type == "python":
                # Sprawdzamy różne możliwe punkty wejścia
                entry_points = [
                    # Flask
                    ("app.py", ["python", "app.py"]),
                    ("wsgi.py", ["python", "wsgi.py"]),
                    ("main.py", ["python", "main.py"]),
                    # Django
                    ("manage.py", ["python", "manage.py", "runserver", f"0.0.0.0:{port or 8000}"]),
                    # FastAPI
                    ("main.py", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port or 8000)])
                ]

                for file_name, command in entry_points:
                    if os.path.exists(os.path.join(project_path, file_name)):
                        # Sprawdzamy czy używamy virtualenv
                        venv_path = os.path.join(project_path, "venv")
                        if os.path.exists(venv_path):
                            if platform.system() == "Windows":
                                python_path = os.path.join(venv_path, "Scripts", "python.exe")
                                if "python" in command[0]:
                                    command[0] = python_path
                            else:
                                python_path = os.path.join(venv_path, "bin", "python")
                                if "python" in command[0]:
                                    command[0] = python_path
                                elif command[0] in ["uvicorn"]:
                                    command[0] = os.path.join(venv_path, "bin", command[0])

                        # Dodajemy port, jeśli podano i nie jest już w poleceniu
                        if port and "--port" not in command and "runserver" not in command:
                            command.extend(["--port", str(port)])

                        process = subprocess.Popen(
                            command,
                            cwd=project_path
                        )
                        logger.info(f"Uruchomiono aplikację Python: {' '.join(command)}")
                        return True, process

                logger.error("Nie znaleziono punktu wejścia dla aplikacji Python")
                return False, None

            elif project_type == "node":
                # Sprawdzamy package.json
                package_json_path = os.path.join(project_path, "package.json")
                if os.path.exists(package_json_path):
                    with open(package_json_path, 'r') as f:
                        package_data = json.load(f)

                    # Sprawdzamy skrypty
                    if "scripts" in package_data:
                        if "start" in package_data["scripts"]:
                            process = subprocess.Popen(
                                ["npm", "start"],
                                cwd=project_path
                            )
                            logger.info("Uruchomiono aplikację Node.js: npm start")
                            return True, process
                        elif "dev" in package_data["scripts"]:
                            process = subprocess.Popen(
                                ["npm", "run", "dev"],
                                cwd=project_path
                            )
                            logger.info("Uruchomiono aplikację Node.js: npm run dev")
                            return True, process

                # Sprawdzamy app.js lub server.js
                entry_points = ["app.js", "server.js", "index.js"]
                for entry_point in entry_points:
                    if os.path.exists(os.path.join(project_path, entry_point)):
                        process = subprocess.Popen(
                            ["node", entry_point],
                            cwd=project_path
                        )
                        logger.info(f"Uruchomiono aplikację Node.js: node {entry_point}")
                        return True, process

                logger.error("Nie znaleziono punktu wejścia dla aplikacji Node.js")
                return False, None

            elif project_type == "php":
                # Sprawdzamy czy to projekt Laravel
                if os.path.exists(os.path.join(project_path, "artisan")):
                    process = subprocess.Popen(
                        ["php", "artisan", "serve", f"--port={port or 8000}", "--host=0.0.0.0"],
                        cwd=project_path
                    )
                    logger.info("Uruchomiono aplikację Laravel")
                    return True, process
                # Wbudowany serwer PHP
                else:
                    public_dir = os.path.join(project_path, "public")
                    serve_dir = public_dir if os.path.exists(public_dir) else project_path
                    process = subprocess.Popen(
                        ["php", "-S", f"0.0.0.0:{port or 8000}"],
                        cwd=serve_dir
                    )
                    logger.info(f"Uruchomiono wbudowany serwer PHP w katalogu {serve_dir}")
                    return True, process

            elif project_type == "ruby":
                # Sprawdzamy czy to projekt Rails
                if os.path.exists(os.path.join(project_path, "bin", "rails")):
                    process = subprocess.Popen(
                        ["bundle", "exec", "rails", "server", "-p", str(port or 3000), "-b", "0.0.0.0"],
                        cwd=project_path
                    )
                    logger.info("Uruchomiono aplikację Ruby on Rails")
                    return True, process
                # Sprawdzamy czy to Sinatra
                elif any(os.path.exists(os.path.join(project_path, f)) for f in ["app.rb", "config.ru"]):
                    process = subprocess.Popen(
                        ["bundle", "exec", "rackup", "-p", str(port or 9292), "-o", "0.0.0.0"],
                        cwd=project_path
                    )
                    logger.info("Uruchomiono aplikację Ruby/Rack")
                    return True, process

                logger.error("Nie znaleziono punktu wejścia dla aplikacji Ruby")
                return False, None

            elif project_type == "rust":
                # Kompilujemy projekt
                subprocess.run(
                    ["cargo", "build", "--release"],
                    cwd=project_path,
                    check=True
                )

                # Sprawdzamy Cargo.toml aby znaleźć nazwę binarki
                with open(os.path.join(project_path, "Cargo.toml"), 'r') as f:
                    cargo_content = f.read()

                binary_name = None
                match = re.search(r'name\s*=\s*"([^"]+)"', cargo_content)
                if match:
                    binary_name = match.group(1)

                if binary_name:
                    binary_path = os.path.join(project_path, "target", "release", binary_name)
                    if platform.system() == "Windows":
                        binary_path += ".exe"

                    if os.path.exists(binary_path):
                        process = subprocess.Popen(
                            [binary_path],
                            cwd=project_path
                        )
                        logger.info(f"Uruchomiono aplikację Rust: {binary_path}")
                        return True, process

                logger.error("Nie znaleziono skompilowanej aplikacji Rust")
                return False, None

            elif project_type == "static":
                # Uruchamiamy prosty serwer HTTP
                if self.available_tools["python"]:
                    process = subprocess.Popen(
                        ["python", "-m", "http.server", str(port or 8000)],
                        cwd=project_path
                    )
                    logger.info(f"Uruchomiono serwer HTTP na porcie {port or 8000}")
                    return True, process
                else:
                    logger.error("Nie znaleziono Pythona do uruchomienia serwera HTTP")
                    return False, None

            logger.error(f"Nieobsługiwany typ projektu: {project_type}")
            return False, None

        except subprocess.SubprocessError as e:
            logger.error(f"Błąd podczas uruchamiania projektu: {str(e)}")
            return False, None

    def process_project(self, repo_url: str, target_dir: str = None, port: int = None) -> Tuple[
        bool, Optional[subprocess.Popen]]:
        """
        Pobiera, instaluje i uruchamia projekt z repozytorium Git.

        Args:
            repo_url: URL repozytorium Git
            target_dir: Katalog docelowy (opcjonalnie)
            port: Port na którym ma być uruchomiony projekt (opcjonalnie)

        Returns:
            Tuple (success, process): Czy operacja się powiodła i obiekt procesu
        """
        # Klonujemy repozytorium
        success, project_path = self.clone_repository(repo_url, target_dir)
        if not success:
            return False, None

        # Wykrywamy typ projektu
        project_types = self.detect_project_type(project_path)
        logger.info(f"Wykryte typy projektu: {', '.join(project_types)}")

        if "unknown" in project_types:
            logger.error("Nie udało się wykryć typu projektu")
            return False, None

        # Konfigurujemy plik .env
        self.setup_env_file(project_path)

        # Instalujemy zależności dla każdego wykrytego typu projektu
        for project_type in project_types:
            if project_type != "static":  # Statyczne strony nie mają zależności
                if not self.install_dependencies(project_path, project_type):
                    logger.warning(f"Instalacja zależności dla typu {project_type} nie powiodła się")

        # Uruchamiamy projekt (priorytet: web-aplikacje)
        for project_type in ["python", "node", "php", "ruby", "rust", "static"]:
            if project_type in project_types:
                success, process = self.run_project(project_path, project_type, port)
                if success:
                    return True, process

        logger.error("Nie udało się uruchomić żadnego obsługiwanego typu projektu")
        return False, None