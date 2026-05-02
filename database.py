import mysql.connector
from mysql.connector import Error, IntegrityError

class DatabaseManager:
    def __init__(self, db_password: str):
        self.config = {
            "host": "localhost",
            "user": "root",
            "password": db_password,
            "database": "pitch_api"
        }
        self.setup_database()

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config, buffered = True)
        except Error as e:
            print(f"[ERROR] Database connection failed: {e}")
            return None
    
    def setup_database(self):
        temp_config = self.config.copy()
        temp_config.pop("database")

        try:
            conn = mysql.connector.connect(**temp_config)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            cursor.close()
            conn.close()

            self.init_tables()
            print("[SYSTEM] Database setup complete")
        except Error as e:
            print(f"[ERROR] Could not setup database: {e}")
        
    def init_tables(self):
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()

        ddl_profile = """
            CREATE TABLE IF NOT EXISTS player_profile ( 
                id               INT AUTO_INCREMENT PRIMARY KEY, 
                name             VARCHAR(100) UNIQUE NOT NULL,
                password         VARCHAR(100) NOT NULL, 
                lifetime_runs    INT  DEFAULT 0, 
                lifetime_wickets INT  DEFAULT 0, 
                total_matches    INT  DEFAULT 0, 
                total_wins       INT  DEFAULT 0, 
                total_losses     INT  DEFAULT 0, 
                total_draws      INT  DEFAULT 0,
                lifetime_balls_faced INT  DEFAULT 0,
                lifetime_balls_bowled INT  DEFAULT 0,
                lifetime_runs_conceded INT  DEFAULT 0,
                centuries        INT  DEFAULT 0,
                half_centuries   INT  DEFAULT 0,
                avg_runs         FLOAT  DEFAULT 0.0
            )
        """
        
        ddl_match_data = """
            CREATE TABLE IF NOT EXISTS match_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(100) NOT NULL,
                runs INT  DEFAULT 0,
                wickets INT  DEFAULT 0,
                ai_wickets INT DEFAULT 0,
                balls_faced INT  DEFAULT 0,
                player_balls_bowled INT  DEFAULT 0,
                player_runs_conceded INT  DEFAULT 0,
                status VARCHAR(20) DEFAULT "IN_PROGRESS",
                result VARCHAR(10),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_player_name (player_name)
            )
        """
        
        ddl_achievements = """
            CREATE TABLE IF NOT EXISTS achievements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(100) NOT NULL,
                achievement VARCHAR(100) NOT NULL,
                achieved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_achievement (player_name, achievement),
                INDEX idx_player_name (player_name)
            )
        """
        
        ddl_deliveries = """
            CREATE TABLE IF NOT EXISTS deliveries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                match_id INT NOT NULL,
                player_name VARCHAR(100) NOT NULL,
                ball_number INT NOT NULL,
                player_move INT NOT NULL,
                ai_move INT NOT NULL,
                is_wicket BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES match_data(id) ON DELETE CASCADE ON UPDATE CASCADE,
                INDEX idx_ai_memory (player_name, match_id)
            )
        """
        
        try:
            cursor.execute(ddl_profile)
            cursor.execute(ddl_match_data)
            cursor.execute(ddl_achievements)
            cursor.execute(ddl_deliveries)
            print("[SYSTEM] All database tables verified/created successfully.")
            conn.commit()
        except Error as e:
            print(f"[ERROR] Failed to create tables: {e}")
        finally:
            cursor.close()
            conn.close()

    def player_exists(self, player_name: str) -> bool:
        conn = self.get_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM player_profile WHERE name = %s", (player_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    
    def register_player(self, player_name: str, password: str) -> bool:
        if self.player_exists(player_name):
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO player_profile (name, password) VALUES (%s, %s)", (player_name, password))
            conn.commit()
            return True
        except Error:
            return False
        finally:
            cursor.close()
            conn.close()

    def create_match(self, player_name: str):
        """Creates a new match record and returns the match_id"""
        conn = self.get_connection()
        if not conn:
            return -1
        
        cursor = conn.cursor()
        try:
            # We try to insert a new row with the player's name to start the match
            sql = "INSERT INTO match_data (player_name, status) VALUES (%s, %s)"
            cursor.execute(sql, (player_name, "IN_PROGRESS"))
            conn.commit()

            # cursor.lastrowid gets the ID of the row we just created
            match_id = cursor.lastrowid
            return match_id
        except Error as e:
            print(f"[ERROR] Could not create match: {e}")
            return -1
        finally:
            cursor.close()
            conn.close()

    def record_delivery(self, match_id: int, player_name: str, player_move: int, ai_move: int, is_wicket: bool) -> bool:
        """Save a single ball to the deliveries table for the ai to learn from later"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            # Figure out what ball number is this for this specific match
            cursor.execute("SELECT COUNT(*) FROM deliveries WHERE match_id = %s", (match_id,))
            ball_number = cursor.fetchone()[0] + 1

            # Insert the exact delivery data 
            sql = """INSERT INTO deliveries
                (match_id, player_name, ball_number, player_move, ai_move, is_wicket)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(sql, (match_id, player_name, ball_number, player_move, ai_move, is_wicket))
            conn.commit()
            return True
        except Error as e:
            print(f"[ERROR] Could not record delivery: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def update_match_score(self, match_id: int, runs_scored: int, is_wicket: bool, ai_is_batting: bool) -> bool:
        """Update the live scoreboard for the active match"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            wicket_val = 1 if is_wicket else 0
            if not ai_is_batting:
                # Player is batting
                sql = """
                    UPDATE match_data
                    SET runs = runs + %s,
                        wickets = wickets + %s,
                        balls_faced = balls_faced + 1
                    WHERE id = %s
                """
                wicket_val = 1 if is_wicket else 0
                cursor.execute(sql, (runs_scored, wicket_val, match_id))
            else:
                # Player is bowling (AI is batting)
                sql = """
                    UPDATE match_data 
                    SET player_runs_conceded = player_runs_conceded + %s,
                        ai_wickets = ai_wickets + %s
                        player_balls_bowled = player_balls_bowled + 1 
                    WHERE id = %s
                """
                cursor.execute(sql, (runs_scored, wicket_val, match_id))

            conn.commit()
            return True
        except Error as e:
            print(f"[ERROR] Could not update scoreboard: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def check_match_status(self, match_id: int) -> dict:
        """Checks if the match has reached its end conditions"""
        conn = self.get_connection()
        if not conn:
            return {"status": "error"}
        
        cursor = conn.cursor()
        try:
            # Get the current score
            cursor.execute("SELECT status, runs, wickets FROM match_data WHERE id = %s", (match_id, ))
            match = cursor.fetchone()

            if not match:
                return {"status": "error"}
            
            p_runs = match["runs"]
            p_wickets = match["wickets"]
            ai_runs = match["player_runs_conceded"]
            ai_wickets = match["ai_wickets"]

            is_completed = False
            result = None

            # Condition 1 : Both teams are out
            if p_wickets >= 1 and ai_wickets >= 1:
                is_completed = True
                if p_runs > ai_runs: result = "WIN"
                elif ai_runs > p_runs: result = "LOSS"
                else: result = "DRAW"
            
            # Condition 2 : Player is chasing and passes the AI
            elif ai_wickets >= 1 and p_runs > ai_runs:
                is_completed = True
                result = "WIN"
            
            # Condition 3 : AI is chasing and passed player
            elif p_wickets >= 1 and ai_runs > p_runs:
                is_completed = True
                result = "LOSS"

            # Execute END Game or Return Live Data
            if is_completed and match["status"] == "IN_PROGRESS":
               sql = ("""
                    UPDATE match_data
                    SET status = 'COMPLETED', result = %s
                    WHERE id = %s
                """)
               cursor.execute(sql, (result, match_id))
               conn.commit()
               return {"status": "COMPLETED",
                       "result": result, 
                       "final_runs": p_runs, 
                       "final_wickets": p_wickets, 
                       "ai_final_runs": ai_runs, 
                       "ai_final_wickets": ai_wickets
                    }
            
            # Check innings if match is still present
            innings = 1 if(p_wickets == 0 and ai_wickets == 0) else 2
            target = None
            if innings == 2:
                target = (p_runs + 1) if p_wickets == 1 else (ai_runs + 1)
            
            return {
                "status": "IN_PROGRESS", 
                "result": result, 
                "target": target,
                "current_runs": p_runs, 
                "current_wickets": p_wickets, 
                "ai_runs": ai_runs, 
                "ai_wickets": ai_wickets
            }
        except Error as e:
            print(f"[ERROR] Could not check match status: {e}")
            return {"status": "error"}
        finally:
            cursor.close()
            conn.close()

    def unlock_achievement(self, player_name: str, achievement: str) -> bool:
        """Attempts to unlock an achievement, Returns True if they don't have it already or returns False if they do"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO achievements (player_name, achievement) VALUES (%s, %s)"
            cursor.execute(sql, (player_name, achievement))
            return True # Successfully unlocked new achievement
        except IntegrityError:
            # Already unlocked Achievement
            return False
        except Error as e:
            print(f"[ERROR] Could not unlock achievement: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_player_profile(self, player_name: str) -> dict:
        """Fetches the player's lifetime stats from the database"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM player_profile WHERE name = %s", (player_name, ))
            return cursor.fetchone() or {}
        except Error as e:
            print(f"[ERROR] Could not fetch profile: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def update_career_stats(self, player_name: str, match_runs: int, match_wickets: int, result: str) -> bool:
        """Permanently adds the match results to the player's lifetime total stats"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            win_val = 1 if result == "WIN" else 0
            loss_val = 1 if result == "LOSS" else 0
            draw_val = 1 if result == "DRAW" else 0

            sql = """
                UPDATE player_profile 
                SET lifetime_runs = lifetime_runs + %s,
                    lifetime_wickets = lifetime_wickets + %s,
                    total_matches = total_matches + 1,
                    total_wins = total_wins + %s,
                    total_losses = total_losses + %s,
                    total_draws = total_draws + %s
                WHERE name = %s
            """
            cursor.execute(sql, (match_runs, match_wickets, win_val, loss_val, draw_val, player_name))
            conn.commit()
            return True
        except Error as e:
            print(f"[ERROR] Could not update career stats: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_recent_plays(self, match_id: int, limit: int = 5) -> list[int]:
        """Fetches the most recent moves made by the player in a specific match"""
        conn = self.get_connection()
        if not conn:
            return []

        cursor = conn.cursor()
        try:
            # we want the most recent deliveries, so we order by ball_number DESC
            # limit restricts how many rows we pullback to save memory
            sql = """
                SELECT player_move
                FROM deliveries
                WHERE match_id = %s
                ORDER BY ball_number DESC
                LIMIT %s
            """

            cursor.execute(sql, (match_id, limit))
            results = cursor.fetchall()

            # The database returns a list of tuples like [(4, 1), (1, ), (6, )]
            # we use a list of comprehension to filter it into a simple list [ 4, 1, 6]
            recent_plays = [row[0] for row in results]

            return recent_plays
        except Error as e:
            print(f"[ERROR] Could not fetch recent plays: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_leaderboard(self) -> list[dict]:
        """Fetches all players, calculates advanced cricket stats, and ranks them by Wins."""
        conn = self.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            # We fetch everyone ordered by who has the most wins
            cursor.fetchone("SELECT * FROM player_profile ORDER BY total_wins DESC, lifetime_runs DESC")
            players = cursor.fetchall()
            
            leaderboard = []
            for p in players:
                # Prevent diversion by zero errors for new players
                balls_faced = max(1, p["lifetime_balls_faced"])
                overs_bowled = max(0.166, p["lifetime_balls_bowled"] / 6) # 1 ball is roughly 0.166 of an over
                matches = max(1, p["total_matches"])
                
                # Calculate Stats
                strike_rate = round((p["lifetime_runs"] / balls_faced) * 100, 2)
                economy_rate = round(p["lifetime_runs_conceded"] / overs_bowled, 2)
                win_rate = round((p["total_wins"] / matches) * 100, 2)

                # Strip out the password and format data for front-end
                safe_profile = {
                    "rank": len(leaderboard) + 1,
                    "name": p["name"],
                    "wins": p["total_wins"],
                    "win_rate": f"{win_rate}%",
                    "runs": p["lifetime_runs"],
                    "wickets": p["lifetime_wickets"],
                    "strike_rate": strike_rate,
                    "economy": economy_rate,
                    "matches_played": p["total_matches"]
                }
                leaderboard.append(safe_profile)
            
            return leaderboard
        except Error as e:
            print(f"[ERROR] Could not fetch leaderboard")
            return []
        finally:
            cursor.close()
            conn.close()