# Datadog Downloader

A professional grade Datadog data downloader that helps you fetch metrics from your Datadog account.

## Prerequisites

- [pyenv](https://github.com/pyenv/pyenv#installation)
- [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv#installation)
- [Poetry](https://python-poetry.org/docs/#installation) package manager
- VSCode (optional)

## Installation

1. Set up Python environment:
```bash
# Install Python 3.9
pyenv install 3.9.18

# Create virtualenv
pyenv virtualenv 3.9.18 datadog-downloader

# Activate virtualenv
pyenv local datadog-downloader

# Verify Python version
python --version  # Should show Python 3.9.18
```

2. Clone the repository:
```bash
git clone <repository-url>
cd datadog-downloader
```

3. Install dependencies using Poetry:
```bash
poetry install
```

## VSCode Setup

1. Install the Python extension for VSCode
2. Open the command palette (Cmd/Ctrl + Shift + P)
3. Search for "Python: Select Interpreter"
4. Choose the interpreter at `.venv/bin/python`

The included `.vscode/settings.json` will:
- Set up the correct Python interpreter
- Enable format on save with black
- Enable automatic import sorting with isort

## Configuration

Create a `.env` file in the root directory with your Datadog credentials:

```env
DATADOG_API_KEY=your_api_key_here
DATADOG_APP_KEY=your_app_key_here
DATADOG_SITE=datadoghq.com  # Optional, defaults to datadoghq.com
```

To get your API and application keys:
1. Log into your Datadog account
2. Navigate to Organization Settings > API Keys
3. Create a new API key or use an existing one
4. Navigate to Team > Application Keys to create or use an existing application key

## Usage

1. Activate the Poetry virtual environment:
```bash
poetry shell
```

2. Run the application:
```bash
# Command line usage instructions will be added as features are implemented
```

## Development

This project uses several development tools:

- `black` for code formatting
- `isort` for import sorting
- `flake8` for code linting
- `mypy` for type checking
- `pytest` for testing

To run the development tools:

```bash
# Format code
poetry run black .
poetry run isort .

# Run linting
poetry run flake8 .

# Run type checking
poetry run mypy .

# Run tests
poetry run pytest
```
