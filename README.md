# FoodieSpot Restaurant Reservation System

An intelligent restaurant reservation system powered by AI agents that help users find and book restaurants based on their preferences.

## System Overview

This system consists of two main components:
- **Backend API**: A FastAPI application that manages restaurant data and reservations
- **AI Agent**: An intelligent assistant built with LLMs that helps users find restaurants and make reservations

## Features

- Search for restaurants by cuisine, location, and capacity
- Check restaurant availability for specific dates and party sizes
- Make, manage, and cancel reservations
- AI assistant that understands natural language requests and helps users find the perfect dining spot

## Getting Started

### Prerequisites

- Python 3.8+
- pip or conda for package management

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd agentic_restaurant_reservation_system
```

2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Create .env file with your API keys
OPENROUTER_API_KEY=your-api-key
OPENAI_API_KEY=your-api-key
```

### Running the API

```bash
cd backend
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs to access the API documentation.

### Using the Playground Notebook

The `backend/playground.ipynb` notebook provides an interactive way to test the restaurant reservation agent.

## Deployment

The system can be deployed to Azure. See the playground notebook for deployment instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Docker Setup

This application consists of a FastAPI backend and a Streamlit frontend. Both components are containerized using Docker.

### Prerequisites

- Docker and Docker Compose installed on your system

### Running the Application

1. Clone this repository
2. Navigate to the repository directory
3. Run the following command:

```bash
docker-compose up --build
```

4. Access the frontend at http://localhost:8501
5. The backend API is available at http://localhost:8000

### Environment Variables

The backend uses environment variables for configuration. These can be set in the `.env` file in the backend directory. Important variables include:

- `OPENAI_API_KEY`: Your OpenAI API key for the chat agent
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`: For OTP functionality
- `JWT_SECRET`: Secret key for JWT token generation (set in docker-compose.yml)

### Persistent Data

The application stores data in SQLite databases in the `backend/data` directory, which is mounted as a volume in the Docker container. This ensures that your data persists between container restarts.

Logs are stored in the `backend/logs` directory, also mounted as a volume.

### Stopping the Application

To stop the application, press `Ctrl+C` in the terminal where you ran `docker-compose up`, or run:

```bash
docker-compose down
```

### Rebuilding

If you make changes to the code, you'll need to rebuild the Docker images:

```bash
docker-compose build
```

Or you can combine building and starting:

```bash
docker-compose up --build
```