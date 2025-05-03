"""
Example of running a Python web application using the orchestrator.
"""

import sys
import logging
from unitmcp.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run a Python web application."""
    # Create orchestrator
    orchestrator = Orchestrator()
    
    # Repository URL (Flask example app)
    repo_url = "https://github.com/pallets/flask-tutorial.git"
    
    # Process the project
    logger.info(f"Processing project from {repo_url}")
    success, process = orchestrator.process_project(repo_url, port=5000)
    
    if success and process:
        logger.info("Project started successfully")
        
        try:
            # Keep the script running until the user terminates it
            logger.info("Press Ctrl+C to stop the application")
            process.wait()
        except KeyboardInterrupt:
            logger.info("Stopping application...")
            if process.poll() is None:
                process.terminate()
    else:
        logger.error("Failed to process project")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
