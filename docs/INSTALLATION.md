# Installation Guide 🔧

Comprehensive installation instructions for all supported platforms and environments.

## Table of Contents

1. [Quick Install](#quick-install)
2. [System Requirements](#system-requirements)
3. [Platform-Specific Installation](#platform-specific-installation)
4. [Development Environment Setup](#development-environment-setup)
5. [Docker Installation](#docker-installation)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

## Quick Install

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper

# Create environment and install
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Verify installation
gundert-scraper --version
```

### Using pip

```bash
# Clone repository
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Verify installation
gundert-scraper --version
```

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.10 or higher |
| **Memory** | 2GB RAM minimum, 4GB recommended |
| **Storage** | 1GB free space for installation + output |
| **Network** | Internet connection for portal access |
| **Browser** | Chrome/Chromium for Selenium (auto-installed) |

### Operating System Support

| OS | Support Level | Notes |
|----|---------------|-------|
| **Linux** | ✅ Full Support | Ubuntu 20.04+, CentOS 8+, Debian 11+ |
| **macOS** | ✅ Full Support | macOS 11+ (Big Sur and later) |
| **Windows** | ✅ Full Support | Windows 10+ (64-bit) |
| **WSL** | ✅ Full Support | WSL2 recommended |

### Python Version Compatibility

```bash
# Check your Python version
python --version

# Supported versions
Python 3.10.x ✅
Python 3.11.x ✅  
Python 3.12.x ✅
Python 3.13.x ✅ (experimental)
```

## Platform-Specific Installation

### Linux (Ubuntu/Debian)

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Install Chrome for Selenium
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone and install project
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv venv .venv
source .venv/bin/activate
uv sync

# Verify installation
gundert-scraper --version
```

### Linux (CentOS/RHEL/Fedora)

```bash
# Update system packages
sudo dnf update -y  # or 'sudo yum update -y' for older versions

# Install Python and development tools
sudo dnf install -y python3.10 python3-pip git

# Install Chrome
sudo dnf install -y wget
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Continue with standard installation
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv venv .venv
source .venv/bin/activate
uv sync
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python@3.10 git

# Install Chrome
brew install --cask google-chrome

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # or ~/.bash_profile

# Clone and install project
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv venv .venv
source .venv/bin/activate
uv sync

# Verify installation
gundert-scraper --version
```

### Windows

#### Using PowerShell (Recommended)

```powershell
# Install Python from Microsoft Store or python.org
# Ensure Python 3.10+ is in PATH

# Install Git for Windows
# Download from: https://git-scm.com/download/win

# Install Chrome
# Download from: https://www.google.com/chrome/

# Install uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Clone and install project
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv venv .venv
.venv\Scripts\activate
uv sync

# Verify installation
gundert-scraper --version
```

#### Using WSL2 (Alternative)

```bash
# Enable WSL2 in Windows Features
# Install Ubuntu from Microsoft Store

# In WSL2 terminal, follow Ubuntu instructions above
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Install Chrome in WSL2
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Continue with standard Linux installation
```

## Development Environment Setup

### For Contributors

```bash
# Clone repository with development dependencies
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper

# Create development environment
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
uv sync --dev

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install

# Run tests to verify setup
uv run pytest

# Check code quality
uv run black --check src/ tests/
uv run flake8 src/ tests/
uv run mypy src/

# Generate coverage report
uv run pytest --cov=src --cov-report=html
```

### IDE Setup

#### Visual Studio Code

1. **Install VS Code**: Download from [code.visualstudio.com](https://code.visualstudio.com/)

2. **Install Python Extension**: Search for "Python" in Extensions

3. **Configure Workspace**:
   ```json
   // .vscode/settings.json
   {
       "python.defaultInterpreterPath": ".venv/bin/python",
       "python.formatting.provider": "black",
       "python.linting.enabled": true,
       "python.linting.flake8Enabled": true,
       "python.testing.pytestEnabled": true,
       "python.testing.pytestArgs": ["tests"],
       "editor.formatOnSave": true
   }
   ```

4. **Recommended Extensions**:
   - Python (ms-python.python)
   - Black Formatter (ms-python.black-formatter)
   - Pylance (ms-python.vscode-pylance)
   - GitLens (eamodio.gitlens)

#### PyCharm

1. **Install PyCharm**: Download Community or Professional edition

2. **Configure Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Add → Existing Environment → `.venv/bin/python`

3. **Configure Tools**:
   - Enable Black formatter in File → Settings → Tools → External Tools
   - Set up pytest as default test runner
   - Configure flake8 for linting

#### Vim/Neovim

```vim
" Example .vimrc configuration for Python development
" Install vim-plug or your preferred plugin manager

Plug 'davidhalter/jedi-vim'        " Python autocompletion
Plug 'psf/black', { 'branch': 'stable' }  " Black formatter
Plug 'dense-analysis/ale'          " Linting
Plug 'vim-test/vim-test'          " Test runner

" Black formatter configuration
autocmd BufWritePre *.py execute ':Black'

" ALE linter configuration
let g:ale_linters = {'python': ['flake8', 'mypy']}
let g:ale_python_flake8_executable = '.venv/bin/flake8'
let g:ale_python_mypy_executable = '.venv/bin/mypy'
```

## Docker Installation

### Using Pre-built Image (When Available)

```bash
# Pull the image
docker pull beniza/gundert-portal-scraper:latest

# Run with volume mount for output
docker run -it --rm \
  -v "$(pwd)/output:/app/output" \
  beniza/gundert-portal-scraper:latest \
  gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper

# Build Docker image
docker build -t gundert-portal-scraper .

# Run container
docker run -it --rm \
  -v "$(pwd)/output:/app/output" \
  gundert-portal-scraper \
  gundert-scraper --help
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  gundert-scraper:
    build: .
    volumes:
      - ./output:/app/output
      - ./temp:/app/temp
    environment:
      - GUNDERT_OUTPUT_DIR=/app/output
      - GUNDERT_TEMP_DIR=/app/temp
    command: gundert-scraper --help
```

```bash
# Run with Docker Compose
docker-compose up gundert-scraper
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Create virtual environment and install dependencies
RUN uv venv .venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync

# Create output directories
RUN mkdir -p /app/output /app/temp

# Set environment variables
ENV GUNDERT_OUTPUT_DIR=/app/output
ENV GUNDERT_TEMP_DIR=/app/temp
ENV PYTHONPATH=/app/src

# Default command
CMD ["gundert-scraper", "--help"]
```

## Verification

### Basic Functionality Test

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Test CLI availability
gundert-scraper --version
gundert-scraper --help

# Test info command
gundert-scraper info

# Test connection (without extraction)
gundert-scraper validate https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1

# Test small extraction
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --pages 1-2 \
  --format usfm \
  --output test_output.usfm
```

### Python API Test

```python
"""Test basic API functionality."""

from gundert_portal_scraper import BookIdentifier, GundertPortalConnector

# Test URL parsing
try:
    book = BookIdentifier("https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1")
    print(f"✓ Book ID parsed: {book.book_id}")
except Exception as e:
    print(f"✗ URL parsing failed: {e}")

# Test connection
try:
    with GundertPortalConnector(book, use_selenium=False) as connector:
        accessible = connector.validate_book_access()
        print(f"✓ Book accessible: {accessible}")
except Exception as e:
    print(f"✗ Connection test failed: {e}")

print("Basic verification complete!")
```

### Full Integration Test

```bash
# Run the complete test suite
uv run pytest tests/ -v

# Run integration tests specifically
uv run pytest tests/integration/ -v --tb=short

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

## Troubleshooting

### Common Issues

#### 1. Python Version Mismatch

**Error**: `Python 3.9 is not supported`

**Solution**:
```bash
# Check Python version
python --version

# Install correct Python version (Ubuntu)
sudo apt install python3.10 python3.10-venv

# Update alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

#### 2. Chrome/ChromeDriver Issues

**Error**: `selenium.common.exceptions.WebDriverException: Message: 'chromedriver' executable needs to be in PATH`

**Solution**:
```bash
# Chrome not installed - install Chrome first
# On Ubuntu:
sudo apt install google-chrome-stable

# On macOS:
brew install --cask google-chrome

# Verify Chrome installation
google-chrome --version

# ChromeDriver is managed automatically by webdriver-manager
# If issues persist, try manual update:
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
```

#### 3. Memory Issues

**Error**: `MemoryError` or browser crashes

**Solution**:
```bash
# Increase available memory or run in headless mode
gundert-scraper extract URL --headless --batch-size 2

# Or reduce batch size in Python API
scraper.scrape_full_book(batch_size=2)
```

#### 4. Network/Firewall Issues

**Error**: `ConnectionError: Failed to establish connection`

**Solution**:
```bash
# Test direct connection
curl -I https://opendigi.ub.uni-tuebingen.de/

# Check proxy settings if behind corporate firewall
export http_proxy=http://proxy.company.com:8080
export https_proxy=$http_proxy

# Or configure in Python
gundert-scraper extract URL --proxy http://proxy.company.com:8080
```

#### 5. Permission Issues

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Fix file permissions
chmod -R 755 gundert-portal-scraper/
chmod +x .venv/bin/*

# Or run with proper user permissions (avoid sudo with pip)
python -m pip install --user -e .
```

#### 6. Import Errors

**Error**: `ModuleNotFoundError: No module named 'gundert_portal_scraper'`

**Solution**:
```bash
# Install in development mode
pip install -e .

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify installation
python -c "import gundert_portal_scraper; print('Import successful')"
```

### Platform-Specific Issues

#### Linux Issues

```bash
# Missing system libraries
sudo apt install -y python3-dev libxml2-dev libxslt1-dev

# SELinux issues (CentOS/RHEL)
sudo setsebool -P httpd_can_network_connect 1

# Firewall blocking Chrome
sudo ufw allow out 80,443
```

#### macOS Issues

```bash
# Xcode command line tools
xcode-select --install

# Permission issues with Chrome
sudo spctl --master-disable  # Temporarily disable Gatekeeper if needed

# Path issues
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows Issues

```powershell
# Windows Defender blocking Chrome automation
# Add exclusion for Chrome and project directory

# Path issues
$env:PATH += ";C:\Program Files\Google\Chrome\Application"

# PowerShell execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Environment variable
export GUNDERT_LOG_LEVEL=DEBUG

# Command line
gundert-scraper extract URL --debug --verbose

# Python API
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Advanced Configuration

### Environment Variables

Create a `.env` file for persistent configuration:

```bash
# .env file
GUNDERT_PORTAL_TIMEOUT=60
GUNDERT_PORTAL_RETRY_ATTEMPTS=3
GUNDERT_PORTAL_USE_SELENIUM=true

SELENIUM_HEADLESS=true
SELENIUM_WINDOW_SIZE=1920,1080
SELENIUM_IMPLICIT_WAIT=10

GUNDERT_OUTPUT_DIR=/path/to/output
GUNDERT_TEMP_DIR=/tmp/gundert_scraper
GUNDERT_LOG_LEVEL=INFO
GUNDERT_LOG_FILE=/path/to/logfile.log

# Proxy settings (if needed)
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
```

### Performance Tuning

```bash
# For high-performance extraction
export GUNDERT_BATCH_SIZE=10
export GUNDERT_PARALLEL_DOWNLOADS=4
export SELENIUM_PAGE_LOAD_TIMEOUT=30

# For low-memory environments
export GUNDERT_BATCH_SIZE=2
export SELENIUM_MEMORY_LIMIT=512m
export GUNDERT_CACHE_SIZE=100
```

### Custom Chrome Options

```python
from gundert_portal_scraper import GundertPortalConnector
from selenium.webdriver.chrome.options import Options

# Custom Chrome configuration
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')

# Use with connector
with GundertPortalConnector(book, chrome_options=chrome_options) as connector:
    # ... operations
```

### System Service Setup

Create a systemd service for automated processing:

```ini
# /etc/systemd/system/gundert-scraper.service
[Unit]
Description=Gundert Portal Scraper Service
After=network.target

[Service]
Type=simple
User=scraper
WorkingDirectory=/opt/gundert-portal-scraper
Environment=PATH=/opt/gundert-portal-scraper/.venv/bin
ExecStart=/opt/gundert-portal-scraper/.venv/bin/gundert-scraper batch --config /etc/gundert-scraper/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl enable gundert-scraper
sudo systemctl start gundert-scraper

# Check status
sudo systemctl status gundert-scraper
```

---

**Next Steps**: 
- See [USER_GUIDE.md](USER_GUIDE.md) for usage instructions
- Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for development setup
- Visit [API_REFERENCE.md](API_REFERENCE.md) for programmatic usage