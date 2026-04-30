# Testing Documentation

## Overview
This document describes the test suites for the StudySync project, where tests are located, what they cover, how to run them, and current limitations.

## Test locations

- `backend/tests/` — backend API and database tests for the FastAPI service.
- `frontend/src/` — React component tests for the frontend app.

### Backend test files
- `backend/tests/conftest.py` — pytest fixtures and test database setup.
- `backend/tests/test_authentication.py` — authentication, user sync, and profile management tests.
- `backend/tests/test_messaging_integrity.py` — messaging and inbox behaviors.
- `backend/tests/test_permissions.py` — permission validation for role-based actions.
- `backend/tests/test_resource_library_crud.py` — resource and post creation, listing, and delete rules.

### Frontend test files
- `frontend/src/App.test.js`
- `frontend/src/SchedulePage.test.js`

## What is covered

### Backend coverage
- User synchronization and profile management endpoints.
- User profile retrieval, update, and list endpoints.
- Role-based permissions for students, TAs, and admins.
- Resource post creation, retrieval, and deletion workflows.
- Core messaging and global inbox endpoints.

### Frontend coverage
- Basic rendering and behavior of the React application.
- Specific page/component tests for `App` and `SchedulePage`.

## Dependencies

### Backend
Install Python dependencies from `backend/requirements.txt`.
The backend tests require:
- `pytest`
- `hypothesis`
- `fastapi`
- `SQLAlchemy`
- `psycopg2-binary`
- `uvicorn`
- `python-dotenv`

### Frontend
Install Node dependencies from `frontend/package.json`.
The frontend tests require:
- `react-scripts`
- `@testing-library/react`
- `@testing-library/jest-dom`
- `@testing-library/user-event`

## How to run tests

### Backend test setup and execution
1. Open PowerShell in the repo root.
2. Change directory to the backend folder:
   ```powershell
   cd backend
   ```
3. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
4. Install test dependencies:
   ```powershell
   pip install -r requirements.txt
   pip install pytest hypothesis
   ```
5. Create a dedicated PostgreSQL test database, for example `studysync_test`.
6. Set environment variables before running tests:
   ```powershell
   set DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/studysync_test
   set ALLOW_DB_RESET_FOR_TESTS=1
   ```
7. Run the backend test suite:
   ```powershell
   pytest -q
   ```

#### Notes
- `backend/tests/conftest.py` resets the database schema for each test session.
- The test suite will refuse to run against a non-test database unless `ALLOW_DB_RESET_FOR_TESTS=1` is set.

### Frontend test setup and execution
1. Open PowerShell in the repo root.
2. Change directory to the frontend folder:
   ```powershell
   cd frontend
   ```
3. Install dependencies:
   ```powershell
   npm install
   ```
4. Run React tests:
   ```powershell
   npm test -- --watchAll=false
   ```

## Known limitations
- The backend test suite depends on a PostgreSQL database and an environment variable configuration that is not committed to the repo.
- The current frontend tests are limited to a small number of component-level cases.
- If the backend database URL points to a non-test database, tests will skip or fail unless `ALLOW_DB_RESET_FOR_TESTS=1` is explicitly set.
- The test coverage is focused primarily on backend endpoints; there is no complete frontend end-to-end test suite present.
- The repo does not currently include generated HTML API docs for testing or validation.

## My contributions for testing
- Testing ownership: `anagomez`
- Documented all current backend and frontend test locations.
- Added reproducible setup and run commands for both backend and frontend suites.
- Fixed backend test setup in `backend/tests/conftest.py` so the ORM models are imported before schema creation.
- Verified backend test discovery and execution under a valid database configuration.
- Identified the required environment variables and the test database requirement.
- Documented known limitations for grading transparency.
