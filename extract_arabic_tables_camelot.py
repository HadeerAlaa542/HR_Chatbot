import camelot
import pandas as pd
from bidi.algorithm import get_display
import arabic_reshaper
import os

def extract_arabic_tables(pdf_path):
    print(f"Processing {pdf_path}...")
    
    # Extract tables (use 'lattice' for bordered tables, 'stream' for text-based)
    # Adding line_scale=40 helps detect finer lines in some PDFs
    try:
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        print(f"Found {len(tables)} tables.")
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    
    processed_tables = []
    
    output_dir = "extracted_tables_camelot"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for i, table in enumerate(tables):
        df = table.df
        
        # Process Arabic text for RTL
        for col in df.columns:
            df[col] = df[col].apply(lambda x: 
                get_display(arabic_reshaper.reshape(str(x))) if pd.notna(x) else x)
        
        # Reverse column order for RTL layout if needed
        # Standard Arabic tables read Right-to-Left, so Column A is usually on the far right.
        # We reverse it so it matches logical order (Col 1, Col 2...)
        df = df.iloc[:, ::-1]
        
        processed_tables.append(df)
        
        # Save each table
        csv_path = os.path.join(output_dir, f'table_{i+1}_page{table.page}.csv')
        df.to_csv(csv_path, encoding='utf-8-sig', index=False, header=False)
        print(f"Saved {csv_path}")
    
    return processed_tables

# Usage
if __name__ == "__main__":
    pdf_file = "sharjah_hr_law 8.pdf"
    tables = extract_arabic_tables(pdf_file)

    # For RAG: Convert to list of texts
    print("\n--- Generating RAG Chunks ---")
    rag_documents = []
    
    # Save RAG chunks to a file for preview
    with open("rag_table_chunks.txt", "w", encoding="utf-8") as f:
        for i, table in enumerate(tables):
            # Convert table to text chunks with RTL formatting
            text = table.to_string(index=False, header=False)
            rag_documents.append(text)
            
            f.write(f"--- Table {i+1} ---\n")
            f.write(text)
            f.write("\n\n")
            
    print(f"Saved {len(rag_documents)} table text chunks to 'rag_table_chunks.txt'")
