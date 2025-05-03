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

    @patch('infrash.core.diagnostics.base.socket.socket')
    def test_check_networking(self, mock_socket):
        """Test _check_networking method."""
        # Setup mocks
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Mock successful connection
        mock_socket_instance.connect_ex.return_value = 0
        
        diagnostics = Diagnostics()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock .env file with network configuration
            with open(os.path.join(temp_dir, ".env"), "w") as f:
                f.write("DB_HOST=localhost\nDB_PORT=5432\nAPI_URL=https://api.example.com\n")
            
            issues = diagnostics._check_networking(temp_dir)
            
            # Verify socket.connect_ex was called
            assert mock_socket_instance.connect_ex.call_count > 0
            
            # Verify no issues were found
            assert issues == []
            
            # Mock failed connection
            mock_socket_instance.connect_ex.return_value = 1
            
            issues = diagnostics._check_networking(temp_dir)
            
            # Verify issues were found
            assert len(issues) > 0
            assert issues[0]["category"] == "networking"
            assert issues[0]["severity"] in ["error", "critical"]

    @patch('infrash.core.diagnostics.base.subprocess.run')
    def test_check_network_connectivity(self, mock_run):
        """Test _check_network_connectivity method."""
        # Setup mock for successful ping
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        diagnostics = Diagnostics()
        
        # Test successful connectivity
        result = diagnostics._check_network_connectivity("192.168.188.154")
        
        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_with(
            ["ping", "-c", "3", "192.168.188.154"],
            capture_output=True,
            text=True
        )
        
        # Verify result
        assert result is True
        
        # Setup mock for failed ping
        mock_process.returncode = 1
        
        # Test failed connectivity
        result = diagnostics._check_network_connectivity("192.168.1.154")
        
        # Verify result
        assert result is False

    @patch('infrash.core.diagnostics.base.socket.gethostbyname')
    def test_check_dns_resolution(self, mock_gethostbyname):
        """Test _check_dns_resolution method."""
        # Setup mock for successful DNS resolution
        mock_gethostbyname.return_value = "93.184.216.34"  # example.com IP
        
        diagnostics = Diagnostics()
        
        # Test successful DNS resolution
        result = diagnostics._check_dns_resolution("example.com")
        
        # Verify socket.gethostbyname was called with correct arguments
        mock_gethostbyname.assert_called_with("example.com")
        
        # Verify result
        assert result is True
        
        # Setup mock for failed DNS resolution
        mock_gethostbyname.side_effect = Exception("DNS resolution failed")
        
        # Test failed DNS resolution
        result = diagnostics._check_dns_resolution("nonexistent.example.com")
        
        # Verify result
        assert result is False

    @patch('infrash.core.diagnostics.base.requests.get')
    def test_check_http_connectivity(self, mock_get):
        """Test _check_http_connectivity method."""
        # Setup mock for successful HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        diagnostics = Diagnostics()
        
        # Test successful HTTP connectivity
        result = diagnostics._check_http_connectivity("https://example.com")
        
        # Verify requests.get was called with correct arguments
        mock_get.assert_called_with("https://example.com", timeout=5)
        
        # Verify result
        assert result is True
        
        # Setup mock for failed HTTP request
        mock_get.side_effect = Exception("HTTP request failed")
        
        # Test failed HTTP connectivity
        result = diagnostics._check_http_connectivity("https://nonexistent.example.com")
        
        # Verify result
        assert result is False

    @patch.object(Diagnostics, '_analyze_log_file')
    def test_analyze_logs(self, mock_analyze_log_file):
        """Test analyze_logs method."""
        # Setup mock
        mock_analyze_log_file.return_value = [
            {"id": "log1", "title": "Error in log", "severity": "error"}
        ]
        
        diagnostics = Diagnostics()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock log file
            log_dir = os.path.join(temp_dir, "logs")
            os.makedirs(log_dir)
            with open(os.path.join(log_dir, "app.log"), "w") as f:
                f.write("ERROR: Connection failed\n")
            
            issues = diagnostics.analyze_logs(temp_dir)
            
            # Verify _analyze_log_file was called
            mock_analyze_log_file.assert_called()
            
            # Verify issues were found
            assert len(issues) > 0
            assert issues[0]["id"] == "log1"

    def test_get_solution(self):
        """Test get_solution method."""
        # Create a diagnostics instance with a mock solutions_db
        diagnostics = Diagnostics()
        diagnostics.solutions_db = {
            "network_unreachable": {
                "title": "Network Unreachable",
                "description": "The target network is unreachable.",
                "solutions": [
                    "Check if the IP address is correct",
                    "Verify that the target device is powered on",
                    "Check network configuration"
                ]
            }
        }
        
        # Test getting a solution that exists
        solution = diagnostics.get_solution("network_unreachable")
        
        # Verify solution was returned
        assert solution is not None
        assert solution["title"] == "Network Unreachable"
        assert len(solution["solutions"]) == 3
        
        # Test getting a solution that doesn't exist
        solution = diagnostics.get_solution("nonexistent_solution")
        
        # Verify no solution was returned
        assert solution is None

    @patch('infrash.core.diagnostics.base.requests.get')
    def test_update_solutions_db(self, mock_get):
        """Test update_solutions_db method."""
        # Setup mock for successful HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "network_unreachable": {
                "title": "Network Unreachable",
                "description": "The target network is unreachable.",
                "solutions": [
                    "Check if the IP address is correct",
                    "Verify that the target device is powered on",
                    "Check network configuration"
                ]
            }
        }
        mock_get.return_value = mock_response
        
        diagnostics = Diagnostics()
        
        # Test successful update
        with patch('infrash.core.diagnostics.base.open', new_callable=mock_open) as mock_file:
            result = diagnostics.update_solutions_db()
            
            # Verify requests.get was called
            mock_get.assert_called()
            
            # Verify file was opened for writing
            mock_file.assert_called()
            
            # Verify result
            assert result is True
            
            # Verify solutions_db was updated
            assert "network_unreachable" in diagnostics.solutions_db
        
        # Setup mock for failed HTTP request
        mock_get.side_effect = Exception("HTTP request failed")
        
        # Test failed update
        result = diagnostics.update_solutions_db()
        
        # Verify result
        assert result is False
