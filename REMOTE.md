
python remote.py --host 192.168.188.154 --user pi --password pi --repo https://github.com/UnitApi/mcp.git


# Remote Installation Script Documentation

## Overview

`remote.py` is a Python script that simplifies the process of setting up a Raspberry Pi environment remotely via SSH. The script connects to a Raspberry Pi, updates the system, installs dependencies, clones a Git repository, creates a Python virtual environment, and installs required Python packages.

## Requirements

- Python 3.6+
- paramiko>=2.7.0 (SSH library for Python)
- A Raspberry Pi with SSH enabled
- Network connectivity to the Raspberry Pi

## Installation

1. Ensure you have Python 3.6 or higher installed
2. Install required dependencies:
   ```bash
   pip install paramiko
   ```

## Usage

Run the script with the following command:

```bash
python remote.py --host <RASPBERRY_PI_IP> --user <SSH_USERNAME> [--password <SSH_PASSWORD>] [--key <SSH_KEY_PATH>] [--port <SSH_PORT>] --repo <GIT_REPOSITORY_URL>
```

### Parameters

- `--host`: IP address or hostname of the Raspberry Pi (required)
- `--user`: SSH username (required)
- `--password`: SSH password (optional if using key authentication)
- `--key`: Path to the SSH private key file (optional)
- `--port`: SSH port (default: 22)
- `--repo`: URL of the Git repository to install (required)

### Example

```bash
python remote.py --host 192.168.1.100 --user pi --password raspberry --repo https://github.com/username/myproject.git
```

## What the Script Does

1. Connects to the Raspberry Pi using the provided SSH credentials
2. Updates the Raspberry Pi system using `apt-get update` and `apt-get upgrade`
3. Installs system dependencies: git, python3, python3-pip, python3-venv
4. Clones the specified Git repository
5. Creates a Python virtual environment in the cloned repository
6. Installs Python requirements from the repository's requirements.txt file

## Logging

The script logs all operations to both the console and a file named `rpi_installer.log`. This allows tracking of the installation process and troubleshooting if issues occur.

## Error Handling

The script includes comprehensive error handling to catch and report issues during:
- SSH connection
- System updates
- Repository cloning
- Virtual environment creation
- Package installation

