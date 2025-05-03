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

__all__ = ['Diagnostics']