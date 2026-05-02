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

class StartMatchRequest(BaseModel):
    player_name: str

class PlayTurnRequest(BaseModel):
    match_id: int
    player_name: str
    player_move: int
    ai_is_batting: bool
    difficulty: int

# Health check Endpoint
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running", "c++ engine": "Connected"}

@app.post("/play_turn")
def play_turn(request: PlayTurnRequest):
    # Ensure the move is valid (0-10)
    if request.player_move < 0 or request.player_move > 10:
        raise HTTPException(status_code = 400, detail = "Invalid move. Must be between 0 and 10")
    
    # Grab the last 5 plays from MySQL
    recent_plays = db.get_recent_plays(request.match_id, limit=5)

    # Feed the history to C++ Engine
    ai_move = handcricket_ai.get_ai_prediction(
        recent_plays,
        request.ai_is_batting,
        request.difficulty
    )

    # Check for a wicket
    is_wicket = (request.player_move == ai_move)

    # Calculate runs for this specific ball
    runs_scored = 0
    if not is_wicket:
        runs_scored = ai_move if request.ai_is_batting else request.player_move

    # Permanently record this delivery in the database
    success = db.record_delivery(
        match_id = request.match_id,
        player_name = request.player_name,
        player_move = request.player_move,
        ai_move = ai_move,
        is_wicket = is_wicket
    )

    # update the live scoreboard
    db.update_match_score(
        match_id = request.match_id,
        runs_scored = runs_scored,
        is_wicket = is_wicket,
        ai_is_batting = request.ai_is_batting
    )

    if not success:
        raise HTTPException(status_code=500, detail="Database error: Could not record delivery")
    
    # Check if match is over
    match_state = db.check_match_status(request.match_id)
    
    # Return result to frontend
    if match_state["status"] == "COMPLETED":
        return {
            "status": "COMPLETED",
            "player_move": request.player_move,
            "ai_move": ai_move,
            "is_wicket": is_wicket,
            "message": f"MATCH OVER! Final Score: {match_state['final_runs']}/{match_state['final_wickets']}",
            "final_score": match_state
        }
    return {
        "status": "success",
        "player_move": request.player_move,
        "ai_move": ai_move,
        "is_wicket": is_wicket,
        "runs_scored": runs_scored,
        "message": "WICKET!" if is_wicket else f"{runs_scored} runs scored.",
        "current_score": match_state
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
    
@app.post("/start_match")
def start_match(request: StartMatchRequest):
    match_id = db.create_match(request.player_name)

    if match_id == -1:
        raise HTTPException(
            status_code = 500,
            detail = "Failed to initialize match in the database"
        )
    
    return {
        "status": "success",
        "message": "Match started successfully",
        "match_id": match_id,
        "player_name": request.player_name
    }

@app.get("/about")
def about():
    return {
        "gamename": "Pitch.io",
        "creator": "Prattik K",
        "version": "1.0"
    }