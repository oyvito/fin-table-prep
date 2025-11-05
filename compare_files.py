import pandas as pd
import sys

def compare_excel_files(file1_path, file2_path, output_path):
    """
    Compares two Excel files and saves a detailed comparison report.
    """
    try:
        df1 = pd.read_excel(file1_path)
        df1_source = "rebuilt"
    except FileNotFoundError:
        print(f"Error: File not found at {file1_path}")
        return

    try:
        df2 = pd.read_excel(file2_path)
        df2_source = "original"
    except FileNotFoundError:
        print(f"Error: File not found at {file2_path}")
        return

    # Ensure columns are in the same order for comparison
    if set(df1.columns) == set(df2.columns):
        df2 = df2[df1.columns]

    # Perform a full outer join to find all differences
    comparison_df = df1.merge(
        df2,
        how='outer',
        indicator=True
    )

    # Rename the indicator column for clarity
    comparison_df['_merge'] = comparison_df['_merge'].replace({
        'left_only': f'Kun i {df1_source}',
        'right_only': f'Kun i {df2_source}',
        'both': 'Identisk'
    })

    # Save the comparison file
    comparison_df.to_excel(output_path, index=False)
    print(f"Comparison file saved to {output_path}")
    print(f"Summary:\n{comparison_df['_merge'].value_counts()}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python compare_files.py <file1.xlsx> <file2.xlsx> <output.xlsx>")
        sys.exit(1)
    
    compare_excel_files(sys.argv[1], sys.argv[2], sys.argv[3])
