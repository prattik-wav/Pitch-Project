from fastapi import FastAPI, HTTPException
import sys
import os
from database import get_db_connection

# Point Python to compiled C++ engine inside the build directory
sys.path.append(os.path.join(os.path.dirname(__file__), "build"))
import handcricket_ai

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

# Database Endpoint to fetch player profile
@app.get("/player/{player_name}")
def get_player_profile(player_name: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        # Querying the exact table structure from Python file.
        query = """
                SELECT name, lifetime_runs, lifetime_wickets, total_matches, total_wins
                FROM player_profile
                WHERE name = %s
            """
        cursor.execute(query, (player_name,))
        player = cursor.fetchone()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
        
        return {"status": "success", "data": player}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()