import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import  user_router
from .routers.restaurants import router as restaurant_router
from .routers.reservation_router import router as reservation_router
from .routers.auth_router import router as auth_router
from .routers.chat_router import router as chat_router
from populate_restaurants import main

main()  # Populate the database with initial restaurant data

# Configure logging for the entire application
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for development
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for this file
logger = logging.getLogger(__name__)
logger.info("Starting FoodieSpot API server")

app = FastAPI(
    title="FoodieSpot Reservation API",
    description="API for restaurant reservations with OTP authentication and agentic chat",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ashish-shroti-agentic-reservation-system-962843070701.europe-west1.run.app", "http://localhost:8501"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(restaurant_router)
app.include_router(reservation_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(chat_router)  # Add the new chat router

@app.get("/")
def read_root():
    return {"message": "Welcome to FoodieSpot Reservation API"}

# Add this if you're using the standard pattern of running the app with uvicorn directly from this file
if __name__ == "__main__":
    logger.info("Application startup")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
