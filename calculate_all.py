import pandas as pd
import numpy as np

# Load the Excel file
df = pd.read_excel('Python Exercises Grades (1).xlsx')

# Convert all column names to strings for consistent comparison
all_columns = [str(col) for col in df.columns]

# Look for columns containing 'virtual programming lab' (case insensitive)
vpl_columns = [col for col in all_columns if 'virtual programming lab' in str(col).lower()]

if not vpl_columns:
    print("Error: Could not find any Virtual Programming Lab columns.")
else:
    total_programs = len(vpl_columns)
    print(f"Total programs: {total_programs}")

    # Convert all identified columns to numeric, handling percentage symbols
    def convert_percentage_to_numeric(series):
        # Convert to string first, then strip '%' and convert to numeric
        return pd.to_numeric(series.astype(str).str.strip().str.rstrip('%'), errors='coerce')

    vpl_data = df[vpl_columns].apply(convert_percentage_to_numeric)

    # For each student, count how many programs they've completed (value = 100%)
    completed_programs = (vpl_data == 100).sum(axis=1)

    # Calculate completion percentage for each student
    completion_percentage = (completed_programs / total_programs) * 100
    completion_percentage = completion_percentage.round(1)

    # Categorize
    categories = []
    for perc in completion_percentage:
        if perc >= 90:
            cat = "90-100%"
        elif perc >= 75:
            cat = "75-90%"
        elif perc >= 55:
            cat = "55-75%"
        elif perc >= 35:
            cat = "35-55%"
        else:
            cat = "<35%"
        categories.append(cat)

    # Collect results
    results = []
    for i in range(len(df)):
        first = df.iloc[i]['First name']
        last = df.iloc[i]['Last name']
        comp = int(completed_programs[i])
        perc = completion_percentage[i]
        cat = categories[i]
        line = f"{first} {last}: {comp}/{total_programs} programs ({perc:.1f}%) - Category: {cat}"
        results.append(line)
        print(line)  # Still print for immediate feedback

    # Write to file
    with open('results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    print(f"\nResults for all {len(df)} students written to results.txt")
