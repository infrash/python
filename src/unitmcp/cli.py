"""
Command-line interface for unitmcp.
"""

import os
import sys
import argparse
import logging
import signal
import time
from typing import Dict, List, Optional, Any

from .orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unitmcp.log')
    ]
)

logger = logging.getLogger(__name__)

def handle_exit(signum, frame):
    """Handle termination signals gracefully."""
    logger.info("Shutting down...")
    sys.exit(0)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Universal Tool for Managing and Configuring Projects')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Clone and run a project')
    run_parser.add_argument('--repo', type=str, required=True,
                          help='URL of the Git repository to clone and run')
    run_parser.add_argument('--port', type=int, default=None,
                          help='Port to run the project on (optional)')
    run_parser.add_argument('--target', type=str, default=None,
                          help='Target directory for the repository (optional)')
    
    # Remote command
    remote_parser = subparsers.add_parser('remote', help='Run a project on a remote host')
    remote_parser.add_argument('--host', type=str, required=True,
                             help='Hostname or IP address of the remote host')
    remote_parser.add_argument('--user', type=str, required=True,
                             help='Username for SSH connection')
    remote_parser.add_argument('--password', type=str, default=None,
                             help='Password for SSH connection (optional if using key authentication)')
    remote_parser.add_argument('--key', type=str, default=None,
                             help='Path to SSH private key file (optional)')
    remote_parser.add_argument('--port', type=int, default=22,
                             help='SSH port (default: 22)')
    remote_parser.add_argument('--repo', type=str, required=True,
                             help='URL of the Git repository to clone and run')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Diagnose issues')
    diagnose_parser.add_argument('--host', type=str, default=None,
                               help='Hostname or IP address to diagnose')
    diagnose_parser.add_argument('--port', type=int, default=None,
                               help='Port to diagnose')
    diagnose_parser.add_argument('--repo', type=str, default=None,
                               help='Repository URL to diagnose')
    
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Create orchestrator
    orchestrator = Orchestrator()
    
    if args.command == 'run':
        # Run locally
        logger.info("Running locally")
        
        # Process the project
        success, process = orchestrator.process_project(args.repo, args.target, args.port)
        
        if success and process:
            logger.info("Project started successfully")
            
            try:
                # Keep the script running until the user terminates it
                while True:
                    time.sleep(1)
                    
                    # Check if the process is still running
                    if process.poll() is not None:
                        logger.error(f"Process terminated. Exit code: {process.returncode}")
                        break
                    
            except KeyboardInterrupt:
                logger.info("Stopping project...")
                if process.poll() is None:
                    process.terminate()
        else:
            logger.error("Failed to run project")
            return 1
    
    elif args.command == 'remote':
        # Run on remote host
        logger.info(f"Running on remote host: {args.host}")
        
        # Connect to the remote host
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
    
    elif args.command == 'diagnose':
        # Diagnose issues
        logger.info("Running diagnostics")
        
        if args.host:
            # Diagnose network issues
            if args.port:
                # Diagnose specific port
                results = orchestrator.diagnostics.diagnose_port_issue(args.host, args.port)
            else:
                # Diagnose host connectivity
                results = orchestrator.diagnostics.diagnose_network_issue(args.host)
            
            # Print results
            logger.info("Diagnostics results:")
            for key, value in results.items():
                if key != "suggestions":
                    logger.info(f"  {key}: {value}")
            
            if results.get("suggestions"):
                logger.info("Suggestions:")
                for suggestion in results["suggestions"]:
                    logger.info(f"  - {suggestion}")
        
        elif args.repo:
            # Diagnose Git repository issues
            logger.info(f"Diagnosing repository: {args.repo}")
            
            # Try to clone the repository
            success, path = orchestrator.clone_repository(args.repo)
            
            if success:
                logger.info(f"Repository cloned successfully to {path}")
            else:
                logger.error("Failed to clone repository")
        
        else:
            logger.error("No diagnostics target specified")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
