#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł diagnostyczny infrash - inicjalizacja.
"""

from infrash.core.diagnostics.base import Diagnostics
from infrash.core.diagnostics.filesystem import _check_filesystem, _check_permissions
from infrash.core.diagnostics.dependencies import _check_dependencies
from infrash.core.diagnostics.configuration import _check_configuration
from infrash.core.diagnostics.repository import _check_repository
from infrash.core.diagnostics.networking import _check_networking
from infrash.core.diagnostics.resources import _check_system_resources
from infrash.core.diagnostics.logs import _check_logs
from infrash.core.diagnostics.database import _check_database
from infrash.core.diagnostics.process import _check_process_handling
from infrash.core.diagnostics.script import analyze_script_error, _find_package_for_module
from infrash.core.diagnostics.asyncio import solve_asyncio_error
from infrash.core.diagnostics.connection import fix_connection_issues
from infrash.core.diagnostics.hardware import analyze_hardware_issues
import socket
import shutil
from typing import Dict, List, Any, Optional

# Dodajemy metody do klasy Diagnostics
Diagnostics._check_filesystem = _check_filesystem
Diagnostics._check_permissions = _check_permissions
Diagnostics._check_dependencies = _check_dependencies
Diagnostics._check_configuration = _check_configuration
Diagnostics._check_repository = _check_repository
Diagnostics._check_networking = _check_networking
Diagnostics._check_system_resources = _check_system_resources
Diagnostics._check_logs = _check_logs
Diagnostics._check_database = _check_database
Diagnostics._check_process_handling = _check_process_handling
Diagnostics.analyze_script_error = analyze_script_error
Diagnostics._find_package_for_module = _find_package_for_module
Diagnostics.solve_asyncio_error = solve_asyncio_error
Diagnostics.fix_connection_issues = fix_connection_issues
Diagnostics.analyze_hardware_issues = analyze_hardware_issues

# Add check_network_connectivity method directly to Diagnostics
def check_network_connectivity(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 3):
    """
    Sprawdza połączenie sieciowe.
    
    Args:
        host: Host do sprawdzenia (domyślnie Google DNS)
        port: Port do sprawdzenia (domyślnie 53 dla DNS)
        timeout: Limit czasu w sekundach
        
    Returns:
        Dict[str, Any]: Status połączenia
    """
    try:
        # Utwórz socket
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(timeout)
        
        # Próba połączenia
        result = socket_obj.connect_ex((host, port))
        socket_obj.close()
        
        if result == 0:
            return {
                "success": True,
                "message": f"Połączenie z {host}:{port} działa poprawnie."
            }
        else:
            return {
                "success": False,
                "message": f"Nie można połączyć się z {host}:{port}.",
                "suggestion": "Sprawdź swoje połączenie internetowe i ustawienia zapory sieciowej."
            }
    except socket.gaierror:
        return {
            "success": False,
            "message": f"Nie można rozwiązać nazwy hosta {host}.",
            "suggestion": "Sprawdź swoje ustawienia DNS lub użyj adresu IP zamiast nazwy hosta."
        }
    except socket.timeout:
        return {
            "success": False,
            "message": f"Upłynął limit czasu podczas łączenia z {host}:{port}.",
            "suggestion": "Sprawdź swoje połączenie internetowe lub zwiększ limit czasu."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Błąd podczas sprawdzania połączenia sieciowego: {str(e)}",
            "suggestion": "Sprawdź swoje połączenie internetowe i ustawienia sieciowe."
        }

# Add check_tool_available method
def check_tool_available(self, tool_name: str) -> Dict[str, Any]:
    """
    Sprawdza, czy narzędzie jest dostępne w systemie.
    
    Args:
        tool_name: Nazwa narzędzia do sprawdzenia
        
    Returns:
        Dict[str, Any]: Status narzędzia
    """
    try:
        # Sprawdź, czy narzędzie jest dostępne w PATH
        if shutil.which(tool_name) is not None:
            return {
                "success": True,
                "message": f"Narzędzie {tool_name} jest dostępne."
            }
        else:
            # Narzędzie nie jest dostępne
            return {
                "success": False,
                "message": f"Narzędzie {tool_name} nie jest dostępne.",
                "suggestion": f"Zainstaluj {tool_name} używając menedżera pakietów twojego systemu."
            }
    except Exception as e:
        # Inny błąd podczas sprawdzania
        return {
            "success": False,
            "message": f"Błąd podczas sprawdzania narzędzia {tool_name}: {str(e)}",
            "suggestion": "Sprawdź logi, aby uzyskać więcej informacji."
        }

# Add check_required_tools method
def check_required_tools(self, tools: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sprawdza, czy wszystkie wymagane narzędzia są dostępne.
    
    Args:
        tools: Lista narzędzi do sprawdzenia (opcjonalne)
        
    Returns:
        Dict[str, Any]: Status narzędzi
    """
    if tools is None:
        tools = ["git", "ssh", "python3", "pip"]
    
    missing_tools = []
    
    for tool in tools:
        try:
            result = self.check_tool_available(tool)
            if not result["success"]:
                missing_tools.append(tool)
        except Exception as e:
            # Kontynuuj sprawdzanie innych narzędzi
            missing_tools.append(tool)
    
    if missing_tools:
        return {
            "success": False,
            "missing": missing_tools,
            "message": f"Brakujące narzędzia: {', '.join(missing_tools)}",
            "suggestion": f"Zainstaluj brakujące narzędzia używając menedżera pakietów twojego systemu."
        }
    else:
        return {
            "success": True,
            "message": "Wszystkie wymagane narzędzia są dostępne."
        }

Diagnostics.check_network_connectivity = check_network_connectivity
Diagnostics.check_tool_available = check_tool_available
Diagnostics.check_required_tools = check_required_tools

__all__ = ['Diagnostics']