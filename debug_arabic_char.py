import pdfplumber
import pandas as pd

def debug_page_100():
    pdf_path = "sharjah_hr_law 8.pdf"
    target_page = 100 # Page 100 (1-based index)
    
    print(f"Inspecting Page {target_page} Raw Output...")
    
    with pdfplumber.open(pdf_path) as pdf:
        # pdfplumber pages are 0-indexed, so Page 100 is index 99
        page = pdf.pages[target_page - 1] 
        tables = page.extract_tables()
        
        # Test different x_tolerance settings to force space detection
        tolerances = [3, 5, 10]
        
        for tol in tolerances:
            print(f"\n--- Testing x_tolerance = {tol} ---")
            # Extract with custom settings
            tables = page.extract_tables(table_settings={"x_tolerance": tol})
            
            if len(tables) >= 2:
                table = tables[1]
                for row in table:
                    for cell in row:
                        if cell and "رابع" in cell:
                             print(f"Cell Content: '{cell}'")

if __name__ == "__main__":
    debug_page_100()
