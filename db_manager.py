import sqlite3
import pandas as pd
from datetime import datetime

DATABASE_NAME = 'lms_reports.db'

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
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
    conn.close()

def save_report(report_date, week_label, selected_month, selected_week, selected_grade, min_completion_percentage, report_type, summary_df, detailed_df):
    """Saves a generated report (summary and detailed) to the database."""
    conn = sqlite3.connect(DATABASE_NAME)
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
            summary_df_to_save['total'] = 0 # Default to 0 if not present (e.g., single grade report)

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
    conn.close()
    return summary_report_id

def get_saved_reports_metadata():
    """Retrieves metadata for all saved reports."""
    conn = sqlite3.connect(DATABASE_NAME)
    query = "SELECT id, report_date, week_label, selected_month, selected_week, selected_grade, min_completion_percentage, report_type, timestamp FROM summary_reports ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def load_report_data(summary_report_id):
    """Loads a specific summary and detailed report by its ID."""
    conn = sqlite3.connect(DATABASE_NAME)

    # Load summary metadata
    summary_meta_query = f"SELECT * FROM summary_reports WHERE id = {summary_report_id}"
    summary_meta_df = pd.read_sql_query(summary_meta_query, conn)

    # Load summary details
    summary_details_query = f"SELECT student_category, grade_6, grade_7, grade_8, grade_9, grade_10, grade_11, grade_12, total FROM summary_report_details WHERE summary_report_id = {summary_report_id}"
    summary_df = pd.read_sql_query(summary_details_query, conn)
    
    # Rename columns back to original format for display
    summary_df = summary_df.rename(columns={f'grade_{g}': f'Grade {g}' for g in range(6,13)})
    summary_df = summary_df.rename(columns={'student_category': 'Student_Category'})

    # Load detailed report
    detailed_query = f"SELECT first_name, last_name, completed_programs, total_programs, completion_percentage, category FROM detailed_reports WHERE summary_report_id = {summary_report_id}"
    detailed_df = pd.read_sql_query(detailed_query, conn)
    
    # Rename columns back to original format for display in Streamlit
    detailed_df = detailed_df.rename(columns={
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'completed_programs': 'Completed Programs',
        'total_programs': 'Total Programs',
        'completion_percentage': 'Completion Percentage',
        'category': 'Category'
    })

    conn.close()
    return summary_meta_df, summary_df, detailed_df

if __name__ == '__main__':
    init_db()
    print(f"Database '{DATABASE_NAME}' initialized and tables created.")
