"""
Diagnostics engine for intelligent troubleshooting.
"""

import os
import re
import socket
import platform
import subprocess
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class DiagnosticsEngine:
    """
    Diagnostics engine for intelligent troubleshooting.
    
    This class provides functionality for:
    - Analyzing errors and providing solutions
    - Checking network connectivity
    - Verifying system requirements
    - Suggesting fixes for common issues
    """
    
    def __init__(self):
        """Initialize the diagnostics engine."""
        self.error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Load error patterns and solutions.
        
        Returns:
            Dictionary of error patterns and their solutions
        """
        return {
            # Git errors
            "destination path '(.+)' already exists": {
                "message": "The directory already exists",
                "solution": "Use a different directory name or remove the existing directory"
            },
            "Could not resolve host": {
                "message": "Network issue: Could not resolve host",
                "solution": "Check your internet connection and DNS settings"
            },
            "Permission denied \\(publickey\\)": {
                "message": "SSH authentication failed",
                "solution": "Check your SSH keys or use HTTPS URL instead"
            },
            
            # Python errors
            "No module named '(.+)'": {
                "message": "Python module not found",
                "solution": "Install the missing module with pip install {0}"
            },
            "ModuleNotFoundError: No module named '(.+)'": {
                "message": "Python module not found",
                "solution": "Install the missing module with pip install {0}"
            },
            
            # Node.js errors
            "Cannot find module '(.+)'": {
                "message": "Node.js module not found",
                "solution": "Install the missing module with npm install {0}"
            },
            "npm ERR! code ENOENT": {
                "message": "npm could not find package.json",
                "solution": "Make sure you're in the correct directory with a valid package.json file"
            },
            
            # PHP errors
            "PHP Fatal error: Uncaught Error: Class '(.+)' not found": {
                "message": "PHP class not found",
                "solution": "Make sure the class is properly autoloaded or included"
            },
            
            # Network errors
            "Address already in use": {
                "message": "Port is already in use",
                "solution": "Use a different port or stop the process using the current port"
            },
            "Unable to connect to port (\\d+) on (.+)": {
                "message": "Connection failed",
                "solution": "Check if the host is reachable and the port is correct"
            },
            
            # General errors
            "command not found": {
                "message": "Command not found",
                "solution": "Install the required tool or check if it's in your PATH"
            },
            "permission denied": {
                "message": "Permission denied",
                "solution": "Check file permissions or try running with sudo"
            }
        }
    
    def analyze_error(self, error_message: str) -> Optional[Dict[str, str]]:
        """
        Analyze an error message and provide a solution.
        
        Args:
            error_message: Error message to analyze
            
        Returns:
            Dictionary with error message and solution, or None if no match
        """
        for pattern, info in self.error_patterns.items():
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                message = info["message"]
                solution = info["solution"]
                
                # Format solution with captured groups if any
                if match.groups():
                    solution = solution.format(*match.groups())
                
                return {
                    "message": message,
                    "solution": solution
                }
        
        return None
    
    def check_network_connectivity(self, host: str, port: int = 22) -> Tuple[bool, str]:
        """
        Check network connectivity to a host.
        
        Args:
            host: Host to check
            port: Port to check (default: 22)
            
        Returns:
            Tuple (success, message): Whether the connection was successful and a message
        """
        try:
            # Try to resolve the hostname
            socket.gethostbyname(host)
            
            # Try to connect to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((host, port))
            
            return True, f"Successfully connected to {host}:{port}"
            
        except socket.gaierror:
            # Could not resolve hostname
            return False, f"Could not resolve hostname: {host}"
            
        except socket.timeout:
            # Connection timed out
            return False, f"Connection to {host}:{port} timed out"
            
        except ConnectionRefusedError:
            # Connection refused
            return False, f"Connection to {host}:{port} refused"
            
        except Exception as e:
            # Other error
            return False, f"Error connecting to {host}:{port}: {str(e)}"
    
    def check_system_requirements(self, requirements: List[str]) -> Dict[str, bool]:
        """
        Check if system meets requirements.
        
        Args:
            requirements: List of required tools
            
        Returns:
            Dictionary of requirements and whether they are met
        """
        result = {}
        
        for req in requirements:
            try:
                subprocess.run(
                    [req, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                result[req] = True
            except (FileNotFoundError, subprocess.SubprocessError):
                result[req] = False
        
        return result
    
    def diagnose_network_issue(self, host: str) -> Dict[str, Any]:
        """
        Diagnose network issues with a host.
        
        Args:
            host: Host to diagnose
            
        Returns:
            Dictionary with diagnosis results
        """
        results = {
            "host": host,
            "reachable": False,
            "dns_resolution": False,
            "suggestions": []
        }
        
        # Check DNS resolution
        try:
            ip = socket.gethostbyname(host)
            results["dns_resolution"] = True
            results["ip"] = ip
        except socket.gaierror:
            results["suggestions"].append("DNS resolution failed. Check if the hostname is correct.")
            
            # Try to suggest similar hostnames or common network ranges
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
                # It's an IP address
                ip_parts = host.split('.')
                if len(ip_parts) == 4:
                    # Suggest common local network ranges
                    common_networks = [
                        "192.168.0", "192.168.1", "192.168.188", "10.0.0", "10.0.1", "172.16.0"
                    ]
                    for network in common_networks:
                        if network != f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}":
                            results["suggestions"].append(
                                f"Try IP addresses in the {network}.0/24 network range."
                            )
        
        # Check if host is reachable
        if results["dns_resolution"]:
            try:
                # Try to ping the host
                if platform.system() == "Windows":
                    ping_cmd = ["ping", "-n", "1", "-w", "1000", host]
                else:
                    ping_cmd = ["ping", "-c", "1", "-W", "1", host]
                
                subprocess.run(
                    ping_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                results["reachable"] = True
            except subprocess.SubprocessError:
                results["suggestions"].append(
                    "Host is not responding to ping. Check if it's online and reachable."
                )
        
        return results
    
    def diagnose_port_issue(self, host: str, port: int) -> Dict[str, Any]:
        """
        Diagnose issues with a specific port on a host.
        
        Args:
            host: Host to diagnose
            port: Port to check
            
        Returns:
            Dictionary with diagnosis results
        """
        results = {
            "host": host,
            "port": port,
            "open": False,
            "suggestions": []
        }
        
        # Check if port is open
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((host, port))
            results["open"] = True
        except socket.timeout:
            results["suggestions"].append(
                f"Connection to {host}:{port} timed out. Check if the host is reachable."
            )
        except ConnectionRefusedError:
            results["suggestions"].append(
                f"Connection to {host}:{port} refused. Check if the service is running."
            )
        except Exception as e:
            results["suggestions"].append(
                f"Error connecting to {host}:{port}: {str(e)}"
            )
        
        return results
    
    def diagnose_git_issue(self, error_message: str, repo_url: str) -> Dict[str, Any]:
        """
        Diagnose issues with Git operations.
        
        Args:
            error_message: Error message from Git
            repo_url: Repository URL
            
        Returns:
            Dictionary with diagnosis results
        """
        results = {
            "repo_url": repo_url,
            "error": error_message,
            "suggestions": []
        }
        
        # Check for common Git errors
        if "destination path" in error_message and "already exists" in error_message:
            # Extract directory name
            match = re.search(r"destination path '(.+)' already exists", error_message)
            if match:
                dir_name = match.group(1)
                results["suggestions"].extend([
                    f"The directory '{dir_name}' already exists.",
                    f"Use a different directory name or remove the existing directory.",
                    f"You can also try: git -C {dir_name} pull to update the existing repository."
                ])
        
        elif "Could not resolve host" in error_message:
            results["suggestions"].extend([
                "Network issue: Could not resolve the host in the repository URL.",
                "Check your internet connection and DNS settings.",
                f"Verify that the repository URL is correct: {repo_url}"
            ])
        
        elif "Permission denied (publickey)" in error_message:
            results["suggestions"].extend([
                "SSH authentication failed.",
                "Check your SSH keys or use HTTPS URL instead.",
                f"For HTTPS, try: {repo_url.replace('git@github.com:', 'https://github.com/').replace('.git', '')}.git"
            ])
        
        elif "not found" in error_message:
            results["suggestions"].extend([
                "Repository not found.",
                "Check if the repository URL is correct and you have access to it.",
                "For private repositories, make sure you have the necessary permissions."
            ])
        
        else:
            # Generic suggestions
            results["suggestions"].extend([
                "Check if Git is installed and in your PATH.",
                "Verify that the repository URL is correct.",
                "Check your internet connection."
            ])
        
        return results
