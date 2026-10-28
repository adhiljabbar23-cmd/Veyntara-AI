# Veyntara AI

Veyntara AI is a Python-based business validation assistant designed to help users evaluate business ideas, examine assumptions, plan experiments, and review evidence before making business decisions.

## Features

- Business profile creation and management
- Business assumption tracking
- Experiment planning and result recording
- Financial calculations, including break-even analysis
- Evidence-based decision support
- Statistical and economic threshold evaluation
- Local database storage using SQLite
- AI-assisted analysis and web research

## Requirements

- Python 3.10 or later
- Git
- A configured AI API endpoint and API key
- Docker, if running the local SearXNG search service

## Installation

Clone the repository and enter the project folder:

```powershell
git clone https://github.com/adhiljabbar23-cmd/Veyntara-AI.git
cd Veyntara-AI
```

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configuration

Create a local `.env` file using `.env.example` as a template. Set your API key:

```text
FREELLMAPI_API_KEY=your_actual_api_key
```

Replace the placeholder with your own key. Never commit `.env` or publish API credentials.

### AI API service

Veyntara AI expects an OpenAI-compatible API service at `http://localhost:3001/v1`, using the model name `auto`. Start and configure that service separately before running the application. The service provider and its startup instructions must be configured for your environment.

### SearXNG web search

Docker is required for the local SearXNG search service. From the project directory, start it with:

```powershell
docker compose -f .\searxng\docker-compose.yml up -d
```

The Compose configuration maps SearXNG to `http://localhost:8081`. Keep `searxng/settings.yml` alongside the Compose file and review its configuration before deployment.

## Run the application

From the project directory:

```powershell
python main.py
```

The application presents an interactive menu for creating a business, continuing an existing business, or exiting.

## Run tests

Run the unit and validation tests:

```powershell
python -m unittest -v test_unit test_decision test_input_validation test_model_validation
```

Database integration tests are maintained separately under `_safe_test` during development. They use an isolated test database and should be run from their designated test directory.

## Data and security

- SQLite database files are local application data and should not be committed.
- API keys belong in `.env`, not source code or documentation.
- Keep database backups private and secure.
- Use synthetic data when running development and integration tests.

## Project status

Veyntara AI is under active development. Test results cover specific components and workflows; they do not guarantee that every feature is production-ready.

## License

No license has been specified yet. Add a license before distributing the project if you intend to grant others permission to use, modify, or redistribute it.
