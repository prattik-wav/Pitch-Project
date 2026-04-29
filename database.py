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
        except Error as e:
            print(f"[ERROR] Could not setup database: {e}")
        
    def init_tables(self):
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()

        ddl_profile = """
                CREATE TABLE IF NOT EXISTS player_profile ( 
                    id INT AUTO_INCREMENT PRIMARY KEY, 
                    name VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL, 
                    lifetime_runs INT DEFAULT 0, 
                    lifetime_wickets INT DEFAULT 0, 
                    total_matches INT DEFAULT 0, 
                    total_wins INT DEFAULT 0, 
                    total_losses INT DEFAULT 0
                )
            """
        
        try:
            cursor.execute(ddl_profile)
            conn.commit()
        except Error as e:
            print(f"[ERROR] Failed to create tables: {e}")
        finally:
            cursor.close()
            con.close()

    def player_exists(self, player_name: str) -> bool:
        conn = self.get_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM player_profile WHERE name = %s", (player_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return Result is not None