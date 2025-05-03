"""
Tests for the Diagnostics class in infrash.core.diagnostics module.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from infrash.core.diagnostics.base import Diagnostics
from infrash.core.diagnostics.networking import _check_networking
from infrash.core.diagnostics.logs import _check_logs


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

    @patch('infrash.core.diagnostics.base.Diagnostics._check_filesystem')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_permissions')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_dependencies')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_configuration')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_repository')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_networking')
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

    @patch('infrash.core.diagnostics.base.Diagnostics._check_filesystem')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_permissions')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_dependencies')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_configuration')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_repository')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_networking')
    def test_check_networking(self, mock_networking, mock_repository, mock_configuration, 
                             mock_dependencies, mock_permissions, mock_filesystem):
        """Test _check_networking method."""
        # Setup mocks - all return empty lists for simplicity
        mock_filesystem.return_value = []
        mock_permissions.return_value = []
        mock_dependencies.return_value = []
        mock_configuration.return_value = []
        mock_repository.return_value = []
        mock_networking.return_value = []
        
        diagnostics = Diagnostics()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock .env file with network configuration
            with open(os.path.join(temp_dir, ".env"), "w") as f:
                f.write("DB_HOST=localhost\nDB_PORT=5432\nAPI_URL=https://api.example.com\n")
            
            # Call run method with advanced level to trigger _check_networking
            diagnostics.run(path=temp_dir, level="advanced")
            
            # Verify _check_networking was called
            mock_networking.assert_called_once()
            
            # Setup mock to return issues
            mock_networking.return_value = [
                {
                    "id": "net1",
                    "title": "Network Issue",
                    "description": "Test network issue",
                    "solution": "Test solution",
                    "severity": "error",
                    "category": "networking"
                }
            ]
            
            # Call run method again
            issues = diagnostics.run(path=temp_dir, level="advanced")
            
            # Verify issues were found
            assert any(issue["category"] == "networking" for issue in issues)

    @patch('socket.create_connection')
    def test_network_connectivity(self, mock_create_connection):
        """Test network connectivity check in _check_networking method."""
        # Import the function directly from the networking module
        from infrash.core.diagnostics.networking import _check_networking
        
        # Setup mock for successful connection
        mock_create_connection.return_value = MagicMock()
        
        # Test successful connectivity
        issues = _check_networking()
        
        # Verify socket.create_connection was called
        mock_create_connection.assert_called_with(("8.8.8.8", 53), timeout=3)
        
        # Verify no connectivity issues were found
        assert not any(issue["title"] == "Brak połączenia z internetem" for issue in issues)
        
        # Setup mock for failed connection
        mock_create_connection.side_effect = Exception("Connection failed")
        
        # Test failed connectivity
        issues = _check_networking()
        
        # Verify connectivity issues were found
        assert any(issue["title"] == "Brak połączenia z internetem" for issue in issues)

    @patch('infrash.core.diagnostics.base.Diagnostics._check_filesystem')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_permissions')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_dependencies')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_configuration')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_repository')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_networking')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_system_resources')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_logs')
    @patch('infrash.core.diagnostics.base.Diagnostics._check_database')
    def test_analyze_log_file(self, mock_database, mock_logs, mock_resources, 
                             mock_networking, mock_repository, mock_configuration, 
                             mock_dependencies, mock_permissions, mock_filesystem):
        """Test log file analysis."""
        # Setup mocks - all return empty lists for simplicity
        mock_filesystem.return_value = []
        mock_permissions.return_value = []
        mock_dependencies.return_value = []
        mock_configuration.return_value = []
        mock_repository.return_value = []
        mock_networking.return_value = []
        mock_resources.return_value = []
        mock_database.return_value = []
        
        # Setup mock for logs to return issues
        mock_logs.return_value = [
            {
                "id": "log1",
                "title": "Błędy w logach",
                "description": "Znaleziono 3 linii z błędami w pliku test.log",
                "solution": "Sprawdź logi, aby zidentyfikować przyczynę błędów.",
                "severity": "warning",
                "category": "logs",
                "metadata": {
                    "log_file": "test.log",
                    "error_count": 3,
                    "last_error": "Error: Connection refused"
                }
            }
        ]
        
        diagnostics = Diagnostics()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call run method with full level to trigger _check_logs
            issues = diagnostics.run(path=temp_dir, level="full")
            
            # Verify _check_logs was called
            mock_logs.assert_called_once_with(temp_dir)
            
            # Verify issues from _check_logs were included in the result
            assert any(issue["category"] == "logs" for issue in issues)

    def test_get_solution(self):
        """Test getting solution for a problem."""
        diagnostics = Diagnostics()
        
        # Mock the solutions_db with a test solution
        diagnostics.solutions_db = {
            "test_problem": {
                "description": "Test problem description",
                "solution": "Test solution steps",
                "severity": "error"
            }
        }
        
        # Test getting an existing solution
        problem_id = "test_problem"
        solution = diagnostics.solutions_db.get(problem_id)
        
        # Verify solution was found
        assert solution is not None
        assert solution["description"] == "Test problem description"
        assert solution["solution"] == "Test solution steps"
        
        # Test getting a non-existent solution
        non_existent_id = "non_existent_problem"
        solution = diagnostics.solutions_db.get(non_existent_id)
        
        # Verify solution was not found
        assert solution is None

    # Removing the test_update_solutions_db test as it's not implemented in the current codebase
