# lms_report_generator.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- Configuration ---
# Define the category labels exactly as they should appear in the report
CATEGORY_LABELS_ORDERED = [
    '#Students who completed more than 90%',
    '#Students who completed 75 to 90%',
    '#Students who completed 55 to 75%',
    '#Students who completed 35 to 55%',
    '#Students who completed less than 35%',
    'Total No Of Students' # Corrected label to match PDF exactly
]
# Grades covered in the report (6th to 12th)
ALL_GRADES = list(range(6, 13))

# --- Configuration: Column Names ---
# You MUST update these to match your actual Excel file column names
FIRST_NAME_COL = 'First name' # Change if different
LAST_NAME_COL = 'Last name'   # Change if different
# --- IMPORTANT: CHANGE THIS TO YOUR ACTUAL COURSE TOTAL COLUMN NAME ---
COURSE_TOTAL_COL = 'Course total (Percentage)' # <--- UPDATE THIS LINE ---

# --- Helper Functions ---
def extract_grade(last_name_series):
    """Extracts grade number from the 'Last name' column."""
    # First try to extract grade from the beginning of the string
    extracted = last_name_series.str.extract(r'^(\d+)')[0]
    # If that fails, try to find any number in the string
    extracted = extracted.fillna(last_name_series.str.extract(r'(\d+)')[0])
    # Convert to numeric, coercing errors to NaN, then to -1 for invalid grades
    grade_series = pd.to_numeric(extracted, errors='coerce').fillna(-1).astype(int)
    # Ensure grades are within valid range (6-12)
    grade_series = grade_series[(grade_series >= 6) & (grade_series <= 12)]
    return grade_series

def categorize_completion_percentage(percentage_series):
    """
    Categorizes a student's overall completion percentage into bands.
    Takes a pandas Series of percentages.
    Returns a pandas Series of category labels.
    """
    # Use np.select for vectorized categorization, matching PDF bands precisely
    conditions = [
        percentage_series > 90,
        (percentage_series > 75) & (percentage_series <= 90),
        (percentage_series > 55) & (percentage_series <= 75),
        (percentage_series > 35) & (percentage_series <= 55),
        percentage_series <= 35
    ]
    choices = [
        '#Students who completed more than 90%',
        '#Students who completed 75 to 90%',
        '#Students who completed 55 to 75%',
        '#Students who completed 35 to 55%',
        '#Students who completed less than 35%'
    ]
    # np.select is vectorized and efficient for Series
    return np.select(conditions, choices, default='#Students who completed less than 35%')

def calculate_program_completion(df):
    """
    Calculate completion percentage by counting how many programs each student
    has completed (100%) out of all Virtual Programming Lab programs.
    Returns a DataFrame with detailed student completion data.
    """
    # Convert all column names to strings for consistent comparison
    all_columns = [str(col) for col in df.columns]

    # Look for columns containing 'virtual programming lab' (case insensitive)
    vpl_columns = [col for col in all_columns if 'virtual programming lab' in str(col).lower()]

    if not vpl_columns:
        st.error("Error: Could not find any Virtual Programming Lab columns.")
        st.write("Please check that your Excel file contains columns with 'Virtual programming lab' in their names.")
        st.write("First 20 column names in your file:")
        st.write("\n".join([f"{i}: {col}" for i, col in enumerate(all_columns[:20], 1)]))
        return pd.DataFrame()

    try:
        # Convert all identified columns to numeric, handling percentage symbols
        def convert_percentage_to_numeric(series):
            # Convert to string first, then strip '%' and convert to numeric
            return pd.to_numeric(series.astype(str).str.strip().str.rstrip('%'), errors='coerce')

        vpl_data = df[vpl_columns].apply(convert_percentage_to_numeric)

        # For each student, count how many programs they've completed (value = 100%)
        completed_programs = (vpl_data == 100).sum(axis=1)
        total_programs = len(vpl_columns)

        # Calculate completion percentage for each student
        completion_percentage = (completed_programs / total_programs) * 100
        completion_percentage = completion_percentage.round(1)

        # Categorize each student
        categories = []
        for perc in completion_percentage:
            if perc > 90:
                cat = "#Students who completed more than 90%"
            elif (perc > 75) & (perc <= 90):
                cat = "#Students who completed 75 to 90%"
            elif (perc > 55) & (perc <= 75):
                cat = "#Students who completed 55 to 75%"
            elif (perc > 35) & (perc <= 55):
                cat = "#Students who completed 35 to 55%"
            else:
                cat = "#Students who completed less than 35%"
            categories.append(cat)

        # Create detailed DataFrame
        detailed_df = pd.DataFrame({
            'First Name': df['First name'],
            'Last Name': df['Last name'],
            'Completed Programs': completed_programs.astype(int),
            'Total Programs': total_programs,
            'Completion Percentage': completion_percentage,
            'Category': categories
        })

        return detailed_df

    except Exception as e:
        st.error(f"Error processing programming lab data: {str(e)}")
        st.write("Please check that the identified columns contain numeric values.")
        return pd.DataFrame()

