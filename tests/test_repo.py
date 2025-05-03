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
