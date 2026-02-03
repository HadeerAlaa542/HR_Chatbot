import os
import shutil
from dotenv import load_dotenv

# Load env immediately
load_dotenv()

from step01_table_detector import detect_and_crop_candidates
from step02_table_classifier import is_table_image
from step03_table_analyzer import analyze_table_semantic

from step04_table_embedder import embed_tables_for_rag

def process_pdf_for_table_rag(pdf_path):
    print("="*50)
    print("STARTING VISION-FIRST TABLE RAG PIPELINE (Refined)")
    print("="*50)
    
    # API Key check removed (Using Local Ollama)
    print("Using Local Vision Model (Ollama)")

    # 1. Detect Rectangles (Broad candidates)
    print("\n[Step 1] Detecting Candidates (OpenCV)...")
    candidate_dir = "candidates_temp"
    candidates = detect_and_crop_candidates(pdf_path, output_dir=candidate_dir)
    
    if not candidates:
        print("No candidates found.")
        return

    print(f"\n[Step 2] Classifying Candidates ({len(candidates)} items)...")
    
    valid_tables = []
    discarded_count = 0
    
    for img_path in candidates:
        # 2. Classify (Vision LLM)
        is_table = is_table_image(img_path)
        
        if is_table:
            print(f"  [ACCEPTED] {os.path.basename(img_path)}")
            valid_tables.append(img_path)
        else:
            print(f"  [DISCARDED] {os.path.basename(img_path)}")
            discarded_count += 1
            try:
                os.remove(img_path)
            except: 
                pass

    print(f"\nClassification Complete.")
    print(f"Accepted: {len(valid_tables)}")
    print(f"Discarded: {discarded_count}")

    # 3. Analyze Valid Tables
    print(f"\n[Step 3] Semantic Analysis ({len(valid_tables)} tables)...")
    
    rag_dir = "final_tables_rag"
    for img_path in valid_tables:
        analyze_table_semantic(img_path, output_dir=rag_dir)
        
    # 4. Embed
    embed_tables_for_rag(tables_dir=rag_dir)
        
    print("\n" + "="*50)
    print("PIPELINE COMPLETE")
    print(f"Check '{rag_dir}/' for results and Qdrant DB.")
    print("="*50)

if __name__ == "__main__":
    # Default to PDF in parent folder if running from subfolder
    pdf_file = os.path.join("..", "sharjah_hr_law 8.pdf")
    if not os.path.exists(pdf_file):
        # Fallback if running from root
        pdf_file = "sharjah_hr_law 8.pdf"
        
    process_pdf_for_table_rag(pdf_file)
