# DocMind AI

AI-powered Document & Multimedia Q&A Platform

## Overview

DocMind AI is a production-grade platform for asking questions about documents and multimedia content using AI. The project follows Clean Architecture principles with a modern tech stack.

## Tech Stack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (Async)
- PostgreSQL
- Redis
- Alembic
- Pydantic v2

### Frontend
- React 18
- Vite
- TypeScript
- Tailwind CSS
- React Query (@tanstack/react-query)

## Project Structure

```
DocMind AI/
├── backend/          # FastAPI backend
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   └── Dockerfile
├── frontend/         # Vite + React frontend
│   ├── src/
│   ├── components/
│   ├── lib/
│   └── Dockerfile
├── docker-compose.yml # Docker Compose configuration
└── .github/          # GitHub Actions CI/CD
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker (optional, for containerized setup)

## Quick Start with Docker

The easiest way to run the entire stack is using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- Backend API on port 8000
- Frontend on port 3000

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

## Local Development Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install uv package manager:
```bash
pip install uv
```

3. Install dependencies:
```bash
uv pip install -e .
```

4. Create and configure environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docmind
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-this-secret-in-development
```

5. Start PostgreSQL and Redis (if not using Docker):
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=docmind postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

6. Run database migrations:
```bash
alembic upgrade head
```

7. Start the backend server:
```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

API Documentation: http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env.local
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Environment Variables

### Backend (.env)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET`: Secret key for JWT tokens
- `GROQ_API_KEY`: Groq AI API key
- `HUGGINGFACE_API_KEY`: Hugging Face API Token (for remote embedding inference)
- `EMBEDDING_MODEL`: Embedding model identifier (default: BAAI/bge-small-en-v1.5)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

See `backend/.env.example` for all available options.

### Frontend (.env.local)
- `NEXT_PUBLIC_API_URL`: Backend API URL

See `frontend/.env.example` for all available options.

## Code Quality

### Backend
Run linting and formatting:
```bash
cd backend
ruff check .
ruff format .
black .
mypy app/
```

Install pre-commit hooks:
```bash
pre-commit install
```

### Frontend
Run linting and formatting:
```bash
cd frontend
npm run lint
npm run format
```

## Testing

### Backend
```bash
cd backend
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

## CI/CD

GitHub Actions workflow runs on every push to main/develop branches:
- Install dependencies
- Run linting (Ruff, Black, MyPy for backend; ESLint for frontend)
- Run formatting checks
- Run type checks
- Run tests

See `.github/workflows/ci.yml` for configuration.

## Architecture

### Backend
- **Clean Architecture**: Separation of concerns with API, Service, Repository layers
- **Async-First**: Built with async/await for optimal performance
- **Dependency Injection**: Using FastAPI's dependency system
- **Structured Logging**: JSON-formatted logs for production
- **Database Migrations**: Alembic for version control

### Frontend
- **App Router**: Next.js 15 file-based routing
- **Server Components**: Optimal performance by default
- **TypeScript**: Full type safety
- **React Query**: Efficient data fetching and caching
- **Axios**: Configured HTTP client with interceptors

## Additional Documentation

- [Backend README](backend/README.md) - Detailed backend setup and architecture
- [Frontend README](frontend/README.md) - Detailed frontend setup and architecture

## License

Proprietary - All rights reserved
