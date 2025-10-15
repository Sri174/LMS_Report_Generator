import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lms_db.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Use AppData/Local for persistent storage on Windows
if os.name == 'nt':  # Windows
    app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    DATABASE_DIR = os.path.join(app_data, 'LMS_Reports')
else:  # Unix/Linux/Mac
    DATABASE_DIR = os.path.join(os.path.expanduser('~'), '.lms_reports')

# Create directory if it doesn't exist
os.makedirs(DATABASE_DIR, exist_ok=True)

DATABASE_NAME = os.path.join(DATABASE_DIR, 'lms_reports.db')
BACKUP_DIR = os.path.join(DATABASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_db_connection():
    """Create a database connection with proper settings."""
    conn = None
    try:
        conn = sqlite3.connect(
            DATABASE_NAME,
            timeout=30,  # 30 seconds timeout
            isolation_level=None,  # Use autocommit mode
            check_same_thread=False  # Allow multiple threads to access the database
        )
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        # Set busy timeout
        conn.execute('PRAGMA busy_timeout=30000')  # 30 seconds
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        if conn:
            conn.close()
        raise

def backup_database():
    """Create a backup of the database."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f'lms_reports_{timestamp}.db')
        
        # Create a backup using SQLite's backup API
        src = sqlite3.connect(DATABASE_NAME)
        dst = sqlite3.connect(backup_file)
        with dst:
            src.backup(dst)
        
        # Close connections
        src.close()
        dst.close()
        
        logger.info(f"Database backup created: {backup_file}")
        
        # Clean up old backups (keep last 7 days)
        cleanup_old_backups()
        
        return True
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        return False

def cleanup_old_backups(days_to_keep=7):
    """Remove backup files older than specified days."""
    try:
        now = datetime.now()
        cutoff = now - timedelta(days=days_to_keep)
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith('lms_reports_') and filename.endswith('.db'):
                file_path = os.path.join(BACKUP_DIR, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed old backup: {filename}")
                    except Exception as e:
                        logger.error(f"Error removing old backup {filename}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Table for summary reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summary_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL,
                week_label TEXT NOT NULL,
                selected_month TEXT,
                selected_week TEXT,
                selected_grade TEXT,
                min_completion_percentage INTEGER,
                report_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table for detailed student data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detailed_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_report_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                completed_programs INTEGER,
                total_programs INTEGER,
                completion_percentage REAL,
                category TEXT,
                FOREIGN KEY (summary_report_id) REFERENCES summary_reports (id)
            )
        ''')

        # Table for summary report details (the actual pivot table data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summary_report_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_report_id INTEGER,
                student_category TEXT,
                grade_6 INTEGER,
                grade_7 INTEGER,
                grade_8 INTEGER,
                grade_9 INTEGER,
                grade_10 INTEGER,
                grade_11 INTEGER,
                grade_12 INTEGER,
                total INTEGER,
                FOREIGN KEY (summary_report_id) REFERENCES summary_reports (id)
            )
        ''')

        conn.commit()
        logger.info("Database tables initialized successfully")
        
        # Create an initial backup after initialization
        backup_database()
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        if conn:
            conn.close()

def save_report(report_date, week_label, selected_month, selected_week, selected_grade, min_completion_percentage, report_type, summary_df, detailed_df):
    """Saves a generated report (summary and detailed) to the database."""
    conn = None
    summary_report_id = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into summary_reports table
        cursor.execute('''
            INSERT INTO summary_reports (report_date, week_label, selected_month, selected_week, selected_grade, min_completion_percentage, report_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (report_date.strftime('%Y-%m-%d'), week_label, selected_month, selected_week, str(selected_grade), min_completion_percentage, report_type))
        
        summary_report_id = cursor.lastrowid

        # Insert into summary_report_details table
        if not summary_df.empty:
            summary_df_to_save = summary_df.copy()
            
            # Rename columns to match database schema (e.g., 'Grade 6' to 'grade_6')
            new_summary_cols = {}
            for col in summary_df_to_save.columns:
                if col.startswith('Grade '):
                    grade_num = col.split(' ')[1]
                    new_summary_cols[col] = f'grade_{grade_num}'
                elif col == 'Student_Category':
                    new_summary_cols[col] = 'student_category'
                elif col == 'Total':
                    new_summary_cols[col] = 'total'
            summary_df_to_save = summary_df_to_save.rename(columns=new_summary_cols)

            # Ensure all grade columns (grade_6 to grade_12) and total are present, fill with 0 if missing
            expected_grade_cols = [f'grade_{g}' for g in range(6, 13)]
            for col in expected_grade_cols:
                if col not in summary_df_to_save.columns:
                    summary_df_to_save[col] = 0
            
            if 'total' not in summary_df_to_save.columns:
                summary_df_to_save['total'] = 0  # Default to 0 if not present (e.g., single grade report)

            # Add summary_report_id
            summary_df_to_save['summary_report_id'] = summary_report_id
            
            # Select and reorder columns to match the schema
            cols_to_insert = ['summary_report_id', 'student_category'] + expected_grade_cols + ['total']
            summary_df_to_save = summary_df_to_save[cols_to_insert]

            summary_df_to_save.to_sql('summary_report_details', conn, if_exists='append', index=False)

        # Insert into detailed_reports table
        if not detailed_df.empty:
            detailed_df_to_save = detailed_df.copy()
            detailed_df_to_save.columns = [col.replace(' ', '_').lower() for col in detailed_df_to_save.columns]
            detailed_df_to_save['summary_report_id'] = summary_report_id
            
            # Ensure column order matches the database schema
            cols_to_insert = [
                'summary_report_id', 'first_name', 'last_name', 
                'completed_programs', 'total_programs', 
                'completion_percentage', 'category'
            ]
            detailed_df_to_save = detailed_df_to_save[cols_to_insert]
            
            detailed_df_to_save.to_sql('detailed_reports', conn, if_exists='append', index=False)

        conn.commit()
        logger.info(f"Successfully saved report: {week_label}")
        return summary_report_id
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving report: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_saved_reports_metadata(report_date=None, selected_week=None):
    """
    Retrieves metadata for all saved reports, with optional filtering by report_date and selected_week.
    """
    conn = None
    try:
        conn = get_db_connection()
        query = """
            SELECT id, report_date, week_label, selected_month, selected_week, 
                   selected_grade, min_completion_percentage, report_type, timestamp 
            FROM summary_reports
        """
        conditions = []
        params = []

        if report_date:
            conditions.append("report_date = ?")
            params.append(report_date.strftime('%Y-%m-%d'))
        
        if selected_week and selected_week != "All":
            conditions.append("selected_week = ?")
            params.append(selected_week)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        logger.error(f"Error retrieving report metadata: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def load_report_data(summary_report_id):
    """Loads a specific summary and detailed report by its ID with error handling."""
    conn = None
    try:
        conn = get_db_connection()
        
        # Load summary metadata using parameterized query to prevent SQL injection
        summary_meta_query = """
            SELECT * FROM summary_reports 
            WHERE id = ?
        """
        summary_meta_df = pd.read_sql_query(summary_meta_query, conn, params=(summary_report_id,))
        if summary_meta_df.empty:
            logger.warning(f"No report found with ID: {summary_report_id}")
            return None, None, None

        # Load summary details
        summary_details_query = """
            SELECT student_category, grade_6, grade_7, grade_8, grade_9, 
                   grade_10, grade_11, grade_12, total 
            FROM summary_report_details 
            WHERE summary_report_id = ?
        """
        summary_df = pd.read_sql_query(
            summary_details_query, 
            conn, 
            params=(summary_report_id,)
        )
        
        # Rename columns back to original format for display
        if not summary_df.empty:
            summary_df = summary_df.rename(
                columns={f'grade_{g}': f'Grade {g}' for g in range(6,13)}
            )
            summary_df = summary_df.rename(
                columns={'student_category': 'Student_Category'}
            )

        # Load detailed report
        detailed_query = """
            SELECT first_name, last_name, completed_programs, 
                   total_programs, completion_percentage, category 
            FROM detailed_reports 
            WHERE summary_report_id = ?
        """
        detailed_df = pd.read_sql_query(
            detailed_query, 
            conn, 
            params=(summary_report_id,)
        )
        
        # Rename columns back to original format for display in Streamlit
        if not detailed_df.empty:
            detailed_df = detailed_df.rename(columns={
                'first_name': 'First Name',
                'last_name': 'Last Name',
                'completed_programs': 'Completed Programs',
                'total_programs': 'Total Programs',
                'completion_percentage': 'Completion Percentage',
                'category': 'Category'
            })

    except Exception as e:
        logger.error(f"Error loading report data (ID: {summary_report_id}): {e}")
        return None, None, None
    finally:
        if conn:
            conn.close()

    return summary_meta_df, summary_df, detailed_df

if __name__ == '__main__':
    init_db()
    print(f"Database '{DATABASE_NAME}' initialized and tables created.")
