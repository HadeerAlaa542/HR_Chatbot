import os
# Fix for "OMP: Error #15: Initializing libiomp5md.dll"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

def parse_with_marker(pdf_path):
    print(f"Processing: {pdf_path}")
    
    # basic check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    print("Loading Marker models (this may download large weights on first run)...")
    try:
        # Load models
        model_dict = create_model_dict(device=device)
        
        # Initialize converter
        print("Initializing PdfConverter...")
        converter = PdfConverter(
            artifact_dict=model_dict,
        )
        
        print("Converting PDF...")
        # The converter directly returns a MarkdownOutput object
        rendered = converter(pdf_path)
        
        # Extract content
        full_text = rendered.markdown
        metadata = rendered.metadata
        
        # Save output
        output_file = pdf_path.replace(".pdf", "_marker.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print(f"\n--- Success! Saved to {output_file} ---")
        print(f"Metadata: {metadata}")
        
        # Preview
        print("\n--- Start of Text ---")
        print(full_text[:500])
        print("\n--- End of Text (Check for Tables) ---")
        print(full_text[-1000:])
        
    except Exception as e:
        print(f"\nError during Marker processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parse_with_marker("sharjah_hr_law 8.pdf")
