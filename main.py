from fastapi import FastAPI
import mysql.connector 
from mysql.connector import Error
import sys
import os

# Point Python to compiled C++ engine inside the build directory
sys.path.append(os.path.join(os.path.dirname(__file__), "build"))
import handcricket_ai

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "pratzelsql",
    "database": "handcricket"
}

def get_db_connection():
    """Establishes and returns a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"]
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Intialize FastAPI server
app = FastAPI(title="Pitch.io", version="1.0")

# Health check Endpoint
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running", "c++ engine": "Connected"}

# Prediction Endpoint
@app.get("/predict")
def get_prediction(ai_is_batting: bool, difficulty: int):
    # mock datas for initial test
    # Endpoint to pull live game arrays from MySQL
    mock_memory_cache = [4, 4, 1, 4, 6]

    # Call the C++ engine
    ai_choice = handcricket_ai.get_ai_prediction(mock_memory_cache, ai_is_batting, difficulty)

    return {
        "status": "success",
        "scenario": "AI batting" if ai_is_batting else "AI bowling",
        "difficulty_level": difficulty,
        "player_memory_analyzed": mock_memory_cache,
        "ai_prediction": ai_choice
    }