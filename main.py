import sys
import os
from dotenv import load_dotenv
from database import DatabaseManager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Point Python to compiled C++ engine inside the build directory
sys.path.append(os.path.join(os.path.dirname(__file__), "build"))
import handcricket_ai # type: ignore

# Intialize FastAPI server
app = FastAPI(title="Pitch.io", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load from .env file
load_dotenv()

# Grab password securely
db_pass = os.getenv("DB_PASSWORD")

# Initialize database
db = DatabaseManager(db_pass)

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
    
    # Check if match is already over
    pre_check = db.check_match_status(request.match_id) 
    if pre_check.get('status') == "COMPLETED":
        return {
            "status": "error",
            "message": "Match has already been completed."
        }

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

    # Check achievement [LIVE]
    new_achievements = []

    # Calculate runs scored so far
    total_match_runs = match_state.get("player_runs", 0)
    total_match_wickets = match_state.get("player_wickets", 0)

    # Get lifetime runs  and calculate true live career runs
    profile = db.get_player_profile(request.player_name)
    baseline_career_runs = profile.get("lifetime_runs", 0)
    baseline_career_wickets = profile.get("lifetime_wickets", 0)
    live_career_runs = baseline_career_runs + total_match_runs
    live_career_wickets = baseline_career_wickets + total_match_wickets

    if profile.get("total_matches", 0) == 0:
        if db.unlock_achievement(request.player_name, "Welcome to the Pitch!"):
            new_achievements.append("Welcome to the Pitch!")

    if request.difficulty == 1:
        if db.unlock_achievement(request.player_name, "The Tarnished."):
            new_achievements.append("The Tarnished.")
    elif request.difficulty == 2:
        if db.unlock_achievement(request.player_name, "The Chosen."):
            new_achievements.append("The Chosen.")
    else:
        if db.unlock_achievement(request.player_name, "The Clairvoyant."):
            new_achievements.append("The Clairvoyant.")

    if request.difficulty in [2, 3]:
        # Runs Achievements
        if live_career_runs >= 1:
            if db.unlock_achievement(request.player_name, "First Shot"):
                new_achievements.append("First Shot")
        if live_career_runs >= 10:
            if db.unlock_achievement(request.player_name, "Determined"):
                new_achievements.append("Determined")
        if live_career_runs >= 30:
            if db.unlock_achievement(request.player_name, "Crazed Batter"):
                new_achievements.append("Crazed Batter")
        if live_career_runs >= 50:
            if db.unlock_achievement(request.player_name, "Half-Century Maker"):
                new_achievements.append("Half-Century Maker")
        if live_career_runs >= 100:
            if db.unlock_achievement(request.player_name, "Century Maker"):
                new_achievements.append("Century Maker")
        if live_career_runs >= 200:
            if db.unlock_achievement(request.player_name, "The Destroyer"):
                new_achievements.append("The Destroyer")
        if live_career_runs >= 500:
            if db.unlock_achievement(request.player_name, "The Undefeated One"):
                new_achievements.append("The Undefeated One")
        if live_career_runs >= 1000:
            if db.unlock_achievement(request.player_name, "The God of War"):
                new_achievements.append("The God of War")
        # Wickets Achievements
        if live_career_wickets >=1:
            if db.unlock_achievement(request.player_name, "First Blood"):
                new_achievements.append("First Blood")
        if live_career_wickets >= 10:
            if db.unlock_achievement(request.player_name, "Wicket Taker"):
                new_achievements.append("Wicket Taker")
        if live_career_wickets >= 30:
            if db.unlock_achievement(request.player_name, "The Speedster"):
                new_achievements.append("The Speedster")
        if live_career_wickets >= 50:
            if db.unlock_achievement(request.player_name, "The Magician"):
                new_achievements.append("The Magician")
        if live_career_wickets >= 100:
            if db.unlock_achievement(request.player_name, "Bowling Maestro"):
                new_achievements.append("Bowling Maestro")
        if live_career_wickets >= 200:
            if db.unlock_achievement(request.player_name, "Merciless"):
                new_achievements.append("Merciless")
        if live_career_wickets >= 500:
            if db.unlock_achievement(request.player_name, "The Relentless"):
                new_achievements.append("The Relentless")
        if live_career_wickets >= 1000:
            if db.unlock_achievement(request.player_name, "The God of Death"):
                new_achievements.append("The God of Death")
        # Hybrid Achievements
        if live_career_runs >= 50 and live_career_wickets >= 50:
            if db.unlock_achievement(request.player_name, "All-Rounder"):
                new_achievements.append("All-Rounder")
        if live_career_runs >= 100 and live_career_wickets >= 100:
            if db.unlock_achievement(request.player_name, "Captain Fantastic"):
                new_achievements.append("Captain Fantastic")
        if live_career_runs >= 200 and live_career_wickets >= 200:
            if db.unlock_achievement(request.player_name, "Legend"):
                new_achievements.append("Legend")
        if live_career_runs >= 500 and live_career_wickets >= 500:
            if db.unlock_achievement(request.player_name, "The Immortal"):
                new_achievements.append("The Immortal")
        if live_career_runs >= 1000 and live_career_wickets >= 1000:
            if db.unlock_achievement(request.player_name, "The All Seeing."):
                new_achievements.append("The All Seeing.")

    # Return result to frontend
    if match_state["status"] == "COMPLETED":
        result = match_state["result"]
        #Save final stats to DB player profile
        db.update_career_stats(
            player_name = request.player_name,
            match_runs = match_state['player_runs'],
            match_wickets = match_state['player_wickets'],
            result = result
        )

        # POST MATCH ACHIEVEMENTS
        profile = db.get_player_profile(request.player_name)
        live_wins = profile.get("total_wins", 0)
        live_loss = profile.get("total_losses", 0)

        if result == "WIN":
            if live_wins >= 1:
                if db.unlock_achievement(request.player_name, "First Victory"):
                    new_achievements.append("First Victory")
            if live_wins >= 10:
                if db.unlock_achievement(request.player_name, "Champion"):
                    new_achievements.append("Champion")
            if live_wins >= 50:
                if db.unlock_achievement(request.player_name, "Pitch Dominator"):
                    new_achievements.append("Pitch Dominator")
        if result == "LOSS":
            if live_loss >= 1:
                if db.unlock_achievement(request.player_name, "First Loss"):
                    new_achievements.append("First Loss")
            if live_loss >= 10:
                if db.unlock_achievement(request.player_name, "A Failure."):
                    new_achievements.append("A Failure.")
            if live_loss >= 50:
                if db.unlock_achievement(request.player_name, "The Disgrace."):
                    new_achievements.append("The Disgrace.")
        if result == "DRAW":
            if db.unlock_achievement(request.player_name, "A Rare Sight."):
                new_achievements.append("A Rare Sight.")

        return {
            "status": "COMPLETED",
            "player_move": request.player_move,
            "ai_move": ai_move,
            "is_wicket": is_wicket,
            "message": f"MATCH OVER! Final Score: {match_state['player_runs']}/{match_state['ai_wickets']} AI: {match_state['ai_runs']} / {match_state['player_wickets']}",
            "final_score": match_state,
            "unlocked_achievements": new_achievements
        }
    return {
        "status": "success",
        "player_move": request.player_move,
        "ai_move": ai_move,
        "is_wicket": is_wicket,
        "runs_scored": runs_scored,
        "message": "WICKET!" if is_wicket else f"{runs_scored} runs scored.",
        "current_score": match_state,
        "unlocked_achievements": new_achievements
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

@app.get("/leaderboard")
def leaderboard():
    top_players = db.get_leaderboard()

    if not top_players:
        raise HTTPException(status_code=500, detail="Could not fetch leaderboard")
    
    return {
        "status": "success",
        "total_players": len(top_players),
        "leaderboard": top_players
    }

@app.get("/about")
def about():
    return {
        "gamename": "Pitch.io",
        "creator": "Prattik K",
        "version": "1.0"
    }