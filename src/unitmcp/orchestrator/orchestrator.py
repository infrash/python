"""
Main Orchestrator class for managing git repositories and running applications.
"""

import os
import sys
import logging
import subprocess
import platform
import shutil
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import tempfile
import importlib.util
import socket
from dotenv import load_dotenv, dotenv_values

from .project_detector import ProjectDetector
from .dependency_manager import DependencyManager
from .diagnostics import DiagnosticsEngine
from .network import NetworkManager

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Main orchestrator class for managing git repositories and running applications.
    
    This class provides functionality for:
    - Cloning git repositories
    - Detecting project types
    - Installing dependencies
    - Setting up environment variables
    - Running applications
    - Diagnosing and fixing common issues
    """
    
    def __init__(self, working_dir: str = None):
        """
        Initialize a new Orchestrator instance.
        
        Args:
            working_dir: Working directory for projects (optional)
        """
        self.working_dir = working_dir or os.path.join(os.path.expanduser("~"), "unitmcp_projects")
        os.makedirs(self.working_dir, exist_ok=True)
        
        self.project_detector = ProjectDetector()
        self.dependency_manager = DependencyManager()
        self.diagnostics = DiagnosticsEngine()
        self.network = NetworkManager()
        
        # Dictionary to store running processes
        self.processes = {}
        
        # Check if required tools are available
        self._check_required_tools()
    
    def _check_required_tools(self):
        """Check if required tools are available and install them if needed."""
        required_tools = ["git"]
        
        for tool in required_tools:
            if not self.dependency_manager.is_tool_available(tool):
                logger.info(f"{tool} is not installed. Attempting to install...")
                self.dependency_manager.install_tool(tool)
    
    def clone_repository(self, repo_url: str, target_dir: str = None) -> Tuple[bool, str]:
        """
        Clone a git repository.
        
        Args:
            repo_url: URL of the git repository
            target_dir: Target directory (optional)
            
        Returns:
            Tuple (success, path): Whether the operation was successful and the path to the cloned repo
        """
        if not self.dependency_manager.is_tool_available("git"):
            logger.error("Git is not installed in the system")
            return False, ""
        
        try:
            # Extract repository name from URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            
            # Determine target path
            timestamp = tempfile.NamedTemporaryFile().name.split('/')[-1]
            target_path = target_dir or os.path.join(self.working_dir, f"{repo_name}_{timestamp}")
            
            # Clone the repository
            logger.info(f"Cloning repository {repo_url}...")
            subprocess.run(
                ["git", "clone", repo_url, target_path],
                check=True
            )
            
            logger.info(f"Repository cloned to {target_path}")
            return True, target_path
            
        except subprocess.SubprocessError as e:
            error_msg = str(e)
            logger.error(f"Error while cloning repository: {error_msg}")
            
            # Provide intelligent suggestions based on the error
            if "already exists" in error_msg:
                logger.info("The directory already exists. Trying to use a different directory name...")
                return self.clone_repository(repo_url, os.path.join(self.working_dir, f"{repo_name}_new"))
            elif "Could not resolve host" in error_msg:
                logger.error("Network issue: Could not resolve host. Please check your internet connection.")
            elif "Permission denied" in error_msg:
                logger.error("Permission denied. Please check your SSH keys or use HTTPS URL.")
            
            return False, ""
    
    def process_project(self, repo_url: str, target_dir: str = None, port: int = None) -> Tuple[bool, Optional[subprocess.Popen]]:
        """
        Process a project from a git repository.
        
        Args:
            repo_url: URL of the git repository
            target_dir: Target directory (optional)
            port: Port to run the application on (optional)
            
        Returns:
            Tuple (success, process): Whether the operation was successful and the process object
        """
        # Clone the repository
        success, project_path = self.clone_repository(repo_url, target_dir)
        if not success:
            return False, None
        
        # Detect project type
        project_types = self.project_detector.detect_project_type(project_path)
        logger.info(f"Detected project types: {', '.join(project_types)}")
        
        if "unknown" in project_types:
            logger.warning("Could not detect project type. Trying to run as generic project.")
        
        # Set up environment variables
        self.setup_env_file(project_path)
        
        # Install dependencies for each detected project type
        for project_type in project_types:
            if project_type != "static":  # Static websites don't have dependencies
                if not self.dependency_manager.install_dependencies(project_path, project_type):
                    logger.warning(f"Failed to install dependencies for {project_type}")
        
        # Run the project (priority: web applications)
        for project_type in ["python", "node", "php", "ruby", "rust", "static"]:
            if project_type in project_types:
                success, process = self.run_project(project_path, project_type, port)
                if success:
                    return True, process
        
        logger.error("Failed to run any supported project type")
        return False, None
    
    def setup_env_file(self, project_path: str) -> bool:
        """
        Set up environment variables from .env file.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Whether the setup was successful
        """
        env_example_paths = [
            os.path.join(project_path, ".env.example"),
            os.path.join(project_path, ".env.sample"),
            os.path.join(project_path, "env.example")
        ]
        
        env_file = os.path.join(project_path, ".env")
        
        # Check if .env already exists
        if os.path.exists(env_file):
            logger.info(".env file already exists")
            # Load environment variables
            load_dotenv(env_file)
            return True
        
        # Look for example file
        example_file = None
        for path in env_example_paths:
            if os.path.exists(path):
                example_file = path
                break
        
        if not example_file:
            logger.info("No .env.example file found")
            return True
        
        logger.info(f"Setting up .env file based on {os.path.basename(example_file)}")
        
        try:
            # Read example file
            with open(example_file, 'r') as f:
                env_content = f.read()
            
            # Create new .env file
            with open(env_file, 'w') as f:
                for line in env_content.splitlines():
                    # Skip comments and empty lines
                    if line.strip().startswith('#') or not line.strip():
                        f.write(line + '\n')
                        continue
                    
                    # Check if line contains a variable
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        
                        # Ask user for value
                        user_value = input(f"Enter value for {key} [{value}]: ")
                        
                        # Use user value or default
                        final_value = user_value if user_value else value
                        f.write(f"{key}={final_value}\n")
                    else:
                        f.write(line + '\n')
            
            # Load environment variables
            load_dotenv(env_file)
            
            logger.info(".env file has been set up")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up .env file: {str(e)}")
            return False
    
    def run_project(self, project_path: str, project_type: str, port: int = None) -> Tuple[bool, Optional[subprocess.Popen]]:
        """
        Run a project.
        
        Args:
            project_path: Path to the project
            project_type: Type of project (python, node, php, ruby, rust, static)
            port: Port to run the application on (optional)
            
        Returns:
            Tuple (success, process): Whether the operation was successful and the process object
        """
        logger.info(f"Running project of type {project_type}...")
        
        # Find an available port if not specified
        if port is None:
            port = self._find_available_port(8000)
        
        try:
            if project_type == "python":
                return self._run_python_project(project_path, port)
            elif project_type == "node":
                return self._run_node_project(project_path, port)
            elif project_type == "php":
                return self._run_php_project(project_path, port)
            elif project_type == "ruby":
                return self._run_ruby_project(project_path, port)
            elif project_type == "rust":
                return self._run_rust_project(project_path, port)
            elif project_type == "static":
                return self._run_static_project(project_path, port)
            else:
                logger.error(f"Unsupported project type: {project_type}")
                return False, None
                
        except subprocess.SubprocessError as e:
            logger.error(f"Error running project: {str(e)}")
            return False, None
    
    def _find_available_port(self, start_port: int) -> int:
        """
        Find an available port starting from the given port.
        
        Args:
            start_port: Starting port number
            
        Returns:
            Available port number
        """
        port = start_port
        while port < start_port + 100:  # Try up to 100 ports
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                port += 1
        
        # If no port is available, return the start port and let the application handle it
        return start_port
    
    def _run_python_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a Python project."""
        # Check for different possible entry points
        entry_points = [
            # Flask
            ("app.py", ["python", "app.py"]),
            ("wsgi.py", ["python", "wsgi.py"]),
            ("main.py", ["python", "main.py"]),
            # Django
            ("manage.py", ["python", "manage.py", "runserver", f"0.0.0.0:{port}"]),
            # FastAPI
            ("main.py", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port)])
        ]
        
        for file_name, command in entry_points:
            if os.path.exists(os.path.join(project_path, file_name)):
                # Check if using virtualenv
                venv_path = os.path.join(project_path, "venv")
                if os.path.exists(venv_path):
                    if platform.system() == "Windows":
                        python_path = os.path.join(venv_path, "Scripts", "python.exe")
                        if "python" in command[0]:
                            command[0] = python_path
                    else:
                        python_path = os.path.join(venv_path, "bin", "python")
                        if "python" in command[0]:
                            command[0] = python_path
                        elif command[0] in ["uvicorn"]:
                            command[0] = os.path.join(venv_path, "bin", command[0])
                
                # Add port if provided and not already in command
                if port and "--port" not in command and "runserver" not in command:
                    command.extend(["--port", str(port)])
                
                process = subprocess.Popen(
                    command,
                    cwd=project_path
                )
                logger.info(f"Started Python application: {' '.join(command)}")
                return True, process
        
        logger.error("No entry point found for Python application")
        return False, None
    
    def _run_node_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a Node.js project."""
        # Check package.json
        package_json_path = os.path.join(project_path, "package.json")
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Check scripts
            if "scripts" in package_data:
                if "start" in package_data["scripts"]:
                    # Set PORT environment variable
                    env = os.environ.copy()
                    env["PORT"] = str(port)
                    
                    process = subprocess.Popen(
                        ["npm", "start"],
                        cwd=project_path,
                        env=env
                    )
                    logger.info("Started Node.js application: npm start")
                    return True, process
                elif "dev" in package_data["scripts"]:
                    # Set PORT environment variable
                    env = os.environ.copy()
                    env["PORT"] = str(port)
                    
                    process = subprocess.Popen(
                        ["npm", "run", "dev"],
                        cwd=project_path,
                        env=env
                    )
                    logger.info("Started Node.js application: npm run dev")
                    return True, process
        
        # Check app.js or server.js
        entry_points = ["app.js", "server.js", "index.js"]
        for entry_point in entry_points:
            if os.path.exists(os.path.join(project_path, entry_point)):
                # Set PORT environment variable
                env = os.environ.copy()
                env["PORT"] = str(port)
                
                process = subprocess.Popen(
                    ["node", entry_point],
                    cwd=project_path,
                    env=env
                )
                logger.info(f"Started Node.js application: node {entry_point}")
                return True, process
        
        logger.error("No entry point found for Node.js application")
        return False, None
    
    def _run_php_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a PHP project."""
        # Check if Laravel project
        if os.path.exists(os.path.join(project_path, "artisan")):
            process = subprocess.Popen(
                ["php", "artisan", "serve", f"--host=0.0.0.0", f"--port={port}"],
                cwd=project_path
            )
            logger.info("Started Laravel application")
            return True, process
        # Built-in PHP server
        else:
            public_dir = os.path.join(project_path, "public")
            serve_dir = public_dir if os.path.exists(public_dir) else project_path
            process = subprocess.Popen(
                ["php", "-S", f"0.0.0.0:{port}"],
                cwd=serve_dir
            )
            logger.info(f"Started built-in PHP server in directory {serve_dir}")
            return True, process
    
    def _run_ruby_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a Ruby project."""
        # Check if Rails project
        if os.path.exists(os.path.join(project_path, "bin", "rails")):
            process = subprocess.Popen(
                ["bundle", "exec", "rails", "server", "-p", str(port), "-b", "0.0.0.0"],
                cwd=project_path
            )
            logger.info("Started Ruby on Rails application")
            return True, process
        # Check if Sinatra/Rack
        elif any(os.path.exists(os.path.join(project_path, f)) for f in ["app.rb", "config.ru"]):
            process = subprocess.Popen(
                ["bundle", "exec", "rackup", "-p", str(port), "-o", "0.0.0.0"],
                cwd=project_path
            )
            logger.info("Started Ruby/Rack application")
            return True, process
        
        logger.error("No entry point found for Ruby application")
        return False, None
    
    def _run_rust_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a Rust project."""
        # Compile project
        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=project_path,
            check=True
        )
        
        # Check Cargo.toml to find binary name
        with open(os.path.join(project_path, "Cargo.toml"), 'r') as f:
            cargo_content = f.read()
        
        binary_name = None
        match = re.search(r'name\s*=\s*"([^"]+)"', cargo_content)
        if match:
            binary_name = match.group(1)
        
        if binary_name:
            binary_path = os.path.join(project_path, "target", "release", binary_name)
            if platform.system() == "Windows":
                binary_path += ".exe"
            
            if os.path.exists(binary_path):
                # Set PORT environment variable
                env = os.environ.copy()
                env["PORT"] = str(port)
                
                process = subprocess.Popen(
                    [binary_path],
                    cwd=project_path,
                    env=env
                )
                logger.info(f"Started Rust application: {binary_path}")
                return True, process
        
        logger.error("No compiled Rust application found")
        return False, None
    
    def _run_static_project(self, project_path: str, port: int) -> Tuple[bool, Optional[subprocess.Popen]]:
        """Run a static website."""
        # Use Python's built-in HTTP server
        process = subprocess.Popen(
            ["python", "-m", "http.server", str(port)],
            cwd=project_path
        )
        logger.info(f"Started HTTP server on port {port}")
        return True, process
