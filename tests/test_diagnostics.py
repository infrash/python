"""
Tests for the Diagnostics class in infrash.core.diagnostics module.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from infrash.core.diagnostics.base import Diagnostics


class TestDiagnostics:
    """Test suite for the Diagnostics class."""

    def test_init(self):
        """Test Diagnostics initialization."""
        diagnostics = Diagnostics()
        assert diagnostics is not None
        assert hasattr(diagnostics, 'os_info')
        assert hasattr(diagnostics, 'package_manager')
        assert hasattr(diagnostics, 'git')
        assert hasattr(diagnostics, 'solutions_db')

    @patch('infrash.core.diagnostics.base.json.load')
    @patch('infrash.core.diagnostics.base.os.path.isfile')
    @patch('infrash.core.diagnostics.base.open', new_callable=mock_open, read_data='{}')
    def test_load_solutions_db(self, mock_file, mock_isfile, mock_json_load):
        """Test loading solutions database."""
        # Setup mocks
        mock_isfile.return_value = True
        mock_json_load.return_value = {"test_solution": {"description": "Test solution"}}
        
        diagnostics = Diagnostics()
        
        # Force reload of solutions_db
        diagnostics.solutions_db = diagnostics._load_solutions_db()
        
        # Verify json.load was called
        mock_json_load.assert_called()
        
        # Verify solutions_db was loaded
        assert diagnostics.solutions_db is not None
        assert "test_solution" in diagnostics.solutions_db

    @patch.object(Diagnostics, '_check_filesystem')
    @patch.object(Diagnostics, '_check_permissions')
    @patch.object(Diagnostics, '_check_dependencies')
    def test_run_basic(self, mock_dependencies, mock_permissions, mock_filesystem):
        """Test run method with basic level."""
        # Setup mocks
        mock_filesystem.return_value = [{"id": "fs1", "title": "FS Issue", "severity": "warning"}]
        mock_permissions.return_value = [{"id": "perm1", "title": "Permission Issue", "severity": "error"}]
        mock_dependencies.return_value = [{"id": "dep1", "title": "Dependency Issue", "severity": "critical"}]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            diagnostics = Diagnostics()
            issues = diagnostics.run(path=temp_dir, level="basic")
            
            # Verify all basic checks were called
            mock_filesystem.assert_called_once_with(os.path.abspath(temp_dir))
            mock_permissions.assert_called_once_with(os.path.abspath(temp_dir))
            mock_dependencies.assert_called_once_with(os.path.abspath(temp_dir))
            
            # Verify issues were sorted by severity
            assert len(issues) == 3
            assert issues[0]["id"] == "dep1"  # critical should be first
            assert issues[1]["id"] == "perm1"  # error should be second
            assert issues[2]["id"] == "fs1"    # warning should be third

    @patch.object(Diagnostics, '_check_filesystem')
    @patch.object(Diagnostics, '_check_permissions')
    @patch.object(Diagnostics, '_check_dependencies')
    @patch.object(Diagnostics, '_check_configuration')
    @patch.object(Diagnostics, '_check_repository')
    @patch.object(Diagnostics, '_check_networking')
    def test_run_advanced(self, mock_networking, mock_repository, mock_configuration, 
                          mock_dependencies, mock_permissions, mock_filesystem):
        """Test run method with advanced level."""
        # Setup mocks - all return empty lists for simplicity
        mock_filesystem.return_value = []
        mock_permissions.return_value = []
        mock_dependencies.return_value = []
        mock_configuration.return_value = []
        mock_repository.return_value = []
        mock_networking.return_value = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            diagnostics = Diagnostics()
            issues = diagnostics.run(path=temp_dir, level="advanced")
            
            # Verify all basic and advanced checks were called
            mock_filesystem.assert_called_once()
            mock_permissions.assert_called_once()
            mock_dependencies.assert_called_once()
            mock_configuration.assert_called_once()
            mock_repository.assert_called_once()
            mock_networking.assert_called_once()
            
            # Verify issues list was returned (empty in this case)
            assert issues == []

    def test_run_nonexistent_directory(self):
        """Test run method with a non-existent directory."""
        # Use a path that definitely doesn't exist
        non_existent_path = "/path/that/definitely/does/not/exist/12345"
        
        diagnostics = Diagnostics()
        issues = diagnostics.run(path=non_existent_path)
        
        # Verify that we got an issue about the non-existent directory
        assert len(issues) == 1
        assert "Katalog projektu nie istnieje" in issues[0]["title"]
        assert issues[0]["severity"] == "critical"
        assert issues[0]["category"] == "filesystem"
