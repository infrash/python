"""
Project type detection module.
"""

import os
from typing import List

class ProjectDetector:
    """
    Class for detecting project types based on file patterns.
    """
    
    def detect_project_type(self, project_path: str) -> List[str]:
        """
        Detect project type based on directory contents.
        
        Args:
            project_path: Path to the project
            
        Returns:
            List of detected project types
        """
        project_types = []
        
        # Check Python
        if os.path.exists(os.path.join(project_path, "requirements.txt")) or \
           os.path.exists(os.path.join(project_path, "setup.py")) or \
           os.path.exists(os.path.join(project_path, "pyproject.toml")):
            project_types.append("python")
        
        # Check Node.js
        if os.path.exists(os.path.join(project_path, "package.json")):
            project_types.append("node")
        
        # Check PHP
        if os.path.exists(os.path.join(project_path, "composer.json")):
            project_types.append("php")
        elif any(f.endswith(".php") for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            project_types.append("php")
        
        # Check Ruby
        if os.path.exists(os.path.join(project_path, "Gemfile")):
            project_types.append("ruby")
        
        # Check Rust
        if os.path.exists(os.path.join(project_path, "Cargo.toml")):
            project_types.append("rust")
        
        # Check static HTML
        if any(f.endswith((".html", ".htm")) for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))):
            project_types.append("static")
        
        return project_types or ["unknown"]
