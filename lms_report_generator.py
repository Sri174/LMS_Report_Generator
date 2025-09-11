# lms_report_generator.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import db_manager
from datetime import datetime

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

def process_single_file_current_week(df, week_label="Current_Week", selected_grade="All", min_completion_percentage=0):
    """
    Processes a single DataFrame by calculating program completion from Virtual Programming Lab columns
    and returns a summary DataFrame for the current week, applying filters.
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

    # --- STEP 2: Calculate Program Completion (initial, unfiltered detailed data) ---
    initial_detailed_df = calculate_program_completion(df)
    if initial_detailed_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # --- STEP 3: Add calculated percentages and grade to the original df for filtering ---
    df['Calculated_Completion'] = initial_detailed_df['Completion Percentage']
    df['Grade'] = extract_grade(df[LAST_NAME_COL])

    # --- STEP 4: Apply Grade and Minimum Completion Percentage Filters ---
    df_filtered_students = df[(df['Grade'] >= 6) & (df['Grade'] <= 12)].copy()

    if selected_grade != "All":
        df_filtered_students = df_filtered_students[df_filtered_students['Grade'] == selected_grade]

    df_filtered_students = df_filtered_students[df_filtered_students['Calculated_Completion'] >= min_completion_percentage]

    if df_filtered_students.empty:
        st.warning("No students match the selected filters (Grade and Minimum Completion Percentage).")
        return pd.DataFrame(), pd.DataFrame()

    # --- STEP 5: Construct the final detailed_df from filtered students ---
    final_detailed_df = pd.DataFrame({
        'First Name': df_filtered_students[FIRST_NAME_COL],
        'Last Name': df_filtered_students[LAST_NAME_COL],
        'Completed Programs': initial_detailed_df.loc[df_filtered_students.index, 'Completed Programs'].astype(int),
        'Total Programs': initial_detailed_df.loc[df_filtered_students.index, 'Total Programs'],
        'Completion Percentage': df_filtered_students['Calculated_Completion'],
        'Category': categorize_completion_percentage(df_filtered_students['Calculated_Completion'])
    })
    
    # --- STEP 6: Categorize Filtered Students for Summary Table ---
    df_filtered_students['Student_Category'] = categorize_completion_percentage(df_filtered_students['Calculated_Completion'])

    # --- STEP 7: Create a pivot table for accurate counting ---
    # Create a cross-tabulation of categories vs grades
    cross_tab = pd.crosstab(
        index=df_filtered_students['Student_Category'], # Use df_filtered_students here
        columns=df_filtered_students['Grade'], # Use df_filtered_students here
        dropna=False
    )

    # If a single grade is selected, ensure only that grade column is present
    if selected_grade != "All":
        # Ensure the selected grade is in the cross_tab columns, if not, add it with zeros
        if selected_grade not in cross_tab.columns:
            cross_tab[selected_grade] = 0
        # Keep only the selected grade column
        cross_tab = cross_tab[[selected_grade]]
    else:
        # Ensure all grades are represented if "All" is selected
        for grade in ALL_GRADES:
            if grade not in cross_tab.columns:
                cross_tab[grade] = 0
        # Reorder columns to match grades 6-12
        cross_tab = cross_tab[ALL_GRADES]

    # Add a 'Total' column only if "All" grades are selected
    if selected_grade == "All":
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
    summary_df = cross_tab.reset_index().rename(columns={'index': 'Student_Category'})

    # Format column names to match the desired header format
    column_mapping = {'Student_Category': 'Student_Category'}
    if selected_grade != "All":
        column_mapping[selected_grade] = f'Grade {selected_grade}'
    else:
        for grade in ALL_GRADES:
            column_mapping[grade] = f'Grade {grade}'
        column_mapping['Total'] = 'Total' # Add 'Total' to mapping only if "All" grades
    
    summary_df = summary_df.rename(columns=column_mapping)

    # Ensure all column names are strings to avoid mixed type warnings
    summary_df.columns = summary_df.columns.astype(str)

    return summary_df, final_detailed_df

def process_two_files_comparison(df1, df2, week1_label, week2_label, selected_grade="All", min_completion_percentage=0):
    """
    Processes two DataFrames and creates a comparison report with a multi-level header, applying filters.
    """
    summary1, _ = process_single_file_current_week(df1, week1_label, selected_grade, min_completion_percentage)
    summary2, _ = process_single_file_current_week(df2, week2_label, selected_grade, min_completion_percentage)

    if summary1.empty or summary2.empty:
        return pd.DataFrame()

    # Set index to Student_Category for merging
    summary1 = summary1.set_index('Student_Category')
    summary2 = summary2.set_index('Student_Category')

    # Create a new DataFrame for the comparison
    comparison_df = pd.DataFrame(index=summary1.index)

    for grade in range(6, 13):
        col_name = f'Grade {grade}'
        comparison_df[(col_name, week1_label)] = summary1[col_name]
        comparison_df[(col_name, week2_label)] = summary2[col_name]
    
    comparison_df[('Total', week1_label)] = summary1['Total']
    comparison_df[('Total', week2_label)] = summary2['Total']
    
    comparison_df.columns = pd.MultiIndex.from_tuples(comparison_df.columns)
    
    return comparison_df.reset_index()

def to_excel_current_week_correct(df_to_save):
    """Converts the final summary DataFrame to a formatted Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if isinstance(df_to_save.columns, pd.MultiIndex):
            # Write the header manually
            worksheet = writer.add_worksheet('LMS_Report')
            header_format = writer.book.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center', 'border': 1
            })

            # Write the 'Student_Category' header
            worksheet.merge_range(0, 0, 1, 0, 'Student_Category', header_format)

            # Write the merged headers for the grades
            col_num = 1
            for i in range(0, len(df_to_save.columns), 2):
                grade = df_to_save.columns[i][0]
                worksheet.merge_range(0, col_num, 0, col_num + 1, grade, header_format)
                worksheet.write(1, col_num, df_to_save.columns[i][1], header_format)
                worksheet.write(1, col_num + 1, df_to_save.columns[i+1][1], header_format)
                col_num += 2
            
            # Flatten the MultiIndex columns for writing data
            # The first column 'Student_Category' is not part of MultiIndex, so handle it separately
            flattened_df = df_to_save.copy()
            flattened_df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in flattened_df.columns]
            
            # Flatten the MultiIndex columns for writing data
            # The first column 'Student_Category' is not part of MultiIndex, so handle it separately
            flattened_df = df_to_save.copy()
            flattened_df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in flattened_df.columns]
            
            # Write the DataFrame data without the header
            flattened_df.to_excel(writer, sheet_name='LMS_Report', index=False, header=False, startrow=2)
        else:
            df_to_save.to_excel(writer, sheet_name='LMS_Report', index=False)
        
        # Set column widths
        worksheet = writer.sheets['LMS_Report']
        worksheet.set_column('A:Z', 15) 
        
    processed_data = output.getvalue()
    return processed_data

