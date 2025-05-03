"""
Dependency management module.
"""

import os
import sys
import subprocess
import platform
import logging
import importlib.util
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class DependencyManager:
    """
    Class for managing dependencies and tools.
    """
    
    def __init__(self):
        """Initialize the dependency manager."""
        self.available_tools = self._detect_tools()
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available tools in the system."""
        tools = {
            "git": self.is_tool_available("git"),
            "python": self.is_tool_available("python") or self.is_tool_available("python3"),
            "pip": self.is_tool_available("pip") or self.is_tool_available("pip3"),
            "node": self.is_tool_available("node"),
            "npm": self.is_tool_available("npm"),
            "php": self.is_tool_available("php"),
            "composer": self.is_tool_available("composer"),
            "ruby": self.is_tool_available("ruby"),
            "bundle": self.is_tool_available("bundle"),
            "cargo": self.is_tool_available("cargo"),
            "rustc": self.is_tool_available("rustc")
        }
        return tools
    
    def is_tool_available(self, command: str) -> bool:
        """
        Check if a command is available in the system.
        
        Args:
            command: Command to check
            
        Returns:
            Whether the command is available
        """
        try:
            subprocess.run(
                [command, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def install_tool(self, tool: str) -> bool:
        """
        Install a tool.
        
        Args:
            tool: Tool to install
            
        Returns:
            Whether the installation was successful
        """
        system = platform.system()
        
        try:
            if system == "Linux":
                # Detect package manager
                if self.is_tool_available("apt-get"):
                    subprocess.run(["sudo", "apt-get", "update"], check=True)
                    subprocess.run(["sudo", "apt-get", "install", "-y", tool], check=True)
                elif self.is_tool_available("yum"):
                    subprocess.run(["sudo", "yum", "install", "-y", tool], check=True)
                elif self.is_tool_available("dnf"):
                    subprocess.run(["sudo", "dnf", "install", "-y", tool], check=True)
                elif self.is_tool_available("pacman"):
                    subprocess.run(["sudo", "pacman", "-S", "--noconfirm", tool], check=True)
                else:
                    logger.error("Unsupported package manager")
                    return False
            
            elif system == "Darwin":  # macOS
                if self.is_tool_available("brew"):
                    subprocess.run(["brew", "install", tool], check=True)
                else:
                    logger.error("Homebrew not found. Please install Homebrew first.")
                    return False
            
            elif system == "Windows":
                if self.is_tool_available("choco"):
                    subprocess.run(["choco", "install", "-y", tool], check=True)
                elif self.is_tool_available("scoop"):
                    subprocess.run(["scoop", "install", tool], check=True)
                else:
                    logger.error("Chocolatey or Scoop not found. Please install one of them first.")
                    return False
            
            else:
                logger.error(f"Unsupported operating system: {system}")
                return False
            
            # Update available tools
            self.available_tools[tool] = True
            return True
            
        except subprocess.SubprocessError as e:
            logger.error(f"Error installing {tool}: {str(e)}")
            return False
    
    def install_dependencies(self, project_path: str, project_type: str) -> bool:
        """
        Install dependencies for a project.
        
        Args:
            project_path: Path to the project
            project_type: Type of project (python, node, php, ruby, rust)
            
        Returns:
            Whether the installation was successful
        """
        logger.info(f"Installing dependencies for {project_type} project...")
        
        try:
            if project_type == "python":
                return self._install_python_dependencies(project_path)
            elif project_type == "node":
                return self._install_node_dependencies(project_path)
            elif project_type == "php":
                return self._install_php_dependencies(project_path)
            elif project_type == "ruby":
                return self._install_ruby_dependencies(project_path)
            elif project_type == "rust":
                return self._install_rust_dependencies(project_path)
            else:
                logger.error(f"Unsupported project type: {project_type}")
                return False
                
        except subprocess.SubprocessError as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return False
    
    def _install_python_dependencies(self, project_path: str) -> bool:
        """Install Python dependencies."""
        if not self.available_tools["pip"]:
            logger.error("pip is not installed")
            if not self.install_tool("python3-pip"):
                return False
        
        # Check if using virtualenv
        venv_path = os.path.join(project_path, "venv")
        if not os.path.exists(venv_path):
            # Create virtualenv
            if self.available_tools["python"]:
                subprocess.run(
                    ["python", "-m", "venv", venv_path],
                    check=True
                )
        
        # Determine Python interpreter path
        python_cmd = os.path.join(venv_path, "bin", "python") if os.path.exists(venv_path) else "python"
        if platform.system() == "Windows" and os.path.exists(venv_path):
            python_cmd = os.path.join(venv_path, "Scripts", "python.exe")
        
        # Install dependencies
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            subprocess.run(
                [python_cmd, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=project_path,
                check=True
            )
        elif os.path.exists(os.path.join(project_path, "setup.py")):
            subprocess.run(
                [python_cmd, "-m", "pip", "install", "-e", "."],
                cwd=project_path,
                check=True
            )
        elif os.path.exists(os.path.join(project_path, "pyproject.toml")):
            subprocess.run(
                [python_cmd, "-m", "pip", "install", "-e", "."],
                cwd=project_path,
                check=True
            )
        
        return True
    
    def _install_node_dependencies(self, project_path: str) -> bool:
        """Install Node.js dependencies."""
        if not self.available_tools["npm"]:
            logger.error("npm is not installed")
            if not self.install_tool("nodejs"):
                return False
        
        subprocess.run(
            ["npm", "install"],
            cwd=project_path,
            check=True
        )
        
        return True
    
    def _install_php_dependencies(self, project_path: str) -> bool:
        """Install PHP dependencies."""
        if os.path.exists(os.path.join(project_path, "composer.json")):
            if not self.available_tools["composer"]:
                logger.error("composer is not installed")
                if not self.install_tool("composer"):
                    return False
            
            subprocess.run(
                ["composer", "install"],
                cwd=project_path,
                check=True
            )
        
        return True
    
    def _install_ruby_dependencies(self, project_path: str) -> bool:
        """Install Ruby dependencies."""
        if not self.available_tools["bundle"]:
            logger.error("bundler is not installed")
            if not self.install_tool("ruby-bundler"):
                return False
        
        subprocess.run(
            ["bundle", "install"],
            cwd=project_path,
            check=True
        )
        
        return True
    
    def _install_rust_dependencies(self, project_path: str) -> bool:
        """Install Rust dependencies."""
        if not self.available_tools["cargo"]:
            logger.error("cargo is not installed")
            if not self.install_tool("rust"):
                return False
        
        subprocess.run(
            ["cargo", "build"],
            cwd=project_path,
            check=True
        )
        
        return True
