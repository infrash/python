# Orchestrator Documentation

The Orchestrator is a powerful component of the UnitMCP system that helps you manage, deploy, and run applications from git repositories across different platforms and environments.

## Features

- Clone git repositories
- Detect project types automatically (Python, Node.js, PHP, Ruby, Rust, static HTML)
- Install dependencies
- Configure environment variables
- Run applications with appropriate commands
- Diagnose and fix common issues
- Deploy to remote machines via SSH

## Installation

The Orchestrator is part of the UnitMCP package. You can install it by:

```bash
# Clone the repository
git clone https://github.com/infrash/python.git
cd infrash

# Install the package
pip install -e .
```

## Usage

### Running a Project Locally

To run a project from a git repository:

```bash
python -m unitmcp run --repo https://github.com/username/project.git
```

This will:
1. Clone the repository
2. Detect the project type
3. Install dependencies
4. Set up environment variables
5. Run the application

#### Example: Running a Python Flask Application

```bash
python -m unitmcp run --repo https://github.com/pallets/flask-tutorial.git --port 8080
```

#### Example: Running a Node.js Application

```bash
python -m unitmcp run --repo https://github.com/expressjs/express-starter.git --port 3000
```

#### Example: Running a Static HTML Website

```bash
python -m unitmcp run --repo https://github.com/username/static-website.git --port 8000
```

### Deploying to a Remote Machine

To deploy and run a project on a remote machine:

```bash
python -m unitmcp remote --host 192.168.188.154 --user pi --password raspberry --repo https://github.com/username/project.git
```

This will:
1. Connect to the remote machine via SSH
2. Update the system
3. Install required dependencies
4. Clone the repository
5. Set up the environment
6. Install project dependencies
7. Run the application

#### Example: Deploying to a Raspberry Pi

```bash
python -m unitmcp remote --host 192.168.188.154 --user pi --password raspberry --repo https://github.com/UnitApi/mcp.git
```

#### Example: Using SSH Key Authentication

```bash
python -m unitmcp remote --host 192.168.188.154 --user pi --key ~/.ssh/id_rsa --repo https://github.com/UnitApi/mcp.git
```

### Diagnosing Issues

The Orchestrator includes a powerful diagnostics engine to help troubleshoot common issues:

```bash
python -m unitmcp diagnose --host 192.168.188.154 --port 22
```

This will analyze connectivity issues and provide intelligent suggestions.

#### Example: Diagnosing Network Connectivity

```bash
python -m unitmcp diagnose --host 192.168.1.154
```

Output:
```
2025-05-03 22:30:15 - __main__ - INFO - Running diagnostics
2025-05-03 22:30:15 - __main__ - INFO - Diagnostics results:
2025-05-03 22:30:15 - __main__ - INFO -   host: 192.168.1.154
2025-05-03 22:30:15 - __main__ - INFO -   reachable: False
2025-05-03 22:30:15 - __main__ - INFO -   dns_resolution: True
2025-05-03 22:30:15 - __main__ - INFO -   ip: 192.168.1.154
2025-05-03 22:30:15 - __main__ - INFO - Suggestions:
2025-05-03 22:30:15 - __main__ - INFO -   - Host is not responding to ping. Check if it's online and reachable.
2025-05-03 22:30:15 - __main__ - INFO -   - Try IP addresses in the 192.168.188.0/24 network range.
```

#### Example: Diagnosing Git Repository Issues

```bash
python -m unitmcp diagnose --repo https://github.com/nonexistent/repo.git
```

## Advanced Usage

### Custom Port

You can specify a custom port for the application:

```bash
python -m unitmcp run --repo https://github.com/username/project.git --port 5000
```

### Custom Target Directory

You can specify a custom directory to clone the repository into:

```bash
python -m unitmcp run --repo https://github.com/username/project.git --target ~/projects/myapp
```

### Environment Variables

The Orchestrator will automatically detect `.env.example` files and prompt you to configure them. You can also manually set environment variables before running the application.

## Supported Project Types

The Orchestrator can automatically detect and run the following project types:

### Python

- Flask applications
- Django applications
- FastAPI applications
- General Python scripts

Detection: Looks for `requirements.txt`, `setup.py`, or `pyproject.toml`

### Node.js

- Express applications
- React applications
- General Node.js applications

Detection: Looks for `package.json`

### PHP

- Laravel applications
- General PHP applications

Detection: Looks for `composer.json` or `.php` files

### Ruby

- Ruby on Rails applications
- Sinatra applications

Detection: Looks for `Gemfile`

### Rust

- Cargo-based Rust applications

Detection: Looks for `Cargo.toml`

### Static HTML

- Static websites

Detection: Looks for `.html` or `.htm` files

## Troubleshooting

### Common Issues

#### Connection Refused

If you see "Connection refused" when connecting to a remote host, check that:
- The host is online
- SSH service is running
- The port is correct and not blocked by a firewall

#### Repository Already Exists

If you see "destination path already exists", the Orchestrator will automatically try to use a different directory name.

#### Missing Dependencies

The Orchestrator will attempt to install missing dependencies automatically. If it fails, you may need to install them manually.

## Examples

### Example 1: Deploying a Python Web Application to Raspberry Pi

```bash
python -m unitmcp remote --host 192.168.188.154 --user pi --password raspberry --repo https://github.com/UnitApi/web-app.git
```

This will deploy the web application to the Raspberry Pi and run it.

### Example 2: Running a Node.js API Server Locally

```bash
python -m unitmcp run --repo https://github.com/UnitApi/api-server.git --port 3000
```

This will run the API server locally on port 3000.

### Example 3: Deploying a Static Website to Raspberry Pi

```bash
python -m unitmcp remote --host 192.168.188.154 --user pi --password raspberry --repo https://github.com/UnitApi/static-site.git
```

This will deploy the static website to the Raspberry Pi and serve it using a simple HTTP server.

### Example 4: Running a PHP Laravel Application Locally

```bash
python -m unitmcp run --repo https://github.com/laravel/laravel.git --port 8000
```

This will run the Laravel application locally on port 8000.

### Example 5: Diagnosing and Fixing Network Issues

```bash
python -m unitmcp diagnose --host 192.168.1.154 --port 22
```

This will diagnose connectivity issues with the host and suggest fixes, such as checking the correct network range.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
