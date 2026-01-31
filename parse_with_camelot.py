import camelot
import os

# Configuration
pdf_path = "sharjah_hr_law 8.pdf"
output_dir = "camelot_tables"

def parse_with_camelot():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Extracting tables from '{pdf_path}' using Camelot...")
    print("Note: This process requires Ghostscript to be installed on your system.")

    try:
        # 1. Try 'Lattice' mode first (best for tables with clear grid lines)
        print("Attempting extraction with flavor='lattice'...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        print(f"Found {len(tables)} tables with lattice flavor.")

        # 2. If 'Lattice' misses things, usually you'd try 'Stream' (for whitespace tables)
        # For now, we stick to lattice as it's cleaner for official docs usually, 
        # but you can uncomment the below to fallback:
        # if len(tables) == 0:
        #     print("Trying 'stream' flavor...")
        #     tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

        # 3. Save results
        json_results = []
        
        for i, table in enumerate(tables):
            # Generate filenames
            json_filename = f"table_{i+1}_page{table.page}.json"
            json_path = os.path.join(output_dir, json_filename)
            
            # Save to JSON (orient='records' is usually best for readability)
            # You can also use orient='split' or 'index' depending on your preference
            table.df.to_json(json_path, orient='records', force_ascii=False, indent=4)
            
            # Also collect in a list if we want one big json later
            json_results.append({
                "table_id": i+1,
                "page": table.page,
                "data": table.df.to_dict(orient='records')
            })

            # Print a preview to console
            print(f"\n--- Table {i+1} (Page {table.page}) ---")
            print(f"Accuracy: {table.accuracy}%")
            print(f"Saved to: {json_path}")

        print(f"\nExtraction complete. {len(tables)} JSON files saved to '{output_dir}/'.")
        
    except ImportError as e:
        print("\nERROR: Missing dependencies.")
        print("Please run: pip install camelot-py opencv-python ghostscript")
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Common fix: Install Ghostscript (https://ghostscript.com/releases/gsdnld.html) and add to PATH.")

if __name__ == "__main__":
    if os.path.exists(pdf_path):
        parse_with_camelot()
    else:
        print(f"File not found: {pdf_path}")
