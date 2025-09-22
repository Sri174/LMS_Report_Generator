# 📊 LMS Report Generator

A complete report generation system for Learning Management Systems (LMS), built with Python, Streamlit, and SQLite. It enables uploading, parsing, validating, and processing LMS data from Excel sheets, applying specific calculation rules, and generating comprehensive, payroll-ready reports.

# 🚀 Url

*   **✅ Check the application here:** (https://lmsreportgenerator.streamlit.app/)
  
## ✨ Features

*   **📤 Upload LMS Data Files (Excel):** Easily upload attendance and other relevant data in Excel format.
*   **⚙️ Parse Data into SQLite:** Efficiently parses uploaded data and stores it in a structured SQLite database for processing.
*   **✅ Automated Calculations:** Applies complex business logic and calculations to generate accurate metrics and insights.
*   **📋 Customizable Report Generation:** Generates detailed and customizable reports tailored to specific LMS requirements.
*   **📊 Reports:**
    *   Attendance summary per employee
    *   Detailed month-wise breakdown
    *   Export to CSV for further analysis or payroll integration.
*   **🖥 Streamlit Frontend:** Provides an intuitive and modern user interface for seamless interaction.
*   **🗄 SQLite Database Backend:** Utilizes a robust SQLite database for efficient storage and retrieval of employee and attendance tracking data.

## 🚀 Tech Stack

*   **Frontend:** Streamlit
*   **Backend:** Python 3.x (based on `requirements.txt`, likely 3.11+)
*   **Database:** SQLite
*   **Data Processing:** Pandas, Openpyxl, XlsxWriter

## 📦 Installation

To get a local copy up and running, follow these simple steps.

### Prerequisites

*   Python 3.x
*   `pip` (Python package installer)

### Steps

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/Sri174/LMS_Report_Generator.git
    cd LMS_Report_Generator
    ```
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Usage

To run the LMS Report Generator as a Streamlit application:

```bash
streamlit run lms_report_generator.py
```

*(Note: The main script `lms_report_generator.py` is assumed to be the entry point for the Streamlit application. If your Streamlit app is in a different file, please adjust the command accordingly.)*

## 📂 Project Structure

```
LMS_Report_Generator/
├── .gitignore             # Specifies intentionally untracked files to ignore by Git.
├── calculate_all.py       # Contains functions for performing all necessary calculations on processed data.
├── db_manager.py          # Handles database connection, session management, and high-level database operations.
├── db_utils.py            # Provides utility functions for common database interactions (insertion, retrieval, updates).
├── lms_report_generator.py# The main script orchestrating the report generation process (data input to output).
├── process_excel.py       # Manages reading, parsing, and initial processing of data from Excel files.
├── requirements.txt       # Lists all Python dependencies required to run the project.
├── test_calculation.py    # Contains unit tests to ensure the correctness of the calculation logic.
└── uploads/               # Directory intended for storing uploaded Excel files or other input data.
```

## 📝 Report Highlights

*   **Summary Report:** Overall percentage calculation, grade wise calculation, weekly comparison.
*   **Detailed Report:** Detailed report of each student which contains completed programs and the percentage of the student.
*   **CSV Export:** Ready for overall calculation or further data analysis.

## 👨‍💻 Author

Veerachinnu – [GitHub Profile](https://github.com/Sri174)
