"""
Example of deploying an application to a remote host using the orchestrator.
"""

import sys
import logging
import argparse
from unitmcp.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Deploy an application to a remote host."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Deploy an application to a remote host')
    parser.add_argument('--host', type=str, required=True, help='Hostname or IP address')
    parser.add_argument('--user', type=str, required=True, help='SSH username')
    parser.add_argument('--password', type=str, help='SSH password (optional if using key authentication)')
    parser.add_argument('--key', type=str, help='Path to SSH private key file (optional)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--repo', type=str, required=True, help='Repository URL')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = Orchestrator()
    
    # Connect to the remote host
    logger.info(f"Connecting to {args.host} as {args.user}...")
    success, ssh_client = orchestrator.network.connect_ssh(
        host=args.host,
        username=args.user,
        password=args.password,
        key_filename=args.key,
        port=args.port
    )
    
    if not success:
        logger.error("Failed to connect to remote host")
        return 1
    
    try:
        # Set up the remote environment
        logger.info(f"Setting up remote environment for {args.repo}...")
        success = orchestrator.network.setup_remote_environment(ssh_client, args.repo)
        
        if success:
            logger.info("Remote setup completed successfully")
        else:
            logger.error("Remote setup failed")
            return 1
            
    finally:
        # Close the SSH connection
        ssh_client.close()
        logger.info("SSH connection closed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
