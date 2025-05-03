"""
Tests for the NetworkManager class in unitmcp.orchestrator.network module.
"""

import os
import sys
import socket
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from unitmcp.orchestrator.network import NetworkManager


class TestNetworkManager:
    """Test suite for the NetworkManager class."""

    def test_init(self):
        """Test NetworkManager initialization."""
        network_manager = NetworkManager()
        assert network_manager is not None

    @patch('paramiko.SSHClient')
    def test_connect_ssh_success(self, mock_ssh_client):
        """Test successful SSH connection."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_ssh_client.return_value = mock_client_instance
        
        network_manager = NetworkManager()
        success, client = network_manager.connect_ssh(
            host="example.com",
            username="user",
            password="password"
        )
        
        assert success is True
        assert client is mock_client_instance
        mock_client_instance.set_missing_host_key_policy.assert_called_once()
        mock_client_instance.connect.assert_called_once_with(
            hostname="example.com",
            port=22,
            username="user",
            password="password",
            key_filename=None,
            timeout=10
        )

    @patch('paramiko.SSHClient')
    def test_connect_ssh_authentication_failure(self, mock_ssh_client):
        """Test SSH connection with authentication failure."""
        # Setup mock
        from paramiko import AuthenticationException
        mock_client_instance = MagicMock()
        mock_client_instance.connect.side_effect = AuthenticationException("Authentication failed")
        mock_ssh_client.return_value = mock_client_instance
        
        network_manager = NetworkManager()
        success, client = network_manager.connect_ssh(
            host="example.com",
            username="user",
            password="wrong_password"
        )
        
        assert success is False
        assert client is None
        mock_client_instance.set_missing_host_key_policy.assert_called_once()
        mock_client_instance.connect.assert_called_once()

    @patch('paramiko.SSHClient')
    def test_connect_ssh_network_error(self, mock_ssh_client):
        """Test SSH connection with network error."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_client_instance.connect.side_effect = socket.error("No route to host")
        mock_ssh_client.return_value = mock_client_instance
        
        network_manager = NetworkManager()
        success, client = network_manager.connect_ssh(
            host="nonexistent.example.com",
            username="user",
            password="password"
        )
        
        assert success is False
        assert client is None
        mock_client_instance.set_missing_host_key_policy.assert_called_once()
        mock_client_instance.connect.assert_called_once()

    @patch('socket.socket')
    def test_get_local_ip_success(self, mock_socket):
        """Test getting local IP address - success case."""
        # Setup mock
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ("192.168.1.100", 12345)
        mock_socket.return_value = mock_socket_instance
        
        network_manager = NetworkManager()
        local_ip = network_manager._get_local_ip()
        
        assert local_ip == "192.168.1.100"
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 80))
        mock_socket_instance.getsockname.assert_called_once()
        mock_socket_instance.close.assert_called_once()

    @patch('socket.socket')
    def test_get_local_ip_failure(self, mock_socket):
        """Test getting local IP address - failure case."""
        # Setup mock
        mock_socket.side_effect = Exception("Network error")
        
        network_manager = NetworkManager()
        local_ip = network_manager._get_local_ip()
        
        assert local_ip is None

    @patch('paramiko.SSHClient')
    def test_setup_remote_environment_success(self, mock_ssh_client):
        """Test setting up remote environment - success case."""
        # Setup mock
        mock_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        network_manager = NetworkManager()
        success = network_manager.setup_remote_environment(
            mock_client,
            "https://github.com/UnitApi/mcp.git"
        )
        
        assert success is True
        assert mock_client.exec_command.call_count >= 3  # At least 3 commands should be executed

    @patch('paramiko.SSHClient')
    def test_setup_remote_environment_clone_failure(self, mock_ssh_client):
        """Test setting up remote environment - clone failure."""
        # Setup mock
        mock_client = MagicMock()
        
        # First two commands succeed
        mock_stdout_success = MagicMock()
        mock_stdout_success.channel.recv_exit_status.return_value = 0
        mock_stderr_success = MagicMock()
        mock_stderr_success.read.return_value = b""
        
        # Clone command fails
        mock_stdout_failure = MagicMock()
        mock_stdout_failure.channel.recv_exit_status.return_value = 1
        mock_stderr_failure = MagicMock()
        mock_stderr_failure.read.return_value = b"fatal: destination path already exists"
        
        # Set up the exec_command to return different results for different calls
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "git clone" in cmd:
                return (None, mock_stdout_failure, mock_stderr_failure)
            else:
                return (None, mock_stdout_success, mock_stderr_success)
        
        mock_client.exec_command.side_effect = side_effect
        
        network_manager = NetworkManager()
        success = network_manager.setup_remote_environment(
            mock_client,
            "https://github.com/UnitApi/mcp.git"
        )
        
        assert success is False
        assert mock_client.exec_command.call_count >= 3  # At least 3 commands should be executed

    @patch('paramiko.SSHClient')
    def test_run_remote_command_success(self, mock_ssh_client):
        """Test running a remote command - success case."""
        # Setup mock
        mock_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Command output"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        network_manager = NetworkManager()
        success, stdout, stderr = network_manager.run_remote_command(
            mock_client,
            "ls -la"
        )
        
        assert success is True
        assert stdout == "Command output"
        assert stderr == ""
        mock_client.exec_command.assert_called_once_with("ls -la")

    @patch('paramiko.SSHClient')
    def test_run_remote_command_failure(self, mock_ssh_client):
        """Test running a remote command - failure case."""
        # Setup mock
        mock_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stdout.read.return_value = b""
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b"Command failed"
        mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
        
        network_manager = NetworkManager()
        success, stdout, stderr = network_manager.run_remote_command(
            mock_client,
            "nonexistent_command"
        )
        
        assert success is False
        assert stdout == ""
        assert stderr == "Command failed"
        mock_client.exec_command.assert_called_once_with("nonexistent_command")

    @patch('paramiko.SSHClient')
    def test_run_remote_command_exception(self, mock_ssh_client):
        """Test running a remote command - exception case."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.exec_command.side_effect = Exception("SSH error")
        
        network_manager = NetworkManager()
        success, stdout, stderr = network_manager.run_remote_command(
            mock_client,
            "ls -la"
        )
        
        assert success is False
        assert stdout == ""
        assert "SSH error" in stderr
        mock_client.exec_command.assert_called_once_with("ls -la")

    def test_get_timestamp(self):
        """Test getting a timestamp."""
        network_manager = NetworkManager()
        timestamp = network_manager._get_timestamp()
        
        assert timestamp is not None
        assert timestamp.isdigit()
        assert len(timestamp) >= 10  # Unix timestamp should be at least 10 digits

    @patch('paramiko.SSHClient')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_env_info(self, mock_file, mock_ssh_client):
        """Test saving environment information."""
        # Setup mocks
        mock_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        
        # Mock os.makedirs to avoid creating directories
        with patch('os.makedirs') as mock_makedirs:
            network_manager = NetworkManager()
            network_manager._save_env_info(
                mock_client,
                "test_project",
                "https://github.com/UnitApi/test.git"
            )
            
            # Verify os.makedirs was called
            mock_makedirs.assert_called_once()
            
            # Verify exec_command was called to create remote .env file
            mock_client.exec_command.assert_called_once()
            
            # Verify local file was created
            mock_file.assert_called_once()
            mock_file().write.assert_called()
