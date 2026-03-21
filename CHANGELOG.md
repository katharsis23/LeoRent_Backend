# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-03-21 by *katharsis23*

### Added
- **Authentication Endpoints**: Implemented `/users/signup/v1` and `/users/login/v1` endpoints without Firebase integration
  - Password hashing using `bcrypt`
  - Duplicate field validation (email, username, phone)
  - Proper error handling with appropriate HTTP status codes
  
- **Testing Infrastructure**:
  - Added `pytest-asyncio` dependency for async test support
  - Created `tests/conftest.py` with `client` fixture for FastAPI TestClient
  - Configured `pyproject.toml` with pytest-asyncio settings
  - Added authentication tests in `tests/test_auth.py`

- **Database Layer**:
  - Created `database_connector.py` to replace the old `database.py` module
  - Consolidated database setup (BASE, engine, AsyncSessionLocal, get_db)
  - Added user repository functions in `database/user.py`
    - `create_user()` with bcrypt password hashing
    - `login_user()` with password verification
    - `find_user_by_id()` for user lookup

### Changed
- **Import Structure**: Fixed import paths across the codebase
  - Changed `from leorent_backend...` to `from src.leorent_backend...` for consistency
  - Updated `PYTHONPATH` in Dockerfile from `/app/src` to `/app`
  
- **Router Responses**: Updated user router to return consistent field names
  - Changed `name` to `username` in JSON responses
  - Fixed parameter passing to use keyword arguments (`db=..., user=...`)

- **Docker Configuration**:
  - Updated `PYTHONPATH` environment variable for proper imports in container
  - Removed old `database.py` and `database/__init__.py` to prevent conflicts

### Fixed
- **Circular Imports**: Resolved circular dependency between `models.py` and `database/__init__.py`
- **Password Storage**: Fixed bcrypt hash storage - now properly decodes bytes to string before storing in database
- **Login Validation**: Fixed login to properly check bcrypt result (was not checking password validity)
- **Database Field Names**: Aligned model field names with schema fields (`phone_number` in model vs `phone` in schema)

### Removed
- **Firebase Integration**: Temporarily removed Firebase authentication (will be re-added in future)
- **Old Database Module**: Removed `src/leorent_backend/database.py` and `src/leorent_backend/database/__init__.py`
- **Legacy Files**: Cleaned up old database package structure

### Technical Details
- **Password Hashing**: Uses `bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')`
- **Session Management**: Tests use `AsyncSessionLocal` with context managers for proper resource cleanup
- **Dependency Injection**: Uses FastAPI's `Depends(get_db)` pattern with `app.dependency_overrides` for testing
