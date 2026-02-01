# CSDS393_StudySync: Study Group & Academic Productivity Platform

## Tech Stack Setup
To run this project locally, ensure you have the following installed:

### 1. Backend (Python + FastAPI)
* **Install Python 3.x**
* **FastAPI & Uvicorn**: `pip install fastapi uvicorn`
* **Testing**: `pip install pytest`

### 2. Frontend (React + TypeScript)
* **Install Node.js** (LTS version)
* **Initialize**: `npx create-react-app study-sync --template typescript`
* **Axios**: `npm install axios`
* **Charts**: `npm install recharts`

### 3. Database (PostgreSQL)
* **Install PostgreSQL**
* **Primary Database**: `study_sync_db`
* **Key Tables**: `users`, `study_groups`, `resources`

### 4. External Services
* **Google Calendar API**: Setup required for later phases.
* **Authentication**: JWT (JSON Web Tokens) will be used for session management.
