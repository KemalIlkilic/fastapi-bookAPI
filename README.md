# FastAPI CRUD and Auth Project

This is the source code for the personal fastapi project. The project focuses on FastAPI development concepts that go beyond the basic CRUD operations.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Running the Application](#running-the-application)
5. [Running Tests](#running-tests)
6. [Project Screenshots](#screenshots)

## Getting Started
Follow the instructions below to set up and run your FastAPI project.

### Prerequisites
Ensure you have the following installed:

- Python >= 3.10
- PostgreSQL
- Redis

### Project Setup
1. Clone the project repository:
    ```bash
    
    git clone https://github.com/KemalIlkilic/fastapi-bookAPI.git
    ```
   
2. Navigate to the project directory:
    ```bash
    cd fastapi-bookAPI/
    ```

3. Create and activate a virtual environment:
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

4. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

5. Run database migrations to initialize the database schema:
    ```bash
    alembic upgrade head
    ```

6. Open a new terminal and ensure your virtual environment is active. Start the Celery worker (Linux/Unix shell):
    ```bash
    sh runworker.sh
    ```

## Running the Application
Start the application:

```bash
fastapi dev src/
``` 

## Running Tests
Run the tests using this command
```bash
pytest
```

### Screenshots
![API Screenshot](images/api-1.png)
![API Screenshot](images/api-2.png)
![Bearer Screenshot](images/auth.png)
![Schemas Screenshot](images/schemas.png)