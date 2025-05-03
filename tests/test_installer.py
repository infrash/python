"""
Tests for the installer module in infrash.core.installer.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from infrash.core.installer import Installer


class TestInstaller:
    """Test suite for the Installer class."""

    def test_init(self):
        """Test Installer initialization."""
        installer = Installer()
        assert installer is not None
        assert hasattr(installer, 'os_info')
        assert hasattr(installer, 'package_manager')

    @patch('infrash.core.installer.get_package_manager')
    @patch('infrash.core.installer.detect_os')
    def test_init_with_custom_os(self, mock_detect_os, mock_get_package_manager):
        """Test Installer initialization with custom OS info."""
        # Setup mocks
        mock_detect_os.return_value = {"type": "custom_os", "version": "1.0"}
        mock_get_package_manager.return_value = "custom_pm"
        
        installer = Installer()
        
        # Verify OS detection was called
        mock_detect_os.assert_called_once()
        mock_get_package_manager.assert_called_once()
        
        # Verify OS info was set correctly
        assert installer.os_info["type"] == "custom_os"
        assert installer.os_info["version"] == "1.0"
        assert installer.package_manager == "custom_pm"

    @patch('infrash.core.installer.subprocess.run')
    def test_install_package(self, mock_run):
        """Test install_package method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        installer = Installer()
        
        # Override package_manager for testing
        installer.package_manager = "apt"
        
        # Test successful package installation
        result = installer.install_package("test-package")
        
        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_with(
            ["apt", "install", "-y", "test-package"],
            capture_output=True,
            text=True
        )
        
        # Verify result
        assert result is True
        
        # Test failed package installation
        mock_process.returncode = 1
        result = installer.install_package("nonexistent-package")
        assert result is False

    @patch('infrash.core.installer.subprocess.run')
    def test_uninstall_package(self, mock_run):
        """Test uninstall_package method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        installer = Installer()
        
        # Override package_manager for testing
        installer.package_manager = "apt"
        
        # Test successful package uninstallation
        result = installer.uninstall_package("test-package")
        
        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_with(
            ["apt", "remove", "-y", "test-package"],
            capture_output=True,
            text=True
        )
        
        # Verify result
        assert result is True
        
        # Test failed package uninstallation
        mock_process.returncode = 1
        result = installer.uninstall_package("nonexistent-package")
        assert result is False

    @patch('infrash.core.installer.os.path.exists')
    @patch('infrash.core.installer.subprocess.run')
    def test_install_from_source(self, mock_run, mock_exists):
        """Test install_from_source method."""
        # Setup mocks
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        mock_exists.return_value = True
        
        installer = Installer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test successful installation from source
            result = installer.install_from_source(temp_dir)
            
            # Verify subprocess.run was called for each step
            assert mock_run.call_count >= 3  # configure, make, make install
            
            # Verify result
            assert result is True
            
            # Test failed installation from source
            mock_process.returncode = 1
            mock_run.reset_mock()
            result = installer.install_from_source(temp_dir)
            assert result is False

    @patch('infrash.core.installer.subprocess.run')
    def test_is_package_installed(self, mock_run):
        """Test is_package_installed method."""
        # Setup mock for successful check
        mock_process_success = MagicMock()
        mock_process_success.returncode = 0
        
        # Setup mock for failed check
        mock_process_fail = MagicMock()
        mock_process_fail.returncode = 1
        
        installer = Installer()
        
        # Override package_manager for testing
        installer.package_manager = "apt"
        
        # Test when package is installed
        mock_run.return_value = mock_process_success
        result = installer.is_package_installed("installed-package")
        assert result is True
        
        # Test when package is not installed
        mock_run.return_value = mock_process_fail
        result = installer.is_package_installed("not-installed-package")
        assert result is False
