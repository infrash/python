#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł naprawczy infrash - inicjalizacja.
"""

from infrash.core.repair.base import Repair
from infrash.core.repair.solutions import _apply_solution, _replace_variables
from infrash.core.repair.execution import _run_command, _modify_file, _create_file, _install_package
from infrash.core.repair.filesystem import _fix_filesystem
from infrash.core.repair.permissions import _fix_permissions
from infrash.core.repair.dependencies import _fix_dependencies
from infrash.core.repair.configuration import _fix_configuration

# Dodajemy metody do klasy Repair
Repair._apply_solution = _apply_solution
Repair._replace_variables = _replace_variables
Repair._run_command = _run_command
Repair._modify_file = _modify_file
Repair._create_file = _create_file
Repair._install_package = _install_package
Repair._fix_filesystem = _fix_filesystem
Repair._fix_permissions = _fix_permissions
Repair._fix_dependencies = _fix_dependencies
Repair._fix_configuration = _fix_configuration

__all__ = ['Repair']