# --- Streamlit App ---
st.set_page_config(page_title="LMS Report Generator", layout="wide")
st.title("📊 LMS Course Completion Report Generator (Using Course Total)")

# Initialize the database
db_manager.init_db()

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

st.sidebar.title("Report Options")
report_type = st.sidebar.radio("Select Report Type", ("Single Week Report", "Two-Week Comparison", "View Saved Reports"))

# Global filters
st.sidebar.subheader("Filters")

report_calculated_date = st.sidebar.date_input("Report Calculated Date", value=pd.to_datetime("today"))

# Month Filter (Placeholder for future implementation)
selected_month = st.sidebar.selectbox("Select Month", ["All", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])

# Week Filter (Placeholder for future implementation)
selected_week = st.sidebar.selectbox("Select Week", ["All", "Week 1", "Week 2", "Week 3", "Week 4"])

# Grade Filter
selected_grade = st.sidebar.selectbox("Select Grade", ["All"] + ALL_GRADES)

min_completion_percentage = st.sidebar.number_input(
    "Minimum Completion Percentage for Students", min_value=0, max_value=100, value=0, step=1
)


if report_type == "Single Week Report":
    st.header("📥 Upload Excel File for Single Week")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"], key="single")
    week_label = st.text_input("Enter Week Label", value="Current_Week")

    summary_df = pd.DataFrame()
    detailed_df = pd.DataFrame()

    if uploaded_file:
        try:
            df_raw = pd.read_excel(uploaded_file)
            summary_df, detailed_df = process_single_file_current_week(df_raw, week_label, selected_grade, min_completion_percentage)
            
            if not summary_df.empty:
                st.success("✅ Single week report processed successfully!")
                st.subheader("📊 Preview of Single Week Report:")
                st.dataframe(summary_df)
                
                st.header("💾 Download Report")
                excel_data = to_excel_current_week_correct(summary_df)
                st.download_button(
                    label="📥 Download Single Week Report (Excel)",
                    data=excel_data,
                    file_name=f'LMS_Report_{week_label}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            
            if not detailed_df.empty:
                st.subheader("📋 Detailed Student Completion Report:")
                # The detailed_df is already filtered by grade and min_completion_percentage in process_single_file_current_week
                st.dataframe(detailed_df)

            # Save report to database
            if st.button("💾 Save Single Week Report to Database"):
                report_id = db_manager.save_report(
                    report_date=report_calculated_date,
                    week_label=week_label,
                    selected_month=selected_month,
                    selected_week=selected_week,
                    selected_grade=selected_grade,
                    min_completion_percentage=min_completion_percentage,
                    report_type="Single Week Report",
                    summary_df=summary_df,
                    detailed_df=detailed_df
                )
                st.success(f"Report saved to database with ID: {report_id}")

        except Exception as e:
            st.error(f"An error occurred: {e}")


elif report_type == "View Saved Reports":
    st.header("📚 View Saved Reports")
    
    # Filters for viewing saved reports
    st.subheader("Filter Saved Reports")
    view_report_date_filter = st.date_input("Filter by Report Date", value=None, key="view_date_filter")
    view_week_filter = st.selectbox("Filter by Week", ["All", "Week 1", "Week 2", "Week 3", "Week 4"], key="view_week_filter")

    saved_reports_meta = db_manager.get_saved_reports_metadata(
        report_date=view_report_date_filter,
        selected_week=view_week_filter
    )

    if saved_reports_meta.empty:
        st.info("No reports saved yet or no reports match the selected filters. Upload and save a report first!")
    else:
        st.subheader("Available Reports:")
        # Display a selection box for saved reports
        saved_reports_meta['display_name'] = saved_reports_meta.apply(
            lambda row: f"{row['report_date']} - {row['week_label']} ({row['report_type']})", axis=1
        )
        
        selected_report_id = st.selectbox(
            "Select a report to view",
            options=saved_reports_meta['id'],
            format_func=lambda x: saved_reports_meta[saved_reports_meta['id'] == x]['display_name'].iloc[0]
        )

        if selected_report_id:
            summary_meta, summary_df, detailed_df = db_manager.load_report_data(selected_report_id)
            

            if not summary_df.empty:
                st.subheader("📊 Saved Summary Report:")
                st.dataframe(summary_df)
            else:
                st.info("No summary data available for this report (e.g., comparison report).")



elif report_type == "Two-Week Comparison":
    st.header("📥 Upload Excel Files for Comparison")
    week1_label = st.text_input("Enter Label for Week 1", value="26-Jul")
    uploaded_file_1 = st.file_uploader("Choose Excel file for Week 1", type=["xlsx"], key="week1")
    
    week2_label = st.text_input("Enter Label for Week 2", value="02-Aug")
    uploaded_file_2 = st.file_uploader("Choose Excel file for Week 2", type=["xlsx"], key="week2")

    comparison_df = pd.DataFrame()
    detailed_df1 = pd.DataFrame()
    detailed_df2 = pd.DataFrame()

    if uploaded_file_1 and uploaded_file_2:
        try:
            df1 = pd.read_excel(uploaded_file_1)
            df2 = pd.read_excel(uploaded_file_2)
            
            comparison_df = process_two_files_comparison(df1, df2, week1_label, week2_label, selected_grade, min_completion_percentage)
            _, detailed_df1 = process_single_file_current_week(df1, week1_label, selected_grade, min_completion_percentage)
            _, detailed_df2 = process_single_file_current_week(df2, week2_label, selected_grade, min_completion_percentage)

            if not comparison_df.empty:
                st.success("✅ Comparison report processed successfully!")
                st.subheader("📊 Preview of Two-Week Comparison Report:")
                st.dataframe(comparison_df)
                
                st.header("💾 Download Report")
                excel_data = to_excel_current_week_correct(comparison_df)
                st.download_button(
                    label="📥 Download Comparison Report (Excel)",
                    data=excel_data,
                    file_name='LMS_Comparison_Report.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            
            if not detailed_df1.empty and not detailed_df2.empty:
                st.subheader("📋 Detailed Student Completion Report (Week 1):")
                st.dataframe(detailed_df1)

                st.subheader("📋 Detailed Student Completion Report (Week 2):")
                st.dataframe(detailed_df2)

            # Save comparison report to database
            if st.button("💾 Save Two-Week Comparison Report to Database"):
                # For comparison reports, the summary_df in db_manager.save_report expects a single-week format.
                # We need to decide how to store comparison data.
                # For now, let's save the metadata and indicate it's a comparison report.
                # The actual comparison_df structure is not directly compatible with summary_report_details table.
                # A more complex schema or separate table would be needed for full comparison data storage.
                # For simplicity, we'll save the metadata and the two detailed dataframes.
                report_id = db_manager.save_report(
                    report_date=report_calculated_date,
                    week_label=f"{week1_label} vs {week2_label}", # Combine labels for comparison
                    selected_month=selected_month,
                    selected_week=selected_week,
                    selected_grade=selected_grade,
                    min_completion_percentage=min_completion_percentage,
                    report_type="Two-Week Comparison",
                    summary_df=pd.DataFrame(), # No direct summary_df for comparison in current schema
                    detailed_df=pd.concat([detailed_df1.assign(Week=week1_label), detailed_df2.assign(Week=week2_label)])
                )
                st.success(f"Comparison report metadata saved to database with ID: {report_id}")

        except Exception as e:
            st.error(f"An error occurred: {e}")
