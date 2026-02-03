import pdfplumber
from bidi.algorithm import get_display
import re
import os

def repair_text(text):
    if not text: return ""
    # Generic Fix 1: English Text merged with Arabic 'أ' (Alif Hamza) acting as space
    # e.g., "Iأacknowledge" -> "I acknowledge"
    text = re.sub(r'([a-zA-Z])أ', r'\1 ', text)
    text = re.sub(r'أ([a-zA-Z])', r' \1', text)

    # Generic Fix 2: Arabic Non-Connectors followed by Alifs
    # Letters that CANNOT connect left: ا, د, ذ, ر, ز, و, ة, ؤ
    # If followed by Alif (start of new word), split them.
    text = re.sub(r'([اأإآدذرزوؤة])([اأإآ])', r'\1 \2', text)
    
    # Generic Fix 3: Ain/Ghain (ع/غ) followed by Alif Hamza (أ)
    # This addresses "رابعأمرة". While technically they can connect, 
    # 'Ain' followed immediately by 'Alif Hamza' is extremely rare inside a root word.
    text = re.sub(r'([عغ])(أ)', r'\1 \2', text)

    # Fix Brackets for RTL display
    # Swap ( and ) because of Bidi mirroring issues
    text = text.replace('(', 'TEMPOPEN').replace(')', '(').replace('TEMPOPEN', ')')
    
    return text

def extract_text_excluding_tables(pdf_path):
    print(f"Processing text from {pdf_path} (Excluding Tables)...")
    
    rag_text_chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # 1. Find Tables
            tables = page.find_tables()
            
            # 2. Define a filter to ignore text inside tables
            def not_inside_tables(obj):
                # Check if object (char) is inside any detected table bbox
                obj_x = (obj['x0'] + obj['x1']) / 2
                obj_y = (obj['top'] + obj['bottom']) / 2
                
                for table in tables:
                    tx, ty, bx, by = table.bbox
                    if tx <= obj_x <= bx and ty <= obj_y <= by:
                        return False # It IS inside a table, so filter it OUT
                return True

            # 3. Create a filtered version of the page (Text Only)
            if tables:
                clean_page = page.filter(not_inside_tables)
            else:
                clean_page = page
            
            # 4. Extract Text
            content = clean_page.extract_text()
            
            if not content:
                continue
                
            # 5. Fix Arabic/English
            cleaned_lines = []
            for line in content.split('\n'):
                line = repair_text(line)
                
                # Apply Bidi ONLY if line has Arabic
                if re.search(r'[\u0600-\u06FF]', line):
                    line = get_display(line)
                
                cleaned_lines.append(line)
            
            final_text = "\n".join(cleaned_lines)
            
            # Add to list
            chunk = f"--- Page {i+1} Text ---\n{final_text}\n"
            rag_text_chunks.append(chunk)

    # Save Results
    output_file = "rag_text_only.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(rag_text_chunks))
        
    print(f"\nExtraction Complete.")
    print(f"Text (without tables) saved to: '{output_file}'")

if __name__ == "__main__":
    extract_text_excluding_tables("sharjah_hr_law 8.pdf")
