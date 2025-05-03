"""
Tests for the Orchestrator class in unitmcp.orchestrator.orchestrator module.
"""

import os
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from unitmcp.orchestrator.orchestrator import Orchestrator


class TestOrchestrator:
    """Test suite for the Orchestrator class."""

    def test_init(self):
        """Test Orchestrator initialization."""
        with patch('unitmcp.orchestrator.orchestrator.Orchestrator._check_required_tools'):
            orchestrator = Orchestrator()
            assert orchestrator is not None
            assert hasattr(orchestrator, 'project_detector')
            assert hasattr(orchestrator, 'dependency_manager')
            assert hasattr(orchestrator, 'diagnostics')
            assert hasattr(orchestrator, 'network')

    @patch('unitmcp.orchestrator.orchestrator.shutil.which')
    @patch('unitmcp.orchestrator.orchestrator.subprocess.run')
    def test_check_required_tools_all_available(self, mock_run, mock_which):
        """Test checking required tools - all available."""
        # Setup mock to indicate all tools are available
        mock_which.return_value = "/usr/bin/tool"
        
        orchestrator = Orchestrator()
        
        # Verify shutil.which was called for each required tool
        assert mock_which.call_count >= 3  # At least git, python, pip
        # Verify subprocess.run was not called (no need to install anything)
        mock_run.assert_not_called()

    @patch('unitmcp.orchestrator.orchestrator.shutil.which')
    @patch('unitmcp.orchestrator.orchestrator.subprocess.run')
    @patch('unitmcp.orchestrator.orchestrator.platform.system')
    def test_check_required_tools_some_missing_linux(self, mock_system, mock_run, mock_which):
        """Test checking required tools - some missing on Linux."""
        # Setup mocks
        mock_system.return_value = "Linux"
        
        # Make git available but python and pip missing
        def which_side_effect(tool):
            return "/usr/bin/git" if tool == "git" else None
        
        mock_which.side_effect = which_side_effect
        
        orchestrator = Orchestrator()
        
        # Verify shutil.which was called for each required tool
        assert mock_which.call_count >= 3
        # Verify subprocess.run was called to install missing tools
        assert mock_run.call_count >= 1

    @patch('unitmcp.orchestrator.orchestrator.subprocess.run')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    def test_clone_repository_new(self, mock_exists, mock_run):
        """Test cloning a new repository."""
        # Setup mocks
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        
        orchestrator = Orchestrator()
        success, path = orchestrator.clone_repository("https://github.com/UnitApi/test.git")
        
        assert success is True
        assert path is not None
        assert "test" in path
        mock_exists.assert_called_once()
        mock_run.assert_called_once()
        # Verify git clone was called
        assert "git" in mock_run.call_args[0][0][0]
        assert "clone" in mock_run.call_args[0][0][1]

    @patch('unitmcp.orchestrator.orchestrator.subprocess.run')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    def test_clone_repository_existing_update(self, mock_exists, mock_run):
        """Test updating an existing repository."""
        # Setup mocks
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        
        orchestrator = Orchestrator()
        success, path = orchestrator.clone_repository("https://github.com/UnitApi/test.git")
        
        assert success is True
        assert path is not None
        assert "test" in path
        mock_exists.assert_called_once()
        mock_run.assert_called_once()
        # Verify git pull was called
        assert "git" in mock_run.call_args[0][0][0]
        assert "pull" in mock_run.call_args[0][0][1]

    @patch('unitmcp.orchestrator.orchestrator.subprocess.run')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    def test_clone_repository_error(self, mock_exists, mock_run):
        """Test cloning a repository with an error."""
        # Setup mocks
        mock_exists.return_value = False
        mock_run.side_effect = subprocess.SubprocessError("Git error")
        
        with patch('unitmcp.orchestrator.orchestrator.DiagnosticsEngine.diagnose_git_issue') as mock_diagnose:
            mock_diagnose.return_value = {"suggestions": ["Try a different URL"]}
            
            orchestrator = Orchestrator()
            success, path = orchestrator.clone_repository("https://github.com/UnitApi/nonexistent.git")
            
            assert success is False
            assert path is None
            mock_exists.assert_called_once()
            mock_run.assert_called_once()
            mock_diagnose.assert_called_once()

    def test_detect_project_type(self):
        """Test detecting project type."""
        with patch('unitmcp.orchestrator.project_detector.ProjectDetector.detect_project_type') as mock_detect:
            mock_detect.return_value = ["python", "flask"]
            
            orchestrator = Orchestrator()
            project_types = orchestrator.detect_project_type("/path/to/project")
            
            assert project_types == ["python", "flask"]
            mock_detect.assert_called_once_with("/path/to/project")

    def test_install_dependencies(self):
        """Test installing dependencies."""
        with patch('unitmcp.orchestrator.dependency_manager.DependencyManager.install_dependencies') as mock_install:
            mock_install.return_value = True
            
            orchestrator = Orchestrator()
            success = orchestrator.install_dependencies("/path/to/project", ["python"])
            
            assert success is True
            mock_install.assert_called_once_with("/path/to/project", ["python"])

    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="KEY=value\nDEBUG=true")
    def test_setup_environment_with_env_example(self, mock_file, mock_exists):
        """Test setting up environment variables with .env.example file."""
        # Setup mocks
        mock_exists.return_value = True
        
        orchestrator = Orchestrator()
        env_vars = orchestrator.setup_environment("/path/to/project")
        
        assert env_vars == {"KEY": "value", "DEBUG": "true"}
        mock_exists.assert_called_once()
        mock_file.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    def test_setup_environment_without_env_example(self, mock_exists):
        """Test setting up environment variables without .env.example file."""
        # Setup mock
        mock_exists.return_value = False
        
        orchestrator = Orchestrator()
        env_vars = orchestrator.setup_environment("/path/to/project")
        
        assert env_vars == {}
        mock_exists.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.subprocess.Popen')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.setup_environment')
    def test_run_application_python(self, mock_setup_env, mock_exists, mock_popen):
        """Test running a Python application."""
        # Setup mocks
        mock_setup_env.return_value = {"DEBUG": "true"}
        
        # Make app.py exist
        def exists_side_effect(path):
            return "app.py" in path
        
        mock_exists.side_effect = exists_side_effect
        
        # Mock successful process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        orchestrator = Orchestrator()
        process = orchestrator.run_application("/path/to/project", ["python"], 5000)
        
        assert process is mock_process
        mock_setup_env.assert_called_once()
        assert mock_exists.call_count >= 1
        mock_popen.assert_called_once()
        # Verify python command was used
        assert "python" in mock_popen.call_args[0][0][0]
        assert "app.py" in mock_popen.call_args[0][0][1]

    @patch('unitmcp.orchestrator.orchestrator.subprocess.Popen')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.setup_environment')
    def test_run_application_node(self, mock_setup_env, mock_exists, mock_popen):
        """Test running a Node.js application."""
        # Setup mocks
        mock_setup_env.return_value = {}
        
        # Make package.json exist
        def exists_side_effect(path):
            return "package.json" in path
        
        mock_exists.side_effect = exists_side_effect
        
        # Mock successful process start
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock reading package.json
        with patch('builtins.open', mock_open(read_data='{"scripts": {"start": "node server.js"}}')):
            with patch('json.load') as mock_json_load:
                mock_json_load.return_value = {"scripts": {"start": "node server.js"}}
                
                orchestrator = Orchestrator()
                process = orchestrator.run_application("/path/to/project", ["node"], 3000)
                
                assert process is mock_process
                mock_setup_env.assert_called_once()
                assert mock_exists.call_count >= 1
                mock_popen.assert_called_once()
                # Verify npm command was used
                assert "npm" in mock_popen.call_args[0][0][0]
                assert "start" in mock_popen.call_args[0][0][1]

    @patch('unitmcp.orchestrator.orchestrator.subprocess.Popen')
    @patch('unitmcp.orchestrator.orchestrator.os.path.exists')
    def test_run_application_process_failure(self, mock_exists, mock_popen):
        """Test running an application that fails to start."""
        # Setup mocks
        mock_exists.return_value = True
        
        # Mock process that fails to start
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Non-zero exit code
        mock_process.communicate.return_value = ("", "Error: Could not start")
        mock_popen.return_value = mock_process
        
        with patch('unitmcp.orchestrator.orchestrator.DiagnosticsEngine.analyze_error') as mock_analyze:
            mock_analyze.return_value = {
                "message": "Application failed to start",
                "solution": "Check the configuration"
            }
            
            orchestrator = Orchestrator()
            process = orchestrator.run_application("/path/to/project", ["python"], 5000)
            
            assert process is None
            mock_popen.assert_called_once()
            mock_process.communicate.assert_called_once()
            mock_analyze.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.clone_repository')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.detect_project_type')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.install_dependencies')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.run_application')
    def test_process_project_success(self, mock_run, mock_install, mock_detect, mock_clone):
        """Test processing a project - success case."""
        # Setup mocks
        mock_clone.return_value = (True, "/path/to/project")
        mock_detect.return_value = ["python"]
        mock_install.return_value = True
        mock_process = MagicMock()
        mock_run.return_value = mock_process
        
        orchestrator = Orchestrator()
        success, process = orchestrator.process_project("https://github.com/UnitApi/test.git")
        
        assert success is True
        assert process is mock_process
        mock_clone.assert_called_once()
        mock_detect.assert_called_once()
        mock_install.assert_called_once()
        mock_run.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.clone_repository')
    def test_process_project_clone_failure(self, mock_clone):
        """Test processing a project - clone failure."""
        # Setup mock
        mock_clone.return_value = (False, None)
        
        orchestrator = Orchestrator()
        success, process = orchestrator.process_project("https://github.com/UnitApi/nonexistent.git")
        
        assert success is False
        assert process is None
        mock_clone.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.clone_repository')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.detect_project_type')
    def test_process_project_detect_failure(self, mock_detect, mock_clone):
        """Test processing a project - detect failure."""
        # Setup mocks
        mock_clone.return_value = (True, "/path/to/project")
        mock_detect.return_value = []  # No project types detected
        
        orchestrator = Orchestrator()
        success, process = orchestrator.process_project("https://github.com/UnitApi/test.git")
        
        assert success is False
        assert process is None
        mock_clone.assert_called_once()
        mock_detect.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.clone_repository')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.detect_project_type')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.install_dependencies')
    def test_process_project_install_failure(self, mock_install, mock_detect, mock_clone):
        """Test processing a project - install failure."""
        # Setup mocks
        mock_clone.return_value = (True, "/path/to/project")
        mock_detect.return_value = ["python"]
        mock_install.return_value = False  # Installation failed
        
        orchestrator = Orchestrator()
        success, process = orchestrator.process_project("https://github.com/UnitApi/test.git")
        
        assert success is False
        assert process is None
        mock_clone.assert_called_once()
        mock_detect.assert_called_once()
        mock_install.assert_called_once()

    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.clone_repository')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.detect_project_type')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.install_dependencies')
    @patch('unitmcp.orchestrator.orchestrator.Orchestrator.run_application')
    def test_process_project_run_failure(self, mock_run, mock_install, mock_detect, mock_clone):
        """Test processing a project - run failure."""
        # Setup mocks
        mock_clone.return_value = (True, "/path/to/project")
        mock_detect.return_value = ["python"]
        mock_install.return_value = True
        mock_run.return_value = None  # Run failed
        
        orchestrator = Orchestrator()
        success, process = orchestrator.process_project("https://github.com/UnitApi/test.git")
        
        assert success is False
        assert process is None
        mock_clone.assert_called_once()
        mock_detect.assert_called_once()
        mock_install.assert_called_once()
        mock_run.assert_called_once()
