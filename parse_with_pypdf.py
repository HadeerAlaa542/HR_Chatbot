from pypdf import PdfReader
import arabic_reshaper
from bidi.algorithm import get_display

def fix_arabic_text(text):
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

def parse_with_pypdf2(pdf_path="sharjah_hr_law 8.pdf"):
    print(f"Reading {pdf_path} using pypdf...")
    
    reader = PdfReader(pdf_path)
    number_of_pages = len(reader.pages)
    
    full_text = []

    # Let's check Page 95 specifically (index 94) since we know it has a table
    # But for now let's just dump first 5 pages and page 95 to verify quality
    target_pages = [0, 1, 2, 94] 
    
    print(f"Total Pages: {number_of_pages}")
    
    with open("pypdf2_debug_output.txt", "w", encoding="utf-8") as f:
        for i in range(number_of_pages):
            page = reader.pages[i]
            text = page.extract_text()
            
            # Apply Arabic Fix
            # Doing this line-by-line is usually safer than whole-page
            fixed_lines = []
            if text:
                for line in text.split('\n'):
                    fixed_lines.append(fix_arabic_text(line))
            
            fixed_text = "\n".join(fixed_lines)
            
            header = f"\n\n--- Page {i+1} ---\n"
            f.write(header)
            f.write(fixed_text)
            
            # Print to console for pages we care about
            if i in target_pages:
                print(header)
                print(fixed_text[:500] + "..." if len(fixed_text) > 500 else fixed_text)

    print("\nExtraction complete. Saved to 'pypdf2_debug_output.txt'")

if __name__ == "__main__":
    parse_with_pypdf2()
