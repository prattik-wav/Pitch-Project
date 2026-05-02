import mysql.connector
from mysql.connector import Error

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
                        player_balls_bowled = player_balls_bowled + 1 
                    WHERE id = %s
                """
                cursor.execute(sql, (runs_scored, match_id))

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
            
            # Check the Wicket limit (currently: 1)
            if match["wickets"] >= 1 and match["status"] == "IN_PROGRESS":
                # The innings is over; Update the status
                cursor.execute("UPDATE match_data SET status = 'COMPLETED' WHERE ID = %s", (match_id, ))
                conn.commit()
                return {"status": "COMPLETED", "final_runs": match["runs"], "final_wickets": match["wickets"]}
            return {"status": "IN_PROGRESS", "current_runs": match["runs"], "current_wickets": match["wickets"]}
        except Error as e:
            print(f"[ERROR] Could not check match status: {e}")
            return {"status": "error"}
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