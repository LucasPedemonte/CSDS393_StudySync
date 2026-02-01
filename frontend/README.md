Frontend Integration Guide
Base API URL: http://127.0.0.1:8000

How to connect to the Login API:
Use Axios or the Fetch API to send the user's credentials to the backend.

Endpoint: POST /login

Example Request (using Axios):

JavaScript
import axios from 'axios';

const handleLogin = async (email, password) => {
  try {
    const response = await axios.post('http://127.0.0.1:8000/login', {
      email: email,
      password: password
    });
    
    // On success, you will receive: { "status": "success", "user": "Name", "role": "student" }
    console.log("Welcome:", response.data.user);
    
  } catch (error) {
    console.error("Login failed:", error.response.data.detail);
  }
};

Important Note on CORS:
The backend is currently configured to allow requests from http://localhost:3000 (React's default port). If you run your frontend on a different port, you need to update the allowed origins in backend/main.py.