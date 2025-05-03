
"""
Moduł zarządzania zależnościami. Służy do sprawdzania i instalowania
zależności systemowych i pakietów Python.
"""

import os
import sys
import subprocess
import platform
import re
import time
from typing import Dict, List, Any, Optional, Union

# Try to import critical dependencies, install them if missing
try:
    import importlib
    import pkg_resources
except ImportError as e:
    # Get the missing module name from the error message
    missing_module = str(e).split("'")[-2] if "'" in str(e) else str(e).split()[-1]
    print(f"Critical dependency missing: {missing_module}. Attempting to install...")
    
    try:
        # Install the missing dependency
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                              "setuptools" if missing_module == "pkg_resources" else missing_module])
        
        # Retry the import after installation
        if missing_module == "pkg_resources":
            import pkg_resources
        elif missing_module == "importlib":
            import importlib
        
        print(f"Successfully installed missing dependency: {missing_module}")
    except Exception as install_error:
        print(f"Failed to install missing dependency: {missing_module}. Error: {install_error}")
        # Continue execution, the error will be properly logged later

from infrash.utils.logger import get_logger
from infrash.system.os_detect import detect_os, get_package_manager, is_admin
from infrash.system.dependency_resolver import DependencyResolver

# Inicjalizacja loggera
logger = get_logger(__name__)

# Inicjalizacja resolwera zależności
dependency_resolver = DependencyResolver()

def ensure_critical_dependencies():
    """
    Sprawdza i instaluje krytyczne zależności wymagane do działania Infrash.
    
    Ta funkcja jest wywoływana automatycznie przy starcie, aby zapewnić,
    że wszystkie niezbędne zależności są dostępne.
    
    Returns:
        bool: True jeśli wszystkie krytyczne zależności są dostępne lub zostały zainstalowane,
              False w przypadku niepowodzenia.
    """
    critical_packages = [
        "setuptools",  # Zawiera pkg_resources
        "wheel",
        "pip",
        "requests"
    ]
    
    success = True
    for package in critical_packages:
        try:
            if package == "setuptools":
                # Specjalny przypadek dla pkg_resources
                try:
                    import pkg_resources
                except ImportError:
                    logger.warning(f"Brak krytycznej zależności: pkg_resources (setuptools). Instalowanie...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
                        import pkg_resources  # Próba ponownego importu
                        logger.info("Pomyślnie zainstalowano setuptools (pkg_resources)")
                    except Exception as e:
                        logger.error(f"Nie udało się zainstalować setuptools: {e}")
                        success = False
            else:
                # Standardowa weryfikacja dla innych pakietów
                try:
                    __import__(package)
                except ImportError:
                    logger.warning(f"Brak krytycznej zależności: {package}. Instalowanie...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                        __import__(package)  # Próba ponownego importu
                        logger.info(f"Pomyślnie zainstalowano {package}")
                    except Exception as e:
                        logger.error(f"Nie udało się zainstalować {package}: {e}")
                        success = False
        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji zależności {package}: {e}")
            success = False
    
    return success

# Wywołanie funkcji zapewniającej krytyczne zależności przy importowaniu modułu
ensure_critical_dependencies()

def check_dependencies(path: str = ".") -> List[str]:
    """
    Sprawdza brakujące zależności.

    Args:
        path: Ścieżka do projektu.

    Returns:
        Lista brakujących zależności.
    """
    missing_deps = []

    # Sprawdzamy, czy istnieją pliki z zależnościami
    requirements_files = [
        os.path.join(path, "requirements.txt"),
        os.path.join(path, "pyproject.toml"),
        os.path.join(path, "setup.py"),
        os.path.join(path, "setup.cfg")
    ]

    # Sprawdzamy plik requirements.txt
    if os.path.isfile(requirements_files[0]):
        missing_deps.extend(_check_requirements_txt(requirements_files[0]))

    # Sprawdzamy plik pyproject.toml
    if os.path.isfile(requirements_files[1]):
        missing_deps.extend(_check_pyproject_toml(requirements_files[1]))

    # Sprawdzamy plik setup.py
    if os.path.isfile(requirements_files[2]):
        missing_deps.extend(_check_setup_py(requirements_files[2]))

    # Sprawdzamy plik setup.cfg
    if os.path.isfile(requirements_files[3]):
        missing_deps.extend(_check_setup_cfg(requirements_files[3]))

    # Sprawdzamy podstawowe systemowe zależności
    system_deps = _check_system_dependencies()
    missing_deps.extend(system_deps)

    # Usuwamy duplikaty i zwracamy listę
    return list(set(missing_deps))

def _check_requirements_txt(file_path: str) -> List[str]:
    """
    Sprawdza brakujące zależności z pliku requirements.txt.

    Args:
        file_path: Ścieżka do pliku requirements.txt.

    Returns:
        Lista brakujących zależności.
    """
    missing_deps = []

    try:
        # Odczytujemy plik requirements.txt
        with open(file_path, "r") as f:
            requirements = f.readlines()

        # Przetwarzamy każdą linię
        for req in requirements:
            # Pomijamy komentarze i puste linie
            req = req.strip()
            if not req or req.startswith("#"):
                continue

            # Pomijamy opcje edytowalne (np. -e .)
            if req.startswith("-e") or req.startswith("--editable"):
                continue

            # Pomijamy URL do plików (np. https://example.com/file.tar.gz)
            if req.startswith("http://") or req.startswith("https://") or req.startswith("git+"):
                continue

            # Usuwamy komentarze z linii
            req = req.split("#")[0].strip()

            # Wyodrębniamy nazwę pakietu i wersję
            match = re.match(r"([^<>=!~]+).*", req)
            if match:
                package_name = match.group(1).strip()

                # Sprawdzamy, czy pakiet jest zainstalowany
                if not _is_package_installed(package_name):
                    missing_deps.append(package_name)
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania zależności w {file_path}: {str(e)}")

    return missing_deps

def _check_pyproject_toml(file_path: str) -> List[str]:
    """
    Sprawdza brakujące zależności z pliku pyproject.toml.

    Args:
        file_path: Ścieżka do pliku pyproject.toml.

    Returns:
        Lista brakujących zależności.
    """
    missing_deps = []

    try:
        # Odczytujemy plik pyproject.toml
        with open(file_path, "r") as f:
            content = f.read()

        # Szukamy sekcji z zależnościami
        dependencies_section = re.search(r"(?:dependencies|requires)\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if not dependencies_section:
            return missing_deps

        # Przetwarzamy każdą zależność
        dependencies = dependencies_section.group(1)
        for dep in re.finditer(r'"([^"]+)"', dependencies):
            package_name = dep.group(1).strip()

            # Usuwamy wersję z nazwy pakietu
            match = re.match(r"([^<>=!~]+).*", package_name)
            if match:
                package_name = match.group(1).strip()

                # Sprawdzamy, czy pakiet jest zainstalowany
                if not _is_package_installed(package_name):
                    missing_deps.append(package_name)
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania zależności w {file_path}: {str(e)}")

    return missing_deps

def _check_setup_py(file_path: str) -> List[str]:
    """
    Sprawdza brakujące zależności z pliku setup.py.

    Args:
        file_path: Ścieżka do pliku setup.py.

    Returns:
        Lista brakujących zależności.
    """
    missing_deps = []

    try:
        # Odczytujemy plik setup.py
        with open(file_path, "r") as f:
            content = f.read()

        # Szukamy sekcji z zależnościami
        dependencies_section = re.search(r"(?:install_requires|requires)\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if not dependencies_section:
            return missing_deps

        # Przetwarzamy każdą zależność
        dependencies = dependencies_section.group(1)
        for dep in re.finditer(r"'([^']+)'|\"([^\"]+)\"", dependencies):
            package_name = dep.group(1) if dep.group(1) else dep.group(2)

            # Usuwamy wersję z nazwy pakietu
            match = re.match(r"([^<>=!~]+).*", package_name)
            if match:
                package_name = match.group(1).strip()

                # Sprawdzamy, czy pakiet jest zainstalowany
                if not _is_package_installed(package_name):
                    missing_deps.append(package_name)
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania zależności w {file_path}: {str(e)}")

    return missing_deps

def _check_setup_cfg(file_path: str) -> List[str]:
    """
    Sprawdza brakujące zależności z pliku setup.cfg.

    Args:
        file_path: Ścieżka do pliku setup.cfg.

    Returns:
        Lista brakujących zależności.
    """
    missing_deps = []

    try:
        # Odczytujemy plik setup.cfg
        with open(file_path, "r") as f:
            content = f.read()

        # Szukamy sekcji z zależnościami
        dependencies_section = re.search(r"(?:install_requires|requires)\s*=(.*?)(?:\n\n|\n\[)", content, re.DOTALL)
        if not dependencies_section:
            return missing_deps

        # Przetwarzamy każdą zależność
        dependencies = dependencies_section.group(1)
        for dep in dependencies.splitlines():
            dep = dep.strip()
            if not dep:
                continue

            # Usuwamy wersję z nazwy pakietu
            match = re.match(r"([^<>=!~]+).*", dep)
            if match:
                package_name = match.group(1).strip()

                # Sprawdzamy, czy pakiet jest zainstalowany
                if not _is_package_installed(package_name):
                    missing_deps.append(package_name)
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania zależności w {file_path}: {str(e)}")

    return missing_deps

def _check_system_dependencies() -> List[str]:
    """
    Sprawdza brakujące zależności systemowe.

    Returns:
        Lista brakujących zależności systemowych.
    """
    missing_deps = []

    # Wykrywamy system operacyjny
    os_info = detect_os()
    os_type = os_info.get("type", "").lower()

    # Sprawdzamy różne zależności systemowe w zależności od systemu
    if "linux" in os_type:
        # Sprawdzamy podstawowe narzędzia
        tools = ["git", "curl", "wget", "ssh"]

        for tool in tools:
            if not _is_command_available(tool):
                if os_type in ["debian", "ubuntu"]:
                    missing_deps.append(tool)
                elif os_type in ["fedora", "centos", "rhel"]:
                    missing_deps.append(tool)
                elif os_type == "arch":
                    missing_deps.append(tool)
                elif os_type == "alpine":
                    missing_deps.append(tool)

        # Jeśli to Raspberry Pi, sprawdzamy dodatkowe zależności
        if "raspberry" in os_type or _is_raspberry_pi():
            rpi_tools = ["raspi-config", "rpi-update"]
            for tool in rpi_tools:
                if not _is_command_available(tool):
                    missing_deps.append(tool)

    elif os_type == "macos":
        # Sprawdzamy, czy zainstalowano Homebrew
        if not _is_command_available("brew"):
            missing_deps.append("homebrew")

        # Sprawdzamy podstawowe narzędzia
        tools = ["git", "curl", "wget", "ssh"]

        for tool in tools:
            if not _is_command_available(tool):
                missing_deps.append(tool)

    elif os_type == "windows":
        # Sprawdzamy, czy zainstalowano Chocolatey lub winget
        if not _is_command_available("choco") and not _is_command_available("winget"):
            missing_deps.append("chocolatey")

        # Sprawdzamy podstawowe narzędzia
        tools = ["git", "curl", "ssh"]

        for tool in tools:
            if not _is_command_available(tool):
                missing_deps.append(tool)

    return missing_deps

def _is_package_installed(package_name: str) -> bool:
    """
    Sprawdza, czy pakiet Python jest zainstalowany.

    Args:
        package_name: Nazwa pakietu.

    Returns:
        True, jeśli pakiet jest zainstalowany, False w przeciwnym razie.
    """
    try:
        # Normalizujemy nazwę pakietu
        package_name = package_name.lower().replace("-", "_")

        # Próbujemy zaimportować pakiet
        importlib.import_module(package_name)
        return True
    except ImportError:
        try:
            # Jeśli import nie działa, sprawdzamy przez pkg_resources
            pkg_resources.get_distribution(package_name)
            return True
        except pkg_resources.DistributionNotFound:
            return False
        except Exception:
            return False
    except Exception:
        return False

def _is_command_available(command: str) -> bool:
    """
    Sprawdza, czy polecenie jest dostępne w systemie.

    Args:
        command: Nazwa polecenia.

    Returns:
        True, jeśli polecenie jest dostępne, False w przeciwnym razie.
    """
    try:
        # Sprawdzamy, czy polecenie jest dostępne
        if platform.system() == "Windows":
            # W Windows używamy where
            process = subprocess.run(
                ["where", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        else:
            # W Unix używamy which
            process = subprocess.run(
                ["which", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

        return process.returncode == 0
    except Exception:
        return False

def _is_raspberry_pi() -> bool:
    """
    Sprawdza, czy system działa na Raspberry Pi.

    Returns:
        True, jeśli system działa na Raspberry Pi, False w przeciwnym razie.
    """
    try:
        # Sprawdzamy, czy istnieje plik /proc/cpuinfo
        if not os.path.isfile("/proc/cpuinfo"):
            return False

        # Odczytujemy zawartość pliku /proc/cpuinfo
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()

        # Sprawdzamy, czy zawiera informacje o procesorze Broadcom używanym w Raspberry Pi
        return any(processor in cpuinfo for processor in ["BCM2708", "BCM2709", "BCM2711", "BCM2835", "BCM2836", "BCM2837"])
    except Exception:
        return False

def install_dependency(package_name: str, package_manager: Optional[str] = None) -> bool:
    """
    Instaluje zależność.

    Args:
        package_name: Nazwa pakietu.
        package_manager: Nazwa menedżera pakietów (opcjonalne).

    Returns:
        True, jeśli pakiet został zainstalowany pomyślnie, False w przeciwnym razie.
    """
    # Jeśli nie podano menedżera pakietów, używamy domyślnego
    if not package_manager:
        package_manager = get_package_manager()

    logger.info(f"Instalowanie pakietu {package_name} za pomocą {package_manager}...")

    try:
        # Instalujemy pakiet w zależności od menedżera pakietów
        if package_manager == "pip":
            # Używamy pip do instalacji pakietu Python
            cmd = [sys.executable, "-m", "pip", "install", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager in ["apt-get", "apt"]:
            # Używamy apt-get/apt do instalacji pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Instalacja pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", package_manager, "install", "-y", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = [package_manager, "install", "-y", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager in ["yum", "dnf"]:
            # Używamy yum/dnf do instalacji pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Instalacja pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", package_manager, "install", "-y", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = [package_manager, "install", "-y", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager == "pacman":
            # Używamy pacman do instalacji pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Instalacja pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", "pacman", "-S", "--noconfirm", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = ["pacman", "-S", "--noconfirm", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager == "apk":
            # Używamy apk do instalacji pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Instalacja pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", "apk", "add", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = ["apk", "add", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager == "brew":
            # Używamy brew do instalacji pakietu systemowego (macOS)
            cmd = ["brew", "install", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager == "choco":
            # Używamy chocolatey do instalacji pakietu systemowego (Windows)
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                logger.warning(f"Instalacja pakietu {package_name} wymaga uprawnień administratora.")

                # W Windows nie możemy użyć sudo, więc zwracamy błąd
                logger.error("Brak uprawnień administratora. Uruchom ponownie z uprawnieniami administratora.")
                return False

            cmd = ["choco", "install", package_name, "-y"]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        elif package_manager == "winget":
            # Używamy winget do instalacji pakietu systemowego (Windows)
            cmd = ["winget", "install", "-e", "--id", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas instalacji {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został zainstalowany pomyślnie.")
            return True

        else:
            logger.error(f"Nieznany menedżer pakietów: {package_manager}")
            return False

    except Exception as e:
        logger.error(f"Błąd podczas instalacji pakietu {package_name}: {str(e)}")
        return False

def uninstall_dependency(package_name: str, package_manager: Optional[str] = None) -> bool:
    """
    Odinstalowuje zależność.

    Args:
        package_name: Nazwa pakietu.
        package_manager: Nazwa menedżera pakietów (opcjonalne).

    Returns:
        True, jeśli pakiet został odinstalowany pomyślnie, False w przeciwnym razie.
    """
    # Jeśli nie podano menedżera pakietów, używamy domyślnego
    if not package_manager:
        package_manager = get_package_manager()

    logger.info(f"Odinstalowywanie pakietu {package_name} za pomocą {package_manager}...")

    try:
        # Odinstalowujemy pakiet w zależności od menedżera pakietów
        if package_manager == "pip":
            # Używamy pip do odinstalowania pakietu Python
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager in ["apt-get", "apt"]:
            # Używamy apt-get/apt do odinstalowania pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Odinstalowanie pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", package_manager, "remove", "-y", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = [package_manager, "remove", "-y", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager in ["yum", "dnf"]:
            # Używamy yum/dnf do odinstalowania pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Odinstalowanie pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", package_manager, "remove", "-y", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = [package_manager, "remove", "-y", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager == "pacman":
            # Używamy pacman do odinstalowania pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Odinstalowanie pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", "pacman", "-R", "--noconfirm", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = ["pacman", "-R", "--noconfirm", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager == "apk":
            # Używamy apk do odinstalowania pakietu systemowego
            # Sprawdzamy, czy mamy uprawnienia roota
            if not is_admin():
                logger.warning(f"Odinstalowanie pakietu {package_name} wymaga uprawnień administratora.")

                # Próbujemy użyć sudo
                if _is_command_available("sudo"):
                    cmd = ["sudo", "apk", "del", package_name]
                else:
                    logger.error("Brak uprawnień administratora i brak polecenia sudo.")
                    return False
            else:
                cmd = ["apk", "del", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager == "brew":
            # Używamy brew do odinstalowania pakietu systemowego (macOS)
            cmd = ["brew", "uninstall", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager == "choco":
            # Używamy chocolatey do odinstalowania pakietu systemowego (Windows)
            # Sprawdzamy, czy mamy uprawnienia administratora
            if not is_admin():
                logger.warning(f"Odinstalowanie pakietu {package_name} wymaga uprawnień administratora.")

                # W Windows nie możemy użyć sudo, więc zwracamy błąd
                logger.error("Brak uprawnień administratora. Uruchom ponownie z uprawnieniami administratora.")
                return False

            cmd = ["choco", "uninstall", package_name, "-y"]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        elif package_manager == "winget":
            # Używamy winget do odinstalowania pakietu systemowego (Windows)
            cmd = ["winget", "uninstall", "-e", "--id", package_name]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode != 0:
                logger.error(f"Błąd podczas odinstalowywania {package_name}: {process.stderr}")
                return False

            logger.info(f"Pakiet {package_name} został odinstalowany pomyślnie.")
            return True

        else:
            logger.error(f"Nieznany menedżer pakietów: {package_manager}")
            return False

    except Exception as e:
        logger.error(f"Błąd podczas odinstalowywania pakietu {package_name}: {str(e)}")
        return False

def install_dependencies(dependencies: List[str], force: bool = False) -> bool:
    """
    Instaluje listę zależności.

    Args:
        dependencies: Lista zależności do zainstalowania.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    logger.info(f"Instalowanie {len(dependencies)} zależności...")
    
    success = True
    for dep in dependencies:
        logger.info(f"Instalowanie zależności: {dep}")
        if not install_dependency(dep):
            logger.error(f"Nie udało się zainstalować zależności: {dep}")
            success = False
    
    return success

def install_dependencies_from_file(file_path: str, force: bool = False) -> bool:
    """
    Instaluje zależności z pliku.

    Args:
        file_path: Ścieżka do pliku z zależnościami.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    if not os.path.isfile(file_path):
        logger.error(f"Plik {file_path} nie istnieje.")
        return False

    # Wybieramy odpowiednią funkcję w zależności od typu pliku
    if file_path.endswith(".txt"):
        return _install_from_requirements_txt(file_path, force)
    elif file_path.endswith(".toml"):
        return _install_from_pyproject_toml(file_path, force)
    elif file_path.endswith(".py"):
        return _install_from_setup_py(file_path, force)
    elif file_path.endswith(".cfg"):
        return _install_from_setup_cfg(file_path, force)
    else:
        logger.error(f"Nieobsługiwany typ pliku: {file_path}")
        return False

def _install_from_requirements_txt(file_path: str, force: bool = False) -> bool:
    """
    Instaluje zależności z pliku requirements.txt.

    Args:
        file_path: Ścieżka do pliku requirements.txt.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    try:
        # Najpierw aktualizuj pip
        dependency_resolver.update_pip()
        
        # Przetwórz plik requirements.txt
        success, processed_file = dependency_resolver.process_requirements_file(file_path)
        
        if not success:
            logger.warning(f"Nie udało się przetworzyć pliku {file_path}, używanie oryginalnego pliku.")
            processed_file = file_path
        
        # Używamy pip do instalacji zależności
        cmd = [sys.executable, "-m", "pip", "install"]

        # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
        if force:
            cmd.append("--force-reinstall")

        # Dodajemy opcję -r i ścieżkę do pliku
        cmd.extend(["-r", processed_file])

        # Instalacja z obsługą ponownych prób
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                if process.returncode == 0:
                    logger.info(f"Wszystkie zależności z {file_path} zostały zainstalowane pomyślnie (próba {attempt+1}/{max_retries}).")
                    return True
                else:
                    logger.error(f"Błąd podczas instalacji zależności z {file_path} (próba {attempt+1}/{max_retries}): {process.stderr}")
            except Exception as e:
                logger.error(f"Błąd podczas instalacji zależności z {file_path} (próba {attempt+1}/{max_retries}): {str(e)}")
            
            # Jeśli to nie ostatnia próba, poczekaj przed kolejną
            if attempt < max_retries - 1:
                logger.info(f"Ponowna próba za {retry_delay} sekund...")
                time.sleep(retry_delay)
        
        logger.error(f"Nie udało się zainstalować zależności z {file_path} po {max_retries} próbach.")
        return False

    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
        return False

def _install_from_pyproject_toml(file_path: str, force: bool = False) -> bool:
    """
    Instaluje zależności z pliku pyproject.toml.

    Args:
        file_path: Ścieżka do pliku pyproject.toml.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    try:
        # Używamy pip do instalacji projektu w trybie deweloperskim
        cmd = [sys.executable, "-m", "pip", "install"]

        # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
        if force:
            cmd.append("--force-reinstall")

        # Dodajemy opcję -e i ścieżkę do katalogu projektu
        directory = os.path.dirname(file_path)
        cmd.extend(["-e", directory])

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
            return False

        logger.info(f"Wszystkie zależności z {file_path} zostały zainstalowane pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
        return False

def _install_from_setup_py(file_path: str, force: bool = False) -> bool:
    """
    Instaluje zależności z pliku setup.py.

    Args:
        file_path: Ścieżka do pliku setup.py.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    try:
        # Używamy pip do instalacji projektu w trybie deweloperskim
        cmd = [sys.executable, "-m", "pip", "install"]

        # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
        if force:
            cmd.append("--force-reinstall")

        # Dodajemy opcję -e i ścieżkę do katalogu projektu
        directory = os.path.dirname(file_path)
        cmd.extend(["-e", directory])

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
            return False

        logger.info(f"Wszystkie zależności z {file_path} zostały zainstalowane pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
        return False

def _install_from_setup_cfg(file_path: str, force: bool = False) -> bool:
    """
    Instaluje zależności z pliku setup.cfg.

    Args:
        file_path: Ścieżka do pliku setup.cfg.
        force: Czy wymusić reinstalację istniejących zależności.

    Returns:
        True, jeśli wszystkie zależności zostały zainstalowane pomyślnie, False w przeciwnym razie.
    """
    try:
        # Używamy pip do instalacji projektu w trybie deweloperskim
        cmd = [sys.executable, "-m", "pip", "install"]

        # Dodajemy opcję --force-reinstall, jeśli wybrano wymuszenie
        if force:
            cmd.append("--force-reinstall")

        # Dodajemy opcję -e i ścieżkę do katalogu projektu
        directory = os.path.dirname(file_path)
        cmd.extend(["-e", directory])

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            logger.error(f"Błąd podczas instalacji zależności z {file_path}: {process.stderr}")
            return False

        logger.info(f"Wszystkie zależności z {file_path} zostały zainstalowane pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności z {file_path}: {str(e)}")
        return False

def create_virtual_env(path: str, python_version: Optional[str] = None) -> bool:
    """
    Tworzy wirtualne środowisko Pythona.

    Args:
        path: Ścieżka do katalogu, w którym ma zostać utworzone wirtualne środowisko.
        python_version: Wersja Pythona (opcjonalne).

    Returns:
        True, jeśli wirtualne środowisko zostało utworzone pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Tworzenie wirtualnego środowiska w {path}...")

        # Sprawdzamy, czy mamy zainstalowany moduł venv
        try:
            import venv
        except ImportError:
            logger.error("Brak modułu venv. Instaluję...")

            # Instalujemy moduł venv
            cmd_install = [sys.executable, "-m", "pip", "install", "virtualenv"]

            process_install = subprocess.run(
                cmd_install,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process_install.returncode != 0:
                logger.error(f"Błąd podczas instalacji modułu virtualenv: {process_install.stderr}")
                return False

        # Tworzymy wirtualne środowisko
        if python_version:
            # Używamy określonej wersji Pythona
            cmd = ["virtualenv", "-p", f"python{python_version}", path]
        else:
            # Używamy bieżącej wersji Pythona
            cmd = ["virtualenv", path]

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            logger.error(f"Błąd podczas tworzenia wirtualnego środowiska: {process.stderr}")
            return False

        logger.info(f"Wirtualne środowisko zostało utworzone pomyślnie w {path}.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia wirtualnego środowiska: {str(e)}")
        return False

def activate_virtual_env(path: str) -> bool:
    """
    Aktywuje wirtualne środowisko Pythona w bieżącym procesie.

    Args:
        path: Ścieżka do katalogu z wirtualnym środowiskiem.

    Returns:
        True, jeśli wirtualne środowisko zostało aktywowane pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Aktywowanie wirtualnego środowiska w {path}...")

        # Sprawdzamy system operacyjny
        if platform.system() == "Windows":
            # Windows
            activate_script = os.path.join(path, "Scripts", "activate.bat")
        else:
            # Unix
            activate_script = os.path.join(path, "bin", "activate")

        # Sprawdzamy, czy skrypt aktywacyjny istnieje
        if not os.path.isfile(activate_script):
            logger.error(f"Brak skryptu aktywacyjnego: {activate_script}")
            return False

        # Aktywujemy wirtualne środowisko
        if platform.system() == "Windows":
            # Windows - aktywujemy przez modyfikację zmiennych środowiskowych
            bin_dir = os.path.join(path, "Scripts")

            # Modyfikujemy PATH
            os.environ["PATH"] = f"{bin_dir};{os.environ.get('PATH', '')}"

            # Modyfikujemy VIRTUAL_ENV
            os.environ["VIRTUAL_ENV"] = path

            # Usuwamy PYTHONHOME, jeśli istnieje
            if "PYTHONHOME" in os.environ:
                del os.environ["PYTHONHOME"]
        else:
            # Unix - aktywujemy przez modyfikację zmiennych środowiskowych
            bin_dir = os.path.join(path, "bin")

            # Modyfikujemy PATH
            os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"

            # Modyfikujemy VIRTUAL_ENV
            os.environ["VIRTUAL_ENV"] = path

            # Usuwamy PYTHONHOME, jeśli istnieje
            if "PYTHONHOME" in os.environ:
                del os.environ["PYTHONHOME"]

        logger.info(f"Wirtualne środowisko zostało aktywowane pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas aktywowania wirtualnego środowiska: {str(e)}")
        return False

def run_script_in_virtual_env(venv_path: str, script_path: str, args: Optional[List[str]] = None) -> bool:
    """
    Uruchamia skrypt Python w wirtualnym środowisku.

    Args:
        venv_path: Ścieżka do katalogu z wirtualnym środowiskiem.
        script_path: Ścieżka do skryptu Python.
        args: Lista argumentów dla skryptu (opcjonalne).

    Returns:
        True, jeśli skrypt został uruchomiony pomyślnie, False w przeciwnym razie.
    """
    try:
        logger.info(f"Uruchamianie skryptu {script_path} w wirtualnym środowisku {venv_path}...")

        # Sprawdzamy system operacyjny
        if platform.system() == "Windows":
            # Windows
            python_executable = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            # Unix
            python_executable = os.path.join(venv_path, "bin", "python")

        # Sprawdzamy, czy interpreter Pythona istnieje
        if not os.path.isfile(python_executable):
            logger.error(f"Brak interpretera Pythona: {python_executable}")
            return False

        # Przygotowujemy polecenie
        cmd = [python_executable, script_path]

        # Dodajemy argumenty, jeśli podano
        if args:
            cmd.extend(args)

        # Uruchamiamy skrypt
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            logger.error(f"Błąd podczas uruchamiania skryptu: {process.stderr}")
            return False

        logger.info(f"Skrypt został uruchomiony pomyślnie.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania skryptu: {str(e)}")
        return False
