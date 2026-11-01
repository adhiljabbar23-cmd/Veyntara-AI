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
- FastAPI-based web application
- User authentication and session management
- Business ownership management
- REST API with automatic Swagger documentation

## Requirements

- Python 3.10 or later
- Git
- A configured OpenAI-compatible AI API endpoint and API key
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

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

For development and automated API testing, install the additional development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

## Configuration

Create a local `.env` file using `.env.example` as a template. Set your API key:

```text
FREELLMAPI_API_KEY=your_actual_api_key
```

Replace the placeholder with your own key. Never commit `.env` or publish API credentials.

### AI API service

Veyntara AI expects an OpenAI-compatible API service at:

```text
http://localhost:3001/v1
```

The model name used by the application is `auto`.

Start and configure that service separately before using AI-powered features. The service provider and its startup instructions must be configured for your environment.

### SearXNG web search

Docker is required for the local SearXNG search service.

From the project directory, start it with:

```powershell
docker compose -f .\searxng\docker-compose.yml up -d
```

The Compose configuration maps SearXNG to:

```text
http://localhost:8081
```

Keep `searxng/settings.yml` alongside the Compose file and review its configuration before deployment.

## Running the application

Veyntara AI supports both a command-line interface and a FastAPI web application.

### 1. Command-line application

From the project directory:

```powershell
python main.py
```

The application presents an interactive menu for creating a business, continuing an existing business, or exiting.

### 2. FastAPI web application

Start the local web server:

```powershell
python -m uvicorn fastapi_app:app --host 127.0.0.1 --port 5500
```

Open the application in your browser:

```text
http://127.0.0.1:5500
```

Useful endpoints:

| Endpoint | Purpose |
|---|---|
| `/` | Web application |
| `/api/health` | API health check |
| `/docs` | Interactive Swagger API documentation |
| `/api/me` | Current authenticated user |
| `/api/businesses` | Authenticated user's businesses |

Stop the server using `Ctrl+C`.

The web application uses the existing project modules and provides authentication, session management, and business ownership checks.

## Database information

The project uses SQLite for local data storage.

- `veyntara.db` is the database used by the command-line application.
- `veyntara_web.db` is used by the FastAPI web application.

These databases are separate. Do not replace, merge, or reset them without first making a backup and understanding the consequences.

Database files and backups should remain private and should not be committed to Git.

## Running tests

Run the existing unit and validation tests:

```powershell
python -m unittest -v test_decision test_input_validation test_model_validation test_unit
```

Run the FastAPI tests separately:

```powershell
python -m unittest -v test_fastapi
```

Or run the complete safe automated test suite:

```powershell
python -m unittest -v test_decision test_input_validation test_model_validation test_unit test_fastapi
```

The FastAPI tests use an isolated temporary database and do not intentionally modify the application's real database.

### Testing precautions

- Do not run `test.py` against your real database without reviewing its database operations first.
- `test_llm.py` calls an external AI API and may consume API resources.
- Use isolated test databases for integration testing.
- Back up important databases before performing manual experiments.

## Security

- API keys belong in `.env`, not source code or frontend JavaScript.
- Passwords are stored using password hashing.
- Authentication sessions use HTTP-only cookies.
- Business ownership is checked by the web API.
- The web server binds to `127.0.0.1` in the documented local setup.
- Keep database files and backups secure.

The current FastAPI configuration is intended for local development. Its session cookies are configured for local HTTP, and additional security work is required before public deployment.

Before production deployment, configure HTTPS and secure cookies, rate limiting, appropriate security headers, trusted hosts, and production-grade server settings. Review authentication, session management, request handling, and API access controls.

Do not expose the development server directly to the public internet.

## Project status

Veyntara AI is under active development. Automated tests cover specific components and API workflows, but passing tests do not guarantee that every feature is production-ready.

## License

No license has been specified yet. Add a license before distributing the project if you intend to grant others permission to use, modify, or redistribute it.