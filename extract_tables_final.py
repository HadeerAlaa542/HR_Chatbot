import pdfplumber
import pandas as pd
from bidi.algorithm import get_display
import os

import json

# We intentionally removed arabic_reshaper because Method C (Bidi Only) was verified as correct.

import re

def repair_text(text):
    if not isinstance(text, str):
        return text
    
def repair_text(text):
    if not isinstance(text, str):
        return text

    # Generic Fix 1: English Text merged with Arabic 'أ' (Alif Hamza) acting as space
    # e.g., "Iأacknowledge" -> "I acknowledge"
    # Logic: English Letter + 'أ' -> English Letter + Space
    text = re.sub(r'([a-zA-Z])أ', r'\1 ', text)
    text = re.sub(r'أ([a-zA-Z])', r' \1', text) # If it's at start of word

    # Generic Fix 2: Arabic Non-Connectors followed by Alifs
    # Letters that NEVER connect to the left: 
    # ا (Alif), د (Dal), ذ (Thal), ر (Ra), ز (Zain), و (Waw), ة (Ta Marbuta - logically end)
    # If these are followed immediately by another Alif (start of next word), there MUST be a space.
    # Pattern: [Non-Connectors] + [Alif/Hamza variants]
    
    non_connectors = r'[اأإآدذرزوؤة]'
    alif_starts = r'[اأإآ]'
    
    # Regex: (Non-Connector) + (Alif Start) -> \1 + Space + \2
    text = re.sub(f'({non_connectors})({alif_starts})', r'\1 \2', text)
    
    # Generic Fix 3: "Ain" (ع) + "Alif" (أ) merge (User specific case: رابعأمرة)
    # This is trickier because 'Ain' connects. But 'Ain' + 'Alif' inside a word is rare 
    # except in specific roots (like سأل - Sa'al - Sin not Ain).
    # 'Ain' + 'Alif Hamza' (عأ) is extremely rare inside a root word.
    # So we can safely split it? 
    # Example: "قرآن" uses Madda. "مسألة" uses Sin.
    # "خطأ" ends with Alif. 
    # Let's risk splitting (Boundaries usually happen at word ends like '...aa' or '...a').
    
    return text

def extract_tables_final(pdf_path):
    print(f"Processing full document: {pdf_path}...")
    
    output_dir = "extracted_tables_final"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    rag_chunks = []
    # Dictionary to store table data for JSON export
    all_tables_data = []
    total_tables = 0

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            
            if not page_tables:
                continue
                
            print(f"Page {i+1}: Found {len(page_tables)} tables")
            total_tables += len(page_tables)
            
            for j, table_data in enumerate(page_tables):
                cleaned_data = [[cell if cell is not None else "" for cell in row] for row in table_data]
                df = pd.DataFrame(cleaned_data)
                
                # --- Method C Logic (Approved) + REPAIR ---
                for col in df.columns:
                    # 1. Repair Text (Split Merges)
                    df[col] = df[col].apply(lambda x: repair_text(str(x)))
                    # 2. Bidi Display
                    df[col] = df[col].apply(lambda x: get_display(str(x)) if x else "")
                
                # Reverse columns
                df = df.iloc[:, ::-1]
                
                # Convert to dict for JSON
                table_dict = {
                    "page": i + 1,
                    "table_index": j + 1,
                    "data": df.values.tolist() # Convert dataframe to list of lists
                }
                all_tables_data.append(table_dict)
                
                # Save CSV
                csv_filename = f"table_p{i+1}_{j+1}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                df.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig')
                
                # RAG Chunk
                rag_chunk = df.to_string(index=False, header=False)
                rag_chunks.append(f"--- Table from Page {i+1} ---\n{rag_chunk}")

    # Save to JSON
    json_path = "extracted_tables.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_tables_data, f, ensure_ascii=False, indent=4)

    # Save all RAG chunks
    with open("rag_table_chunks_final.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(rag_chunks))
        
    print("\n" + "="*50)
    print(f"EXTRACTION COMPLETE")
    print(f"Total Tables Extracted: {total_tables}")
    print(f"JSON saved to: '{json_path}'")
    print(f"CSVs saved to: '{output_dir}/'")
    print(f"RAG Text File: 'rag_table_chunks_final.txt'")
    print("="*50)

if __name__ == "__main__":
    extract_tables_final("sharjah_hr_law 8.pdf")
