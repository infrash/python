"""
Tests for the Runner class in infrash.core.runner module.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from infrash.core.runner import Runner, init_project


class TestRunner:
    """Test suite for the Runner class."""

    def test_init(self):
        """Test Runner initialization."""
        runner = Runner()
        assert runner is not None
        assert hasattr(runner, 'config')
        assert hasattr(runner, 'os_info')
        assert hasattr(runner, 'service_manager')
        assert hasattr(runner, 'processes')
        assert hasattr(runner, 'git')
        assert isinstance(runner.pid_dir, Path)

    @patch('infrash.core.runner.yaml')
    def test_load_config(self, mock_yaml):
        """Test loading configuration."""
        # Setup mock
        mock_yaml.safe_load.return_value = {"auto_repair": False}
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(suffix='.yaml') as temp_file:
            runner = Runner(config_path=temp_file.name)
            
            # Verify yaml.safe_load was called
            mock_yaml.safe_load.assert_called_once()
            
            # Verify config was loaded
            assert runner.config is not None
            
    @patch('infrash.core.runner.os.path.isfile')
    def test_load_config_default(self, mock_isfile):
        """Test loading default configuration when no file exists."""
        # Make os.path.isfile return False for all paths
        mock_isfile.return_value = False
        
        runner = Runner()
        
        # Verify default config was loaded
        assert runner.config is not None
        assert 'auto_repair' in runner.config
        assert 'diagnostic_level' in runner.config
        assert 'environments' in runner.config

    @patch('infrash.core.runner.Runner')
    def test_init_project(self, mock_runner):
        """Test init_project function."""
        # Setup mock
        mock_instance = MagicMock()
        mock_runner.return_value = mock_instance
        
        # Call the function
        result = init_project(path="test_path", template="custom")
        
        # Verify the function called the right methods
        mock_instance.assert_not_called()  # init_project doesn't use the Runner instance
        
        # Since we're mocking, we can't really test the return value
        # but we can verify the function completed without errors
        assert result is not None

    @patch.object(Runner, '_get_process_info')
    @patch.object(Runner, 'is_running_pid')
    def test_is_running(self, mock_is_running_pid, mock_get_process_info):
        """Test is_running method."""
        # Setup mocks
        mock_get_process_info.return_value = {'pid': 12345}
        mock_is_running_pid.return_value = True
        
        runner = Runner()
        
        # Test when process is running
        assert runner.is_running("test_path") is True
        
        # Test when process is not running
        mock_is_running_pid.return_value = False
        assert runner.is_running("test_path") is False
        
        # Test when no process info
        mock_get_process_info.return_value = None
        assert runner.is_running("test_path") is False

    @patch.object(Runner, 'install_dependencies')
    @patch.object(Runner, 'detect_app_type')
    def test_run_application(self, mock_detect_app_type, mock_install_dependencies):
        """Test run_application method."""
        # Setup mocks
        mock_detect_app_type.return_value = "python"
        mock_install_dependencies.return_value = True
        
        runner = Runner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the _run_python_app method
            with patch.object(runner, '_run_python_app', return_value=True) as mock_run_python:
                result = runner.run_application(temp_dir)
                
                # Verify dependencies were installed
                mock_install_dependencies.assert_called_once_with(temp_dir)
                
                # Verify app type was detected
                mock_detect_app_type.assert_called_once_with(temp_dir)
                
                # Verify the correct run method was called
                mock_run_python.assert_called_once_with(temp_dir)
                
                # Verify result
                assert result is True
    
    @patch.object(Runner, 'detect_app_type')
    def test_run_application_unsupported_type(self, mock_detect_app_type):
        """Test run_application method with unsupported app type."""
        # Setup mock
        mock_detect_app_type.return_value = "unsupported"
        
        runner = Runner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.run_application(temp_dir)
            
            # Verify app type was detected
            mock_detect_app_type.assert_called_once_with(temp_dir)
            
            # Verify result
            assert result is False

    def test_detect_app_type(self):
        """Test detect_app_type method."""
        runner = Runner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a requirements.txt file to simulate a Python app
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("flask==2.0.1\n")
            
            # Test Python app detection
            assert runner.detect_app_type(temp_dir) == "python"
            
            # Create a package.json file to simulate a Node.js app
            with open(os.path.join(temp_dir, "package.json"), "w") as f:
                f.write('{"name": "test-app", "version": "1.0.0"}')
            
            # Test Node.js app detection (should take precedence over Python)
            assert runner.detect_app_type(temp_dir) == "nodejs"
            
            # Create an index.php file to simulate a PHP app
            with open(os.path.join(temp_dir, "index.php"), "w") as f:
                f.write("<?php echo 'Hello World'; ?>")
            
            # Test PHP app detection
            assert runner.detect_app_type(temp_dir) == "php"
            
            # Create an index.html file to simulate a static HTML app
            with open(os.path.join(temp_dir, "index.html"), "w") as f:
                f.write("<html><body>Hello World</body></html>")
            
            # Test static HTML app detection
            assert runner.detect_app_type(temp_dir) == "html"
    
    @patch('infrash.core.runner.paramiko.SSHClient')
    def test_remote_deploy(self, mock_ssh_client):
        """Test remote_deploy method."""
        # Setup mocks
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client
        
        # Mock successful connection
        mock_client.connect.return_value = None
        
        # Mock successful command execution
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"Success"
        mock_stdin = MagicMock()
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        
        mock_channel = MagicMock()
        mock_channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr, mock_channel)
        
        runner = Runner()
        
        # Test successful remote deployment
        result = runner.remote_deploy(
            host="192.168.188.154",
            user="pi",
            password="raspberry",
            repo="https://github.com/UnitApi/mcp.git"
        )
        
        # Verify SSH connection was established
        mock_client.connect.assert_called_with(
            hostname="192.168.188.154",
            username="pi",
            password="raspberry"
        )
        
        # Verify commands were executed
        assert mock_client.exec_command.call_count >= 3  # At least system update, dependency install, and git clone
        
        # Verify result
        assert result is True
        
        # Test failed connection
        mock_client.connect.side_effect = Exception("Connection failed")
        
        result = runner.remote_deploy(
            host="192.168.1.154",  # Invalid IP
            user="pi",
            password="raspberry",
            repo="https://github.com/UnitApi/mcp.git"
        )
        
        # Verify result
        assert result is False
    
    @patch('infrash.core.runner.os.makedirs')
    @patch('infrash.core.runner.os.path.exists')
    @patch('infrash.core.runner.open', new_callable=MagicMock)
    def test_save_environment_variables(self, mock_open, mock_exists, mock_makedirs):
        """Test save_environment_variables method."""
        # Setup mocks
        mock_exists.return_value = False
        
        runner = Runner()
        
        # Test saving environment variables
        env_vars = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "API_KEY": "secret_key"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.save_environment_variables(temp_dir, env_vars)
            
            # Verify directory was created if it didn't exist
            mock_makedirs.assert_called_once_with(temp_dir, exist_ok=True)
            
            # Verify file was opened for writing
            mock_open.assert_called_once()
            
            # Verify result
            assert result is True
