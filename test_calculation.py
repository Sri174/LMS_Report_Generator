import pandas as pd
import numpy as np

def test_percentage_conversion():
    """Test the percentage conversion function"""
    # Sample data with percentage symbols
    sample_data = pd.Series(['100.0 %', '85.5 %', '0.0 %', 'NaN', '75.0 %'])

    def convert_percentage_to_numeric(series):
        # Convert to string first, then strip '%' and convert to numeric
        return pd.to_numeric(series.astype(str).str.strip().str.rstrip('%'), errors='coerce')

    converted = convert_percentage_to_numeric(sample_data)
    print("Original data:", sample_data.tolist())
    print("Converted data:", converted.tolist())

    # Test completion calculation
    total_programs = 5
    completed_programs = pd.Series([5, 4, 0, 2, 3])  # Example completion counts
    completion_percentage = (completed_programs / total_programs) * 100

    print("\nCompletion calculation test:")
    print("Completed programs:", completed_programs.tolist())
    print("Completion percentages:", completion_percentage.tolist())

    # Test categorization
    conditions = [
        completion_percentage > 90,
        (completion_percentage > 75) & (completion_percentage <= 90),
        (completion_percentage > 55) & (completion_percentage <= 75),
        (completion_percentage > 35) & (completion_percentage <= 55),
        completion_percentage <= 35
    ]
    choices = [
        '#Students who completed more than 90%',
        '#Students who completed 75 to 90%',
        '#Students who completed 55 to 75%',
        '#Students who completed 35 to 55%',
        '#Students who completed less than 35%'
    ]

    categories = np.select(conditions, choices, default='#Students who completed less than 35%')
    print("Categories:", categories.tolist())

if __name__ == "__main__":
    test_percentage_conversion()
