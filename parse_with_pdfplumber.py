import pdfplumber
import json
import os
import arabic_reshaper
from bidi.algorithm import get_display

# Configuration
pdf_path = "sharjah_hr_law 8.pdf"
output_dir = "pdfplumber_tables"

def fix_arabic_text(text):
    # Returning raw text to debug format issues
    if not text:
        return ""
    return text.strip()

def parse_with_pdfplumber():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Extracting tables from '{pdf_path}' using pdfplumber...")
    
    extracted_tables_count = 0


    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):


            # --- 2. Extract Tables ---
            # check for tables on this page
            tables = page.extract_tables()
            
            for j, table in enumerate(tables):
                # 'table' is a list of lists (rows of columns)
                # We need to clean the cells inside the table
                cleaned_table = []
                for row in table:
                    cleaned_row = []
                    for cell in row:
                        # Clean None values and fix Arabic
                        cell_str = cell if cell is not None else ""
                        cleaned_row.append(fix_arabic_text(cell_str))
                    cleaned_table.append(cleaned_row)

                # Convert List of Lists -> List of Dicts (Record Format)
                if cleaned_table:
                    headers = cleaned_table[0]
                    # Handle empty headers
                    final_headers = []
                    for k, h in enumerate(headers):
                        if h.strip():
                            final_headers.append(h_strip := h.strip())
                        else:
                            final_headers.append(f"Column_{k+1}")
                    
                    records = []
                    # Start from row 1 (skipping headers)
                    for row in cleaned_table[1:]:
                        # Ensure row matches header length (pad with empty strings if needed)
                        if len(row) < len(final_headers):
                            row += [""] * (len(final_headers) - len(row))
                        
                        record = {}
                        for k, header in enumerate(final_headers):
                            # Safety check for row length
                            if k < len(row):
                                record[header] = row[k]
                            else:
                                record[header] = ""
                        records.append(record)
                else:
                    records = []

                # Save to JSON (List of Records)
                json_filename = f"table_p{i+1}_{j+1}.json"
                json_path = os.path.join(output_dir, json_filename)
                
                with open(json_path, "w", encoding="utf-8") as f:
                    # Save straight list of records, matching Camelot's output style
                    json.dump(records, f, ensure_ascii=False, indent=4)
                
                print(f"Saved Table {j+1} on Page {i+1} to {json_filename}")
                extracted_tables_count += 1

    print(f"\nExtraction complete.")
    print(f"Total Tables Found: {extracted_tables_count}")

if __name__ == "__main__":
    if os.path.exists(pdf_path):
        parse_with_pdfplumber()
    else:
        print(f"File not found: {pdf_path}")
