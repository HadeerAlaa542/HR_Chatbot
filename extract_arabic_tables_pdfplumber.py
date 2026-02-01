import pdfplumber
import pandas as pd
from bidi.algorithm import get_display
import arabic_reshaper
import os

def extract_tables_pdfplumber(pdf_path):
    print(f"Processing {pdf_path} (First 10 pages for debugging)...")
    
    output_dir = "debug_tables"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with pdfplumber.open(pdf_path) as pdf:
        # Check pages 90-95 where we know tables exist
        for i, page in enumerate(pdf.pages[90:95]): 
            # Adjust index for printing (pages are 0-indexed in list, but 1-indexed for humans)
            effective_page_num = 90 + i + 1 
            page_tables = page.extract_tables()
            
            if not page_tables:
                continue
                
            print(f"Found {len(page_tables)} tables on page {effective_page_num}")
            
            for j, table_data in enumerate(page_tables):
                cleaned_data = [[cell if cell is not None else "" for cell in row] for row in table_data]
                
                # --- Method A: Standard (Reshape + Bidi) ---
                df_A = pd.DataFrame(cleaned_data)
                for col in df_A.columns:
                    df_A[col] = df_A[col].apply(lambda x: get_display(arabic_reshaper.reshape(str(x))) if x else "")
                df_A = df_A.iloc[:, ::-1] # Reverse columns
                df_A.to_csv(os.path.join(output_dir, f"table_p{effective_page_num}_{j+1}_MethodA.csv"), index=False, header=False, encoding='utf-8-sig')

                # --- Method B: Reshape Only (No Bidi Reordering) ---
                df_B = pd.DataFrame(cleaned_data)
                for col in df_B.columns:
                    df_B[col] = df_B[col].apply(lambda x: arabic_reshaper.reshape(str(x)) if x else "")
                df_B = df_B.iloc[:, ::-1]
                df_B.to_csv(os.path.join(output_dir, f"table_p{effective_page_num}_{j+1}_MethodB.csv"), index=False, header=False, encoding='utf-8-sig')

                # --- Method C: Bidi Only (No Reshaping) ---
                df_C = pd.DataFrame(cleaned_data)
                for col in df_C.columns:
                    df_C[col] = df_C[col].apply(lambda x: get_display(str(x)) if x else "")
                df_C = df_C.iloc[:, ::-1]
                df_C.to_csv(os.path.join(output_dir, f"table_p{effective_page_num}_{j+1}_MethodC.csv"), index=False, header=False, encoding='utf-8-sig')

                # --- Method D: Raw (No processing) ---
                df_D = pd.DataFrame(cleaned_data)
                df_D = df_D.iloc[:, ::-1]
                df_D.to_csv(os.path.join(output_dir, f"table_p{effective_page_num}_{j+1}_MethodD.csv"), index=False, header=False, encoding='utf-8-sig')

    print(f"Debug variations saved to '{output_dir}/'. Please check which Method (A, B, C, or D) looks correct.")

if __name__ == "__main__":
    extract_tables_pdfplumber("sharjah_hr_law 8.pdf")
