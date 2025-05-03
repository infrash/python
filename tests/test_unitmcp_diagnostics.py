"""
Tests for the DiagnosticsEngine class in unitmcp.orchestrator.diagnostics module.
"""

import os
import sys
import socket
import platform
import subprocess
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from unitmcp.orchestrator.diagnostics import DiagnosticsEngine


class TestDiagnosticsEngine:
    """Test suite for the DiagnosticsEngine class."""

    def test_init(self):
        """Test DiagnosticsEngine initialization."""
        engine = DiagnosticsEngine()
        assert engine is not None
        assert hasattr(engine, 'error_patterns')
        assert isinstance(engine.error_patterns, dict)
        assert len(engine.error_patterns) > 0

    def test_analyze_error_git_existing_directory(self):
        """Test analyzing a Git error for an existing directory."""
        engine = DiagnosticsEngine()
        error_message = "fatal: destination path 'mcp' already exists and is not an empty directory."
        
        result = engine.analyze_error(error_message)
        
        assert result is not None
        assert "message" in result
        assert "solution" in result
        assert "directory already exists" in result["message"].lower()

    def test_analyze_error_git_network(self):
        """Test analyzing a Git error for network issues."""
        engine = DiagnosticsEngine()
        error_message = "fatal: Could not resolve host: github.com"
        
        result = engine.analyze_error(error_message)
        
        assert result is not None
        assert "message" in result
        assert "solution" in result
        assert "network issue" in result["message"].lower()
        assert "internet connection" in result["solution"].lower()

    def test_analyze_error_python_module(self):
        """Test analyzing a Python module not found error."""
        engine = DiagnosticsEngine()
        error_message = "ModuleNotFoundError: No module named 'paramiko'"
        
        result = engine.analyze_error(error_message)
        
        assert result is not None
        assert "message" in result
        assert "solution" in result
        assert "module not found" in result["message"].lower()
        assert "pip install paramiko" in result["solution"].lower()

    def test_analyze_error_no_match(self):
        """Test analyzing an error with no matching pattern."""
        engine = DiagnosticsEngine()
        error_message = "This is a completely random error message that won't match any pattern"
        
        result = engine.analyze_error(error_message)
        
        assert result is None

    @patch('socket.gethostbyname')
    @patch('socket.socket')
    def test_check_network_connectivity_success(self, mock_socket, mock_gethostbyname):
        """Test checking network connectivity - success case."""
        # Setup mocks
        mock_gethostbyname.return_value = "192.168.1.1"
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        engine = DiagnosticsEngine()
        success, message = engine.check_network_connectivity("example.com", 80)
        
        assert success is True
        assert "Successfully connected" in message
        mock_gethostbyname.assert_called_once_with("example.com")
        mock_socket_instance.connect.assert_called_once()

    @patch('socket.gethostbyname')
    def test_check_network_connectivity_dns_failure(self, mock_gethostbyname):
        """Test checking network connectivity - DNS resolution failure."""
        # Setup mock to raise an exception
        mock_gethostbyname.side_effect = socket.gaierror("DNS resolution failed")
        
        engine = DiagnosticsEngine()
        success, message = engine.check_network_connectivity("nonexistent.example.com", 80)
        
        assert success is False
        assert "Could not resolve hostname" in message
        mock_gethostbyname.assert_called_once_with("nonexistent.example.com")

    @patch('socket.gethostbyname')
    @patch('socket.socket')
    def test_check_network_connectivity_connection_timeout(self, mock_socket, mock_gethostbyname):
        """Test checking network connectivity - connection timeout."""
        # Setup mocks
        mock_gethostbyname.return_value = "192.168.1.1"
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.timeout("Connection timed out")
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        engine = DiagnosticsEngine()
        success, message = engine.check_network_connectivity("example.com", 80)
        
        assert success is False
        assert "timed out" in message
        mock_gethostbyname.assert_called_once_with("example.com")
        mock_socket_instance.connect.assert_called_once()

    @patch('socket.gethostbyname')
    @patch('socket.socket')
    def test_check_network_connectivity_connection_refused(self, mock_socket, mock_gethostbyname):
        """Test checking network connectivity - connection refused."""
        # Setup mocks
        mock_gethostbyname.return_value = "192.168.1.1"
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        engine = DiagnosticsEngine()
        success, message = engine.check_network_connectivity("example.com", 80)
        
        assert success is False
        assert "refused" in message
        mock_gethostbyname.assert_called_once_with("example.com")
        mock_socket_instance.connect.assert_called_once()

    @patch('subprocess.run')
    def test_check_system_requirements_all_met(self, mock_run):
        """Test checking system requirements - all requirements met."""
        # Setup mock to indicate all tools are available
        mock_run.return_value = MagicMock(returncode=0)
        
        engine = DiagnosticsEngine()
        result = engine.check_system_requirements(["git", "python", "npm"])
        
        assert result == {"git": True, "python": True, "npm": True}
        assert mock_run.call_count == 3

    @patch('subprocess.run')
    def test_check_system_requirements_some_missing(self, mock_run):
        """Test checking system requirements - some requirements missing."""
        # Setup mock to indicate some tools are missing
        def mock_run_side_effect(cmd, **kwargs):
            if cmd[0] == "git":
                return MagicMock(returncode=0)
            else:
                raise FileNotFoundError(f"No such file or directory: '{cmd[0]}'")
        
        mock_run.side_effect = mock_run_side_effect
        
        engine = DiagnosticsEngine()
        result = engine.check_system_requirements(["git", "nonexistent1", "nonexistent2"])
        
        assert result == {"git": True, "nonexistent1": False, "nonexistent2": False}

    @patch('socket.gethostbyname')
    def test_diagnose_network_issue_dns_failure(self, mock_gethostbyname):
        """Test diagnosing network issues - DNS resolution failure."""
        # Setup mock to raise an exception
        mock_gethostbyname.side_effect = socket.gaierror("DNS resolution failed")
        
        engine = DiagnosticsEngine()
        result = engine.diagnose_network_issue("nonexistent.example.com")
        
        assert result["host"] == "nonexistent.example.com"
        assert result["dns_resolution"] is False
        assert result["reachable"] is False
        assert len(result["suggestions"]) > 0
        assert any("DNS resolution failed" in suggestion for suggestion in result["suggestions"])

    @patch('socket.gethostbyname')
    @patch('subprocess.run')
    def test_diagnose_network_issue_ping_failure(self, mock_run, mock_gethostbyname):
        """Test diagnosing network issues - ping failure."""
        # Setup mocks
        mock_gethostbyname.return_value = "192.168.1.1"
        mock_run.side_effect = subprocess.SubprocessError("Ping failed")
        
        engine = DiagnosticsEngine()
        result = engine.diagnose_network_issue("example.com")
        
        assert result["host"] == "example.com"
        assert result["dns_resolution"] is True
        assert result["reachable"] is False
        assert "ip" in result
        assert len(result["suggestions"]) > 0
        assert any("not responding to ping" in suggestion for suggestion in result["suggestions"])

    @patch('socket.socket')
    def test_diagnose_port_issue_connection_refused(self, mock_socket):
        """Test diagnosing port issues - connection refused."""
        # Setup mock
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        engine = DiagnosticsEngine()
        result = engine.diagnose_port_issue("example.com", 22)
        
        assert result["host"] == "example.com"
        assert result["port"] == 22
        assert result["open"] is False
        assert len(result["suggestions"]) > 0
        assert any("refused" in suggestion for suggestion in result["suggestions"])
        assert any("service is running" in suggestion for suggestion in result["suggestions"])

    def test_diagnose_git_issue_existing_directory(self):
        """Test diagnosing Git issues - existing directory."""
        engine = DiagnosticsEngine()
        error_message = "fatal: destination path 'mcp' already exists and is not an empty directory."
        repo_url = "https://github.com/UnitApi/mcp.git"
        
        result = engine.diagnose_git_issue(error_message, repo_url)
        
        assert result["repo_url"] == repo_url
        assert result["error"] == error_message
        assert len(result["suggestions"]) > 0
        assert any("already exists" in suggestion for suggestion in result["suggestions"])
        assert any("different directory" in suggestion for suggestion in result["suggestions"])

    def test_diagnose_git_issue_host_not_found(self):
        """Test diagnosing Git issues - host not found."""
        engine = DiagnosticsEngine()
        error_message = "fatal: Could not resolve host: github.com"
        repo_url = "https://github.com/UnitApi/mcp.git"
        
        result = engine.diagnose_git_issue(error_message, repo_url)
        
        assert result["repo_url"] == repo_url
        assert result["error"] == error_message
        assert len(result["suggestions"]) > 0
        assert any("Network issue" in suggestion for suggestion in result["suggestions"])
        assert any("internet connection" in suggestion for suggestion in result["suggestions"])

    def test_diagnose_git_issue_authentication_failed(self):
        """Test diagnosing Git issues - authentication failed."""
        engine = DiagnosticsEngine()
        error_message = "fatal: Authentication failed for 'https://github.com/UnitApi/mcp.git'"
        repo_url = "https://github.com/UnitApi/mcp.git"
        
        result = engine.diagnose_git_issue(error_message, repo_url)
        
        assert result["repo_url"] == repo_url
        assert result["error"] == error_message
        assert len(result["suggestions"]) > 0
