import sqlite3
import pandas as pd

class LMSDatabase:
    def __init__(self, db_path='lms_reports.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                week_label TEXT UNIQUE,
                report_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
    
    def save_report(self, week_label, report_df):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO reports (week_label, report_data) VALUES (?, ?)',
                (week_label, report_df.to_json(orient='records'))
            )
    
    def get_report(self, week_label):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT report_data FROM reports WHERE week_label = ?',
                (week_label,)
            )
            result = cursor.fetchone()
            return pd.read_json(result[0], orient='records') if result else None
            
    def get_previous_reports(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT week_label FROM reports ORDER BY created_at DESC'
            )
            return [row[0] for row in cursor.fetchall()]

# Global database instance
db = LMSDatabase()
