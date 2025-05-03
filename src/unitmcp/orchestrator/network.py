"""
Network management module.
"""

import os
import socket
import subprocess
import logging
import platform
import re
import paramiko
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Network management class for handling SSH connections and remote operations.
    """
    
    def __init__(self):
        """Initialize the network manager."""
        # Check if paramiko is installed
        try:
            import paramiko
        except ImportError:
            logger.warning("Paramiko is not installed. SSH functionality will be limited.")
    
    def connect_ssh(self, host: str, username: str, password: str = None, 
                   key_filename: str = None, port: int = 22) -> Tuple[bool, Optional[paramiko.SSHClient]]:
        """
        Connect to a remote host via SSH.
        
        Args:
            host: Hostname or IP address
            username: SSH username
            password: SSH password (optional if using key authentication)
            key_filename: Path to SSH private key file (optional)
            port: SSH port (default: 22)
            
        Returns:
            Tuple (success, client): Whether the connection was successful and the SSH client
        """
        try:
            # Check if paramiko is installed
            import paramiko
        except ImportError:
            logger.error("Paramiko is not installed. Installing it now...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "paramiko"],
                    check=True
                )
                import paramiko
            except Exception as e:
                logger.error(f"Failed to install paramiko: {str(e)}")
                return False, None
        
        try:
            logger.info(f"Connecting to {host} as {username}...")
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh_client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=10
            )
            
            logger.info("SSH connection established successfully")
            return True, ssh_client
            
        except paramiko.AuthenticationException:
            logger.error("Authentication failed. Check your credentials.")
            return False, None
            
        except paramiko.SSHException as e:
            logger.error(f"SSH error: {str(e)}")
            return False, None
            
        except socket.error as e:
            logger.error(f"Socket error: {str(e)}")
            
            # Provide intelligent suggestions based on the error
            error_str = str(e)
            if "No route to host" in error_str:
                logger.error("Host is unreachable. Check if it's online and connected to the network.")
            elif "Connection refused" in error_str:
                logger.error("Connection refused. Check if SSH service is running on the host.")
            elif "timed out" in error_str:
                logger.error("Connection timed out. Check if host is reachable and SSH port is open.")
            elif "Unable to connect" in error_str and "port 22" in error_str:
                # Check if the IP address is valid for the network
                self._suggest_network_fix(host)
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error connecting to SSH: {str(e)}")
            return False, None
    
    def _suggest_network_fix(self, host: str):
        """
        Suggest network fixes based on the host address.
        
        Args:
            host: Hostname or IP address
        """
        # Check if it's an IP address
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
            ip_parts = host.split('.')
            if len(ip_parts) == 4:
                # Get local IP address
                local_ip = self._get_local_ip()
                if local_ip:
                    local_parts = local_ip.split('.')
                    if len(local_parts) == 4:
                        # Check if the network part matches
                        if local_parts[0:3] != ip_parts[0:3]:
                            logger.error(
                                f"The IP address {host} appears to be on a different network than your local "
                                f"network ({local_ip}). Check if the IP address is correct."
                            )
                            logger.info(f"Your local network is {local_parts[0]}.{local_parts[1]}.{local_parts[2]}.0/24")
                            logger.info(f"Try using an IP address in the same network, e.g., "
                                       f"{local_parts[0]}.{local_parts[1]}.{local_parts[2]}.{ip_parts[3]}")
    
    def _get_local_ip(self) -> Optional[str]:
        """
        Get the local IP address.
        
        Returns:
            Local IP address or None if not found
        """
        try:
            # Create a socket to determine the local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return None
    
    def setup_remote_environment(self, ssh_client, repo_url: str) -> bool:
        """
        Set up remote environment and install the project.
        
        Args:
            ssh_client: Connected SSH client
            repo_url: URL of the Git repository to install
            
        Returns:
            Whether the setup was successful
        """
        try:
            # Update system
            logger.info("Updating remote system...")
            stdin, stdout, stderr = ssh_client.exec_command('sudo apt-get update && sudo apt-get upgrade -y')
            stdout.channel.recv_exit_status()
            
            # Install dependencies
            logger.info("Installing system dependencies...")
            stdin, stdout, stderr = ssh_client.exec_command(
                'sudo apt-get install -y git python3 python3-pip python3-venv'
            )
            stdout.channel.recv_exit_status()
            
            # Create a unique directory for the project
            timestamp = self._get_timestamp()
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            project_dir = f"{repo_name}_{timestamp}"
            
            # Clone repository
            logger.info(f"Cloning repository {repo_url}...")
            stdin, stdout, stderr = ssh_client.exec_command(f'git clone {repo_url} {project_dir}')
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error = stderr.read().decode()
                logger.error(f"Error cloning repository: {error}")
                return False
            
            # Create virtual environment
            logger.info("Creating virtual environment...")
            stdin, stdout, stderr = ssh_client.exec_command(
                f'cd {project_dir} && python3 -m venv venv'
            )
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                logger.error(f"Error creating virtual environment: {stderr.read().decode()}")
                return False
            
            # Install requirements
            logger.info("Installing requirements...")
            stdin, stdout, stderr = ssh_client.exec_command(
                f'cd {project_dir} && source venv/bin/activate && pip install -r requirements.txt'
            )
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                logger.error(f"Error installing requirements: {stderr.read().decode()}")
                return False
            
            # Save environment information
            self._save_env_info(ssh_client, project_dir, repo_url)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up remote environment: {str(e)}")
            return False
    
    def _get_timestamp(self) -> str:
        """
        Get a timestamp string.
        
        Returns:
            Timestamp string
        """
        import time
        return str(int(time.time()))
    
    def _save_env_info(self, ssh_client, project_dir: str, repo_url: str):
        """
        Save environment information to a .env file.
        
        Args:
            ssh_client: Connected SSH client
            project_dir: Project directory
            repo_url: Repository URL
        """
        env_content = f"""# Environment information
PROJECT_DIR={project_dir}
REPO_URL={repo_url}
INSTALL_DATE={self._get_timestamp()}
"""
        
        # Create .env file
        stdin, stdout, stderr = ssh_client.exec_command(f'echo "{env_content}" > {project_dir}/.env')
        stdout.channel.recv_exit_status()
        
        # Also save locally
        local_env_dir = os.path.join(os.path.expanduser("~"), ".unitmcp")
        os.makedirs(local_env_dir, exist_ok=True)
        
        local_env_file = os.path.join(local_env_dir, f"{project_dir}.env")
        with open(local_env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"Environment information saved to {local_env_file}")
    
    def run_remote_command(self, ssh_client, command: str) -> Tuple[bool, str, str]:
        """
        Run a command on the remote host.
        
        Args:
            ssh_client: Connected SSH client
            command: Command to run
            
        Returns:
            Tuple (success, stdout, stderr): Whether the command was successful, stdout and stderr
        """
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_str = stdout.read().decode()
            stderr_str = stderr.read().decode()
            
            if exit_status == 0:
                return True, stdout_str, stderr_str
            else:
                return False, stdout_str, stderr_str
                
        except Exception as e:
            logger.error(f"Error running remote command: {str(e)}")
            return False, "", str(e)
