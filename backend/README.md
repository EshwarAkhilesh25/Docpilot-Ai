# DocMind Backend

AI-powered Document & Multimedia Q&A Platform Backend

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (Async)
- Alembic
- Pydantic v2
- PostgreSQL
- Redis
- uv package manager

## Project Structure

```
backend/
├── app/
│   ├── api/          # API endpoints and routing
│   ├── core/         # Configuration, logging, exceptions, security
│   ├── db/           # Database session and base models
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic layer
│   ├── repositories/ # Data access layer
│   ├── dependencies/ # Dependency injection
│   ├── middleware/   # Custom middleware
│   ├── utils/        # Utility functions
│   ├── workers/      # Background task workers
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── alembic/          # Database migrations
├── .env.example      # Environment variables template
├── pyproject.toml    # Dependencies and configuration
└── Dockerfile        # Container configuration
```

## Local Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- uv package manager

### Installation

1. Install uv:
```bash
pip install uv
```

2. Install dependencies:
```bash
uv pip install -e .
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Configure environment variables in `.env`:
```env
APP_NAME=DocMind API
APP_VERSION=0.1.0
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docmind

JWT_SECRET=change-this-secret-in-development
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080

GROQ_API_KEY=
HUGGINGFACE_API_KEY=
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
SUPABASE_URL=
SUPABASE_KEY=

REDIS_URL=redis://localhost:6379/0

LOG_LEVEL=INFO
LOG_FORMAT=json
```

5. Start PostgreSQL and Redis (using Docker):
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=docmind postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

### Running the Application

Development mode with hot reload:
```bash
uvicorn app.main:app --reload
```

Production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

### Code Quality

Run linting:
```bash
ruff check .
```

Format code:
```bash
ruff format .
black .
```

Type checking:
```bash
mypy app/
```

Install pre-commit hooks:
```bash
pre-commit install
```

## Docker

### Build Image

```bash
docker build -t docmind-backend .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/docmind \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  docmind-backend
```

### Docker Compose

Use the root `docker-compose.yml` to run all services:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| APP_NAME | Application name | DocMind API |
| APP_VERSION | Application version | 0.1.0 |
| APP_ENV | Environment (development/staging/production) | development |
| DEBUG | Debug mode | true |
| DATABASE_URL | PostgreSQL connection string | postgresql+asyncpg://... |
| JWT_SECRET | JWT secret key | change-this-secret-in-production |
| JWT_ALGORITHM | JWT algorithm | HS256 |
| JWT_EXPIRATION_MINUTES | JWT expiration time | 10080 |
| GROQ_API_KEY | Groq AI API key | |
| SUPABASE_URL | Supabase project URL | |
| SUPABASE_KEY | Supabase API key | |
| REDIS_URL | Redis connection string | redis://localhost:6379/0 |
| LOG_LEVEL | Logging level | INFO |
| LOG_FORMAT | Log format (json/text) | json |

## Architecture

This project follows Clean Architecture principles with clear separation of concerns:

- **API Layer**: FastAPI routers and endpoints
- **Service Layer**: Business logic
- **Repository Layer**: Data access
- **Models**: Database entities
- **Schemas**: Request/response validation
- **Core**: Configuration, security, constants, logging