def process_single_file_current_week(df, week_label="Current_Week"):
    """
    Processes a single DataFrame by calculating program completion from Virtual Programming Lab columns
    and returns a summary DataFrame for the current week.
    """
    # --- STEP 1: Validate Required Columns ---
    required_cols = [FIRST_NAME_COL, LAST_NAME_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Error: The following required columns are missing in the uploaded file: {missing_cols}")
        st.write("Please check that your Excel file contains these exact column names (case-sensitive):")
        st.write("\n".join([f"- {col}" for col in required_cols]))
        st.write("\nAvailable columns in your file:", ", ".join([f'"{col}"' for col in df.columns]))
        return pd.DataFrame(), pd.DataFrame()

    # --- STEP 2: Calculate Program Completion ---
    detailed_df = calculate_program_completion(df)
    if detailed_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # --- STEP 3: Add calculated percentages to the dataframe ---
    df['Calculated_Completion'] = detailed_df['Completion Percentage']

    # --- STEP 4: Extract Grade ---
    df['Grade'] = extract_grade(df[LAST_NAME_COL])
    df_filtered = df[(df['Grade'] >= 6) & (df['Grade'] <= 12)].copy()

    if df_filtered.empty:
        st.error("No students found in grades 6-12 in the uploaded file.")
        return pd.DataFrame(), pd.DataFrame()

    # --- STEP 5: Categorize Each Student Based on Calculated Percentage ---
    df_filtered['Student_Category'] = categorize_completion_percentage(df_filtered['Calculated_Completion'])

    # --- STEP 6: Create a pivot table for accurate counting ---
    # Create a cross-tabulation of categories vs grades
    cross_tab = pd.crosstab(
        index=df_filtered['Student_Category'],
        columns=df_filtered['Grade'],
        dropna=False
    )

    # Ensure all categories and grades are represented
    for grade in ALL_GRADES:
        if grade not in cross_tab.columns:
            cross_tab[grade] = 0

    # Reorder columns to match grades 6-12
    cross_tab = cross_tab[ALL_GRADES]

    # Add a 'Total' column
    cross_tab['Total'] = cross_tab.sum(axis=1)

    # Ensure all categories are present, even if empty
    for category in CATEGORY_LABELS_ORDERED[:-1]:  # Exclude 'Total No Of Students'
        if category not in cross_tab.index:
            cross_tab.loc[category] = 0

    # Add the 'Total No Of Students' row
    cross_tab.loc['Total No Of Students'] = cross_tab.sum()

    # Reorder rows to match the desired order
    cross_tab = cross_tab.reindex(CATEGORY_LABELS_ORDERED)

    # Reset index to make Category a column
    summary_df = cross_tab.reset_index().rename(columns={'index': 'Category'})

    # Ensure all column names are strings to avoid mixed type warnings
    summary_df.columns = summary_df.columns.astype(str)

    return summary_df, detailed_df

def to_excel_current_week_correct(df_to_save):
    """Converts the final summary DataFrame to a formatted Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_to_save.to_excel(writer, sheet_name='LMS_Report', index=False)
        worksheet = writer.sheets['LMS_Report']
        
        header_format = writer.book.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center', 'border': 1
        })
        
        # Write the two-row header structure
        for col_num, column_title in enumerate(df_to_save.columns.values):
            if isinstance(column_title, tuple) and len(column_title) == 2:
                # MultiIndex column for data: (Grade, Week_Label)
                grade, date = column_title
                # Write grade (e.g., "9th") in the first header row
                worksheet.write(0, col_num, f"{grade}th", header_format)
                # Write date/week label in the second header row
                worksheet.write(1, col_num, date, header_format)
            else:
                # The 'Category' column
                worksheet.write(0, col_num, column_title, header_format)
                if column_title == 'Category':
                    worksheet.merge_range(0, col_num, 1, col_num, column_title, header_format)
        
        # Set column widths
        worksheet.set_column('A:Z', 15) 
        
    processed_data = output.getvalue()
    return processed_data

# --- Streamlit App ---
st.set_page_config(page_title="LMS Report Generator", layout="wide")
st.title("📊 LMS Course Completion Report Generator (Using Course Total)")

# --- Instructions ---
# with st.expander("ℹ️ How to Use This App"):
#     st.write("""
#     1.  **Update Column Names:** Make sure the column names in the script (at the top) match the names in your Excel file:
#         *   `STUDENT_ID_COL`
#         *   `FIRST_NAME_COL`
#         *   `LAST_NAME_COL`
#         *   **`COURSE_TOTAL_COL` (Most Important!)** - This should be the name of the column containing the overall completion percentage (e.g., 80.0, 95.5).
#     2.  **Upload File:** Upload your Excel file (e.g., `Python Exercises Grades.xlsx`).
#     3.  **Check Preview:** View the generated report.
#     4.  **Download:** Download the formatted Excel report.
#     """)

st.header("📥 Upload Excel File")
st.subheader("Upload data for the current week")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

# Allow user to override the week label
week_label = st.text_input("Enter Week Label", value="Current_Week")

single_summary_df = None
detailed_df = None

if uploaded_file is not None:
    try:
        # Read the uploaded Excel file
        df_raw = pd.read_excel(uploaded_file)
        st.write(f"✅ File loaded successfully. Shape: {df_raw.shape}")
        # st.write("First few rows of your data:")
        # st.dataframe(df_raw.head()) # Optional: Show raw data snippet

        # Process the DataFrame
        single_summary_df, detailed_df = process_single_file_current_week(df_raw, week_label)
        
        if not single_summary_df.empty:
             st.success("✅ File processed successfully!")
             st.subheader("📊 Preview of Current Week Report:")
             # Display the report preview, formatting numbers without decimals
             # Use a container to potentially control width better
             with st.container():
                 # Create a copy to avoid modifying the original dataframe
                 display_df = single_summary_df.copy()
                 # Format only numeric columns
                 numeric_cols = display_df.select_dtypes(include=[np.number]).columns
                 format_dict = {col: "{:.0f}" for col in numeric_cols}
                 st.dataframe(
                     display_df.style.format(format_dict, na_rep='0'),
                     width='stretch' # Makes table use full width of container
                 )
             
             # Display detailed report
             st.subheader("📋 Detailed Student Completion Report:")
             st.dataframe(detailed_df)
        else:
             st.error("❌ Processing resulted in an empty report. Please check the data and column names.")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred processing the file: {e}")
        st.write(f"Technical details: {type(e).__name__} - {e}")

st.header("💾 Download Report")
if single_summary_df is not None and not single_summary_df.empty:
    # Generate the Excel file data in memory
    excel_data = to_excel_current_week_correct(single_summary_df)
    # Provide a download button for the user
    st.download_button(
        label="📥 Download Current Week Report (Excel)",
        data=excel_data, # The binary Excel data
        file_name=f'LMS_Report_{week_label.replace(" ", "_")}.xlsx', # Suggested filename
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' # MIME type for .xlsx
    )

if detailed_df is not None and not detailed_df.empty:
    # Generate the Excel file data for detailed report
    detailed_excel = to_excel_current_week_correct(detailed_df)  # Reuse the function
    st.download_button(
        label="📥 Download Detailed Student Report (Excel)",
        data=detailed_excel,
        file_name=f'Detailed_Report_{week_label.replace(" ", "_")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
