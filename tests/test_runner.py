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
