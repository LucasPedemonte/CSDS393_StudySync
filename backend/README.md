## README.md

This is the FastAPI backend for the StudySync project. It handles user authentication and serves as the bridge between the React frontend and the PostgreSQL database.

## Technical Stack

* **Framework:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Validation:** Pydantic
* **Security:** python-dotenv (Environment Variables)

## Local Development Setup

### 1. Environment Configuration

Create a file named `.env` in the `backend/` directory. This file is ignored by Git to protect local credentials. Add the following line, replacing the placeholders with your pgAdmin credentials:

`DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/studysync_db`

### 2. Installation and Execution

1. **Activate Virtual Environment:**
* Windows: `.\venv\Scripts\activate`
* Mac/Linux: `source venv/bin/activate`


2. **Install Requirements:**
* `pip install -r requirements.txt`

3. **Start Server:**
* `uvicorn main:app --reload`

The API documentation will be available at `http://127.0.0.1:8000/docs`.

## API Documentation

### POST /login

Authenticates a user against the database.

**Request Body:**

```json
{
  "email": "test@case.edu",
  "password": "password123"
}

```

**Success Response (200 OK):**

```json
{
  "status": "success",
  "user": "Test Student",
  "role": "student"
}

```

## Team Notes

* **Frontend:** The backend must be running for Axios requests to succeed. Use `http://127.0.0.1:8000/login` for the authentication flow.
* **Database:** New tables should be defined in `models.py`. SQLAlchemy will handle the table creation on server restart.
* **General:** Do not commit your `.env` file to the repository.