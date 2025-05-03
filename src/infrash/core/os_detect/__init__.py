#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł wykrywania systemu operacyjnego - inicjalizacja.
"""

from infrash.system.os_detect.base import detect_os, is_admin
from infrash.system.os_detect.package_manager import get_package_manager
from infrash.system.os_detect.installation import install_package_manager
from infrash.system.os_detect.utilities import (
    get_python_version,
    is_virtual_env,
    is_raspberry_pi,
    is_available_command
)

__all__ = [
    'detect_os',
    'is_admin',
    'get_package_manager',
    'install_package_manager',
    'get_python_version',
    'is_virtual_env',
    'is_raspberry_pi',
    'is_available_command'
]