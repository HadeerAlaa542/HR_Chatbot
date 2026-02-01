import camelot
import os
import arabic_reshaper
from bidi.algorithm import get_display

# Configuration
pdf_path = "sharjah_hr_law 8.pdf"
output_dir = "camelot_tables_fixed"

def fix_arabic(text):
    """
    Fixes Arabic text rendering by reshaping characters and applying Bidi algorithm.
    """
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

def parse_with_camelot():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Extracting tables from '{pdf_path}' using Camelot with Arabic Fixes...")
    print("Note: This process requires Ghostscript to be installed on your system.")

    try:
        # 1. Extract tables using 'lattice' mode (best for grid lines)
        # You can try 'stream' if lattice fails to find some tables.
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        print(f"Found {len(tables)} tables.")

        for i, table in enumerate(tables):
            # 2. Get the Pandas DataFrame
            df = table.df

            # 3. Apply Arabic Fix to every cell in the DataFrame
            # verify we are working with strings before applying
            df_fixed = df.applymap(lambda x: fix_arabic(str(x)) if isinstance(x, str) else x)

            # 4. Save results
            json_filename = f"table_{i+1}_page{table.page}_fixed.json"
            csv_filename = f"table_{i+1}_page{table.page}_fixed.csv"
            
            json_path = os.path.join(output_dir, json_filename)
            csv_path = os.path.join(output_dir, csv_filename)
            
            # Save JSON
            df_fixed.to_json(json_path, orient='records', force_ascii=False, indent=4)
            # Save CSV (useful for quick Excel inspection)
            df_fixed.to_csv(csv_path, index=False, encoding='utf-8-sig')

            print(f"Table {i+1} (Page {table.page}) saved to: {output_dir}")

        print(f"\nExtraction complete. Files saved to '{output_dir}/'.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Ensure Ghostscript is installed and added to PATH.")

if __name__ == "__main__":
    if os.path.exists(pdf_path):
        parse_with_camelot()
    else:
        print(f"File not found: {pdf_path}")
