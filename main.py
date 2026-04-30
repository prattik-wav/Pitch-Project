from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
from database import DatabaseManager

# Point Python to compiled C++ engine inside the build directory
sys.path.append(os.path.join(os.path.dirname(__file__), "build"))
import handcricket_ai # type: ignore

# Intialize FastAPI server
app = FastAPI(title="Pitch.io", version="1.0")

db = DatabaseManager("pratzelsql")

class LoginRequest(BaseModel):
    player_name: str

class RegisterRequest(BaseModel):
    player_name: str
    password: str

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

@app.post("/check_player")
def check_player(request: LoginRequest):
    exists = db.player_exists(request.player_name)
    return {"player_name": request.player_name, "exists": exists}

@app.post("/register")
def register(request: RegisterRequest):
    success = db.register_player(request.player_name, request.password)
    
    if success:
        return {
            "status": "success", 
            "player_name": request.player_name
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail="Registration failed. Player might already exist."
        )
    
@app.get("/about")
def about():
    return {
        "gamename": "Pitch.io",
        "creator": "Prattik K",
        "version": "1.0"
    }