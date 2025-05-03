"""
Tests for the GitRepo class in infrash.repo.git module.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from infrash.repo.git import GitRepo


class TestGitRepo:
    """Test suite for the GitRepo class."""

    def test_init(self):
        """Test GitRepo initialization."""
        repo = GitRepo()
        assert repo is not None

    @patch('infrash.repo.git.subprocess.run')
    def test_clone(self, mock_run):
        """Test clone method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test successful clone
            result = repo.clone("https://github.com/example/repo.git", temp_dir)
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_with(
                ["git", "clone", "https://github.com/example/repo.git", temp_dir],
                capture_output=True,
                text=True
            )
            
            # Verify result
            assert result is True
            
            # Test failed clone
            mock_process.returncode = 1
            result = repo.clone("https://github.com/example/nonexistent.git", temp_dir)
            assert result is False

    @patch('infrash.repo.git.subprocess.run')
    def test_pull(self, mock_run):
        """Test pull method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test successful pull
            result = repo.pull(temp_dir)
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_with(
                ["git", "pull"],
                cwd=temp_dir,
                capture_output=True,
                text=True
            )
            
            # Verify result
            assert result is True
            
            # Test failed pull
            mock_process.returncode = 1
            result = repo.pull(temp_dir)
            assert result is False

    @patch('infrash.repo.git.subprocess.run')
    def test_checkout(self, mock_run):
        """Test checkout method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test successful checkout
            result = repo.checkout(temp_dir, "main")
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_with(
                ["git", "checkout", "main"],
                cwd=temp_dir,
                capture_output=True,
                text=True
            )
            
            # Verify result
            assert result is True
            
            # Test failed checkout
            mock_process.returncode = 1
            result = repo.checkout(temp_dir, "nonexistent-branch")
            assert result is False

    @patch('infrash.repo.git.os.path.isdir')
    def test_is_git_repo(self, mock_isdir):
        """Test is_git_repo method."""
        # Setup mock
        mock_isdir.return_value = True
        
        repo = GitRepo()
        
        # Test when .git directory exists
        result = repo.is_git_repo("/path/to/repo")
        mock_isdir.assert_called_with(os.path.join("/path/to/repo", ".git"))
        assert result is True
        
        # Test when .git directory doesn't exist
        mock_isdir.return_value = False
        result = repo.is_git_repo("/path/to/repo")
        assert result is False

    @patch('infrash.repo.git.subprocess.run')
    def test_clone_with_unique_directory(self, mock_run):
        """Test clone_with_unique_directory method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test successful clone with unique directory
            result, target_dir = repo.clone_with_unique_directory(
                "https://github.com/UnitApi/mcp.git", 
                temp_dir
            )
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_with(
                ["git", "clone", "https://github.com/UnitApi/mcp.git", os.path.join(temp_dir, "mcp_1")],
                capture_output=True,
                text=True
            )
            
            # Verify result
            assert result is True
            assert target_dir == os.path.join(temp_dir, "mcp_1")
            
            # Test failed clone
            mock_process.returncode = 1
            result, target_dir = repo.clone_with_unique_directory(
                "https://github.com/example/nonexistent.git", 
                temp_dir
            )
            assert result is False
            assert target_dir is None

    @patch('infrash.repo.git.subprocess.run')
    def test_get_repo_info(self, mock_run):
        """Test get_repo_info method."""
        # Setup mock for remote URL
        mock_remote_process = MagicMock()
        mock_remote_process.returncode = 0
        mock_remote_process.stdout = "https://github.com/UnitApi/mcp.git"
        
        # Setup mock for current branch
        mock_branch_process = MagicMock()
        mock_branch_process.returncode = 0
        mock_branch_process.stdout = "main"
        
        # Setup mock for last commit
        mock_commit_process = MagicMock()
        mock_commit_process.returncode = 0
        mock_commit_process.stdout = "abcdef1234567890 Initial commit"
        
        # Set up the side effect to return different values for different calls
        mock_run.side_effect = [
            mock_remote_process,
            mock_branch_process,
            mock_commit_process
        ]
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test getting repo info
            info = repo.get_repo_info(temp_dir)
            
            # Verify subprocess.run was called for each piece of info
            assert mock_run.call_count == 3
            
            # Verify info was returned correctly
            assert info["remote_url"] == "https://github.com/UnitApi/mcp.git"
            assert info["current_branch"] == "main"
            assert info["last_commit"] == "abcdef1234567890 Initial commit"
            
            # Test failed info retrieval
            mock_run.side_effect = Exception("Command failed")
            
            info = repo.get_repo_info(temp_dir)
            
            # Verify default info was returned
            assert info["remote_url"] == "Unknown"
            assert info["current_branch"] == "Unknown"
            assert info["last_commit"] == "Unknown"

    @patch('infrash.repo.git.subprocess.run')
    def test_detect_repo_type(self, mock_run):
        """Test detect_repo_type method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "https://github.com/UnitApi/mcp.git"
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files to simulate different repo types
            
            # Python repo
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("flask==2.0.1\n")
            
            # Test Python repo detection
            repo_type = repo.detect_repo_type(temp_dir)
            assert repo_type == "python"
            
            # Node.js repo
            with open(os.path.join(temp_dir, "package.json"), "w") as f:
                f.write('{"name": "test-app", "version": "1.0.0"}')
            
            # Test Node.js repo detection (should take precedence)
            repo_type = repo.detect_repo_type(temp_dir)
            assert repo_type == "nodejs"
            
            # PHP repo
            with open(os.path.join(temp_dir, "composer.json"), "w") as f:
                f.write('{"name": "test/app", "require": {"php": ">=7.4"}}')
            
            # Test PHP repo detection
            repo_type = repo.detect_repo_type(temp_dir)
            assert repo_type == "php"
            
            # Remove all files
            os.remove(os.path.join(temp_dir, "requirements.txt"))
            os.remove(os.path.join(temp_dir, "package.json"))
            os.remove(os.path.join(temp_dir, "composer.json"))
            
            # Test unknown repo type
            repo_type = repo.detect_repo_type(temp_dir)
            assert repo_type == "unknown"

    @patch('infrash.repo.git.subprocess.run')
    def test_save_repo_config(self, mock_run):
        """Test save_repo_config method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test saving repo config
            config = {
                "repo_url": "https://github.com/UnitApi/mcp.git",
                "branch": "main",
                "last_update": "2025-05-03T21:58:12+02:00"
            }
            
            with patch('infrash.repo.git.open', new_callable=MagicMock) as mock_open:
                result = repo.save_repo_config(temp_dir, config)
                
                # Verify file was opened for writing
                mock_open.assert_called_once()
                
                # Verify result
                assert result is True
                
                # Test failed save
                mock_open.side_effect = Exception("Failed to write file")
                
                result = repo.save_repo_config(temp_dir, config)
                
                # Verify result
                assert result is False

    @patch('infrash.repo.git.subprocess.run')
    def test_load_repo_config(self, mock_run):
        """Test load_repo_config method."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        repo = GitRepo()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config file
            config_data = """{
                "repo_url": "https://github.com/UnitApi/mcp.git",
                "branch": "main",
                "last_update": "2025-05-03T21:58:12+02:00"
            }"""
            
            with patch('infrash.repo.git.open', new_callable=MagicMock) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = config_data
                
                # Test loading repo config
                config = repo.load_repo_config(temp_dir)
                
                # Verify file was opened for reading
                mock_open.assert_called_once()
                
                # Verify config was loaded correctly
                assert config["repo_url"] == "https://github.com/UnitApi/mcp.git"
                assert config["branch"] == "main"
                assert config["last_update"] == "2025-05-03T21:58:12+02:00"
                
                # Test failed load
                mock_open.side_effect = Exception("Failed to read file")
                
                config = repo.load_repo_config(temp_dir)
                
                # Verify default config was returned
                assert config == {}
