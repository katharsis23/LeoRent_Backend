# LeoRent Backend

A modern FastAPI-based backend for the LeoRent real estate platform that ensures safe and transparent rental processes for both landlords and tenants.

## Features

- **FastAPI Framework** - Modern, fast web framework for building APIs
- **PostgreSQL Database** - Robust relational database with async support
- **Docker Support** - Containerized deployment for easy setup
- **Poetry Dependency Management** - Modern Python dependency management
- **Automated Testing** - pytest-based testing framework
- **Code Quality** - Flake8 linting and pre-commit hooks
- **Interactive API Documentation** - Auto-generated Swagger UI and ReDoc

## Prerequisites

### For Local Development:
- **Python 3.14+**
- **PostgreSQL 16+** (if not using Docker)
- **Poetry** (Python dependency manager)
- **Git**

### For Docker Deployment:
- **Docker** and **Docker Compose**
- **Git**

## Installation

### Option 1: Docker (Recommended for All Platforms)

The Docker approach works seamlessly on **Windows, macOS, and Linux**.

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd LeoRent_Backend
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Database: localhost:5430

5. **Stop the application**
   ```bash
   docker-compose down
   ```

### Option 2: Local Development

#### Windows Setup

1. **Install Python 3.14+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Install PostgreSQL**
   - Download from [postgresql.org](https://www.postgresql.org/download/windows/)
   - Remember your password during installation

3. **Install Poetry**
   ```powershell
   # Open PowerShell as Administrator
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python3 -
   ```
   - Restart your terminal after installation

4. **Clone and setup**
   ```powershell
   git clone <repository_url>
   cd LeoRent_Backend\LeoRent_backend
   ```

5. **Configure Poetry**
   ```powershell
   poetry config virtualenvs.in-project true
   poetry install
   ```

6. **Setup environment**
   ```powershell
   # Copy and edit the environment file
   copy ..\.env.example ..\.env
   ```

7. **Create database**
   ```sql
   -- Run in PostgreSQL
   CREATE USER leouser WITH PASSWORD 'leopass';
   CREATE DATABASE leodb OWNER leouser;
   GRANT ALL PRIVILEGES ON DATABASE leodb TO leouser;
   ```

8. **Run the application**
   ```powershell
   poetry run inv dev
   ```

#### macOS/Linux Setup

1. **Install Python 3.14+**
   ```bash
   # macOS with Homebrew
   brew install python@3.14
   
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.14 python3.14-venv
   ```

2. **Install PostgreSQL**
   ```bash
   # macOS with Homebrew
   brew install postgresql@16
   brew services start postgresql@16
   
   # Ubuntu/Debian
   sudo apt install postgresql-16
   sudo systemctl start postgresql
   ```

3. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

4. **Clone and setup**
   ```bash
   git clone <repository_url>
   cd LeoRent_Backend/LeoRent_backend
   
   poetry config virtualenvs.in-project true
   poetry install
   ```

5. **Setup environment**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your database credentials
   ```

6. **Create database**
   ```bash
   sudo -u postgres createuser leouser
   sudo -u postgres createdb leodb -O leouser
   sudo -u postgres psql -c "ALTER USER leouser PASSWORD 'leopass';"
   ```

7. **Run the application**
   ```bash
   poetry run inv dev
   ```

## Quick Start Commands

### Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build -d
```

### Local Development Commands (using Invoke)

```bash
# Start development server
poetry run inv dev

# Run tests
poetry run inv test

# Run tests with coverage
poetry run inv test --cov

# Check code quality
poetry run inv lint

# Run all checks (lint + test)
poetry run inv check

# Clean temporary files
poetry run inv clean

# List all available commands
poetry run inv --list
```

## Project Structure

```
LeoRent_Backend/
├── LeoRent_backend/           # Main application directory
│   ├── src/
│   │   └── leorent_backend/
│   │       ├── main.py        # FastAPI application entry point
│   │       ├── config/        # Configuration files
│   │       ├── database/      # Database models and migrations
│   │       └── routers/       # API route handlers
│   ├── tests/                 # Test files
│   ├── poetry.lock            # Locked dependencies
│   ├── pyproject.toml         # Project configuration
│   └── tasks.py               # Invoke task definitions
├── docker-compose.yaml        # Docker Compose configuration
├── Dockerfile                 # Docker image configuration
├── .env.example              # Environment variables template
└── scripts/                  # Utility scripts
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Database configuration
POSTGRES_USER=leouser
POSTGRES_PASSWORD=leopass
POSTGRES_DB=leodb
DATABASE_URL=postgresql+asyncpg://leouser:leopass@postgres:5432/leodb

# App configuration
MODE=debug
SECRET_KEY=your_super_secret_key_for_university_project
DEBUG=True
```

### Database Setup

The application automatically creates database tables on startup. Make sure your PostgreSQL server is running and accessible.

## Testing

```bash
# Run all tests
poetry run inv test

# Run tests with coverage report
poetry run inv test --cov

# Run only failed tests
poetry run inv test --lastfailed
```

## API Documentation

Once the application is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/healthcheck

## Development Workflow

1. **Setup pre-commit hooks** (recommended for contributors)
   ```bash
   cp scripts/pre-commit.bash .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```

2. **Make changes** to your code

3. **Run checks** before committing
   ```bash
   poetry run inv check
   ```

4. **Commit** your changes

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Kill process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

**Poetry not found**
```bash
# Restart your terminal or add poetry to PATH
# Windows: Restart PowerShell
# macOS/Linux: source ~/.bashrc or ~/.zshrc
```

**Database connection failed**
- Check PostgreSQL is running
- Verify credentials in `.env` file
- Ensure database exists

**Docker issues**
```bash
# Clean up Docker
docker system prune -a
docker-compose down -v
docker-compose up --build
```

### Getting Help

- Check the logs: `docker-compose logs -f` or application console output
- Verify all prerequisites are installed
- Ensure environment variables are correctly set

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `poetry run inv check`
5. Submit a pull request

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Support

For support and questions, please open an issue in the repository or contact the development team.
