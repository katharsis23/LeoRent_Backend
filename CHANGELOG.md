# Changelog

All notable changes to this project will be documented in this file.

## [UnReleased] - 2026-03-27 by *nazar* & *katharsis23*

### Fixed
- **Configuration Loading**: Fixed cascade validation errors on startup
  - Moved Redis configuration to separate module to prevent unrelated JWT/SMTP/S3 validation failures
  - BaseHTTPMiddleware now properly returns JSONResponse instead of raising HTTPException for rate limit responses
  - Logging middleware now captures all HTTP requests/responses with timing information

### Changed
- **Dependency Management**: Updated `poetry.lock` to include new redis dependencies
- **Error Handling**: Rate limiter now fails gracefully with in-memory fallback instead of returning 500 errors

### Technical Details
- **Rate Limiting Logic**:
  - Redis key format: `rate_limit:{client_ip}`
  - TTL per window: 60 seconds
  - In-memory dict tracks: `{key: (request_count, window_start_time)}`
  - Window reset: when current_time >= (start_time + window_duration)

- **Middleware Stack Order** (innermost to outermost):
  1. LoggingMiddleware - captures all requests/responses
  2. ErrorHandlingMiddleware - centralized error handling
  3. RateLimitMiddleware - enforces rate limits
  4. CORSMiddleware - handles CORS headers

## [UnReleased] - 2026-03-23 by *katharsis23*

### Added
- **Firebase Authentication**: Complete Firebase integration with ID token verification
  - `/users/firebase-auth/v1` endpoint for JSON body authentication
  - `/firebase/signup` endpoint for Bearer token authentication  
  - `/firebase/me` endpoint for user profile retrieval
  - Firebase Admin SDK integration with service account configuration
  - Automatic user creation from Firebase tokens
  - Support for Email/Password and Google OAuth providers

- **Database Schema**: Extended Users model for Firebase support
  - Added `firebase_uid` field (unique, nullable)
  - Added `first_name` field (optional, nullable)
  - Added `last_name` field (optional, nullable)
  - Made `username` and `phone_number` nullable for Firebase users
  - Added `firebase_email_verified` boolean field

- **Firebase Configuration**:
  - `FirebaseSettings` class with environment variable support
  - Service account credentials handling
  - Firebase app initialization with error handling
  - Updated `.env.example` with Firebase configuration template

- **Testing Infrastructure**:
  - Created `tests/test_firebase_auth.py` with comprehensive Firebase tests
  - Mock Firebase app and token verification for isolated testing
  - Test coverage for success, failure, and service unavailable scenarios
  - Created `firebase_test.html` frontend for manual testing

- **Frontend Testing Tool**:
  - Email/Password and Google OAuth login forms
  - Manual token input for debugging
  - Token display and copy functionality
  - API endpoint testing with detailed logging

### Changed
- **Database Migration**: Updated Users table schema for Firebase compatibility
  - Added Firebase-specific fields for token-based authentication
  - Backward compatibility with existing local authentication

- **User Creation Logic**: Enhanced Firebase user handling
  - __Username generation from email (`` → ``).__ 
  - __Automatic phone number generation for Firebase users (`+0000000000`).__
  - __Username uniqueness validation with random suffix for duplicates__
  - First/last name extraction from Firebase tokens

- **Authentication Flow**: Dual authentication support
  - Local bcrypt authentication (existing `/users/signup/v1`, `/users/login/v1`)
  - Firebase token-based authentication (new `/firebase/*` endpoints)
  - Unified user model supporting both authentication methods

### Fixed
- **Firebase Token Handling**: Fixed token extraction and validation
  - Proper Firebase app initialization checking
  - Token verification with revocation checking
  - User creation fallback when Firebase user doesn't exist in local DB

- **Database Constraints**: Resolved NOT NULL constraint violations
  - Fixed username generation for Firebase users
  - Added phone number placeholder for missing phone data
  - Proper handling of optional fields in Firebase authentication

### Technical Details
- **Firebase Integration**: Uses Firebase Admin SDK with service account authentication
  - Token verification: `auth.verify_id_token(token, check_revoked=True)`
  - User creation: `create_user_from_firebase(decoded_token, first_name, last_name, db)`
  - Configuration via environment variables with `FIREBASE_*` prefixes

- **Authentication Methods**:
  - **Local**: bcrypt password hashing and verification
  - **Firebase**: ID token verification with automatic user sync
  - **Hybrid**: Single user table supporting both authentication types

- **Testing Strategy**:
  - Mock-based testing for Firebase services
  - Database transaction rollback for test isolation
  - Comprehensive error scenario coverage

> **NEEDS FIX OR REFACTOR**
> - *create_user_from_firebase* function needs refactoring to handle edge cases better. Delete redundant logic to username
>   simulation or phone simulation.
> - *migration* - Migration to create Username nullable and NOT UNIQUE. 
> - *tests* - Tests need to be rewritten to clear the database after testing
> - *documentation* - Documentation needs to be updated to reflect the new authentication methods
> - *v1_endpoints* - V1 endpoints need to be updated to reflect the new authentication methods.


## [Released] - 2026-03-21 by *katharsis23*

### Added
- **Authentication Endpoints**: Implemented `/users/signup/v1` and `/users/login/v1` endpoints without Firebase integration
  - Password hashing using `bcrypt`
  - Duplicate field validation (email, username, phone)
  - Proper error handling with appropriate HTTP status codes

- **Backblaze Photo Storage**:
  - Added Backblaze B2 S3 configuration via environment variables
  - Added `BackblazeService` for working with photo uploads, downloads, and deletion
  - Added photo upload endpoint from external URL: `/photos/upload-from-url`
  - Added photo upload endpoint from local file: `/photos/upload-from-file`
  - Added photo download endpoint: `/photos/download/{file_key}`
  - Added photo delete endpoint: `/photos/delete/{file_key}`
  - Added photo response schemas for upload and delete operations
  
- **Testing Infrastructure**:
  - Added `pytest-asyncio` dependency for async test support
  - Created `tests/conftest.py` with `client` fixture for FastAPI TestClient
  - Configured `pyproject.toml` with pytest-asyncio settings
  - Added authentication tests in `tests/test_auth.py`
  - Added photo API and service tests in `tests/test_photos.py`

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

- **Photo Handling**:
  - Moved Backblaze operations to async-compatible service calls using `asyncio.to_thread()` for boto3 requests
  - Added multipart file upload support for local image uploads
  - Added structured JSON responses for photo deletion
  
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
- **Photo Endpoint Coverage**: Added test coverage for upload, download, delete, nested paths, and filenames with spaces

### Removed
- **Firebase Integration**: Temporarily removed Firebase authentication (will be re-added in future)
- **Old Database Module**: Removed `src/leorent_backend/database.py` and `src/leorent_backend/database/__init__.py`
- **Legacy Files**: Cleaned up old database package structure

### Technical Details
- **Password Hashing**: Uses `bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')`
- **Session Management**: Tests use `AsyncSessionLocal` with context managers for proper resource cleanup
- **Dependency Injection**: Uses FastAPI's `Depends(get_db)` pattern with `app.dependency_overrides` for testing
