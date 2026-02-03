import os
import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image

def extract_tables_from_pdf(pdf_path, output_dir="extracted_table_images"):
    """
    Step 1: Detect and crop tables from PDF pages using PyMuPDF (Fitz) and OpenCV.
    (Switched to Fitz to avoid Poppler dependency issues on Windows)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Opening PDF with Fitz: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    print(f"PDF Opened. Found {len(doc)} pages. Detecting tables...")

    table_images = []

    for i, page in enumerate(doc):
        page_num = i + 1
        
        # Render high-res image (300 DPI equivalent)
        zoom = 2 # 2.0 = 200% resolution (~144 dpi standard, can go higher)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert fitz Pixmap to PIL Image
        img_data = pix.tobytes("ppm")
        pil_image = Image.frombytes("RGB", [pix.width, pix.height], img_data)
        
        # Convert PIL to OpenCV format
        open_cv_image = np.array(pil_image) 
        # Convert RGB to BGR 
        open_cv_image = open_cv_image[:, :, ::-1].copy() 

        # Preprocessing for contour detection
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        
        # Invert to get black text on white
        # Use simple thresholding to isolate lines/text
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Detect horizontal and vertical lines to identify table structure
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        # Morphological operations to detect lines
        detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

        # Combine lines to find grid
        mask = detect_horizontal + detect_vertical

        # Dilate to connect gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=3)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_count = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter valid tables by size (avoid small noise)
            if w > 150 and h > 100: 
                # --- VALIDATION: Intersection Count (The Grid Check) ---
                # A real table must have intersecting horizontal and vertical lines.
                # A frame or photo usually has borders but few internal crossings.
                
                # Extract the intersection points (joints) from the whole page mask
                # using the previously computed line masks
                joints = cv2.bitwise_and(detect_horizontal, detect_vertical)
                
                # Crop joints to the current contour's region
                roi_joints = joints[y:y+h, x:x+w]
                
                # Count the number of intersection points
                # Each "dot" in roi_joints is a crossing.
                # Use countNonZero (pixels) is risky if lines are thick, so let's find contours of joints.
                joint_contours, _ = cv2.findContours(roi_joints, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
                
                num_joints = len(joint_contours)
                
                # Heuristic: A simple 2x2 table has 9 intersections (3 lines x 3 lines).
                # A single box has 4.
                # Let's demand at least 10 intersections to be safe.
                if num_joints < 10:
                    continue

                # Crop
                cropped_table = open_cv_image[y:y+h, x:x+w]
                
                # Save
                table_filename = f"page_{page_num}_table_{table_count + 1}.png"
                table_path = os.path.join(output_dir, table_filename)
                
                # Convert back to PIL to save easily
                pil_image = Image.fromarray(cv2.cvtColor(cropped_table, cv2.COLOR_BGR2RGB))
                pil_image.save(table_path)
                
                table_images.append(table_path)
                table_count += 1
                
        if table_count > 0:
            print(f"Page {page_num}: Found {table_count} candidate table regions.")

    print(f"\nStep 1 Complete. Extracted {len(table_images)} table images to '{output_dir}'.")
    return table_images

if __name__ == "__main__":
    # Test run
    pdf_file = "sharjah_hr_law 8.pdf"
    extract_tables_from_pdf(pdf_file)
