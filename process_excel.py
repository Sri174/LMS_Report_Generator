import pandas as pd
import numpy as np
from io import BytesIO

# Configuration
CATEGORY_LABELS = {
    '>90%': '#Students who completed more than 90%',
    '75-90%': '#Students who completed 75 to 90%',
    '55-75%': '#Students who completed 55 to 75%',
    '35-55%': '#Students who completed 35 to 55%',
    '<35%': '#Students who completed less than 35%'
}
GRADES = list(range(6, 13))  # 6th to 12th

def extract_grade(last_name_series):
    """Extracts grade number from the 'Last name' column."""
    extracted_grade_series = last_name_series.str.extract(r'^(\d+)')[0]
    grade_series = pd.to_numeric(extracted_grade_series, errors='coerce').fillna(-1).astype(int)
    return grade_series

def categorize_completion(pct):
    """Categorizes completion percentage into bands."""
    if pct > 90:
        return '>90%'
    elif pct >= 75:
        return '75-90%'
    elif pct >= 55:
        return '55-75%'
    elif pct >= 35:
        return '35-55%'
    else:
        return '<35%'

def clean_data(df):
    """Clean the DataFrame: remove duplicates, handle missing values."""
    print("Original data shape:", df.shape)
    print("Columns:", list(df.columns))

    # Remove duplicate rows
    df = df.drop_duplicates()
    print("After removing duplicates:", df.shape)

    # Handle missing values in key columns
    if 'Last name' in df.columns:
        df['Last name'] = df['Last name'].fillna('Unknown')

    # Fill NaN in lab columns with 0
    lab_columns = [col for col in df.columns if col.startswith('Virtual programming lab:')]
    for col in lab_columns:
        df[col] = df[col].fillna(0.0)

    print("Data cleaned.")
    return df

def process_file(df, week_label):
    """Processes the DataFrame to get category counts per grade."""
    # Extract Grade
    df['Grade'] = extract_grade(df['Last name'])
    df_filtered = df[(df['Grade'] >= 6) & (df['Grade'] <= 12)].copy()
    print(f"Students in grades 6-12: {len(df_filtered)}")

    # Detect Lab Columns
    lab_columns = [col for col in df_filtered.columns if col.startswith('Virtual programming lab:')]
    if not lab_columns:
        print("No 'Virtual programming lab:' columns found.")
        return pd.DataFrame()

    print(f"Found {len(lab_columns)} lab columns")

    # Convert Lab Completion to Binary
    for col in lab_columns:
        df_filtered[col] = df_filtered[col].fillna(0.0)
        df_filtered[col] = df_filtered[col].apply(lambda x: 1 if x == 100.0 else 0)

    # Calculate Completion Percentage and Category
    df_filtered['Completed Count'] = df_filtered[lab_columns].sum(axis=1)
    df_filtered['Total Labs'] = len(lab_columns)
    df_filtered['Completion %'] = np.where(
        df_filtered['Total Labs'] > 0,
        (df_filtered['Completed Count'] / df_filtered['Total Labs']) * 100,
        0.0
    )
    df_filtered['Category'] = df_filtered['Completion %'].apply(categorize_completion)

    # Generate Summary Counts
    summary_data = []
    for category_code, category_label in CATEGORY_LABELS.items():
        row_data = {'Category': category_label}
        for grade in GRADES:
            count = len(df_filtered[(df_filtered['Grade'] == grade) & (df_filtered['Category'] == category_code)])
            row_data[(grade, week_label)] = count
        summary_data.append(row_data)

    # Add Total row
    total_row_data = {'Category': 'Total No Of Students'}
    for grade in GRADES:
        total_count = len(df_filtered[df_filtered['Grade'] == grade])
        total_row_data[(grade, week_label)] = total_count
    summary_data.append(total_row_data)

    summary_df = pd.DataFrame(summary_data)
    return summary_df, df_filtered

def main():
    # Read the Excel file
    file_path = 'uploads/Python Exercises Grades.xlsx'
    try:
        df = pd.read_excel(file_path)
        print("File loaded successfully.")
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # Clean the data
    df_cleaned = clean_data(df)

    # Process the file
    summary_df, processed_df = process_file(df_cleaned, 'Python Exercises')

    if summary_df.empty:
        print("No data to process.")
        return

    # Save cleaned data
    df_cleaned.to_excel('cleaned_data.xlsx', index=False)
    print("Cleaned data saved to cleaned_data.xlsx")

    # Save processed data
    processed_df.to_excel('processed_data.xlsx', index=False)
    print("Processed data saved to processed_data.xlsx")

    # Save summary report
    summary_df.to_excel('summary_report.xlsx', index=False)
    print("Summary report saved to summary_report.xlsx")

    # Print summary
    print("\nSummary Report:")
    print(summary_df)

    # Additional statistics
    print(f"\nTotal students: {len(processed_df)}")
    print(f"Average completion %: {processed_df['Completion %'].mean():.2f}%")
    print(f"Median completion %: {processed_df['Completion %'].median():.2f}%")

    # Category distribution
    print("\nCategory Distribution:")
    category_counts = processed_df['Category'].value_counts()
    for category, count in category_counts.items():
        print(f"{category}: {count} students")

if __name__ == "__main__":
    main()
