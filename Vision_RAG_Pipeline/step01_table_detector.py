import os
import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image

def detect_and_crop_candidates(pdf_path, output_dir="extracted_candidates"):
    """
    Detects rectangular regions using OpenCV and crops them as candidate images.
    Step 1 of the pipeline (Candidate Proposal).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Opening PDF with Fitz: {pdf_path}")
    candidates = []
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return []
    
    print(f"PDF Opened. Scanning {len(doc)} pages for candidates...")

    candidate_count = 0

    for i, page in enumerate(doc):
        page_num = i + 1
        
        # Render high-res image
        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("ppm")
        pil_image = Image.frombytes("RGB", [pix.width, pix.height], img_data)
        open_cv_image = np.array(pil_image) 
        open_cv_image = open_cv_image[:, :, ::-1].copy() # RGB to BGR

        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Use medium kernels to catch most boxes
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

        mask = detect_horizontal + detect_vertical
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=3)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Simple heuristic filter
            if w > 100 and h > 100:
                # We do NOT run the strict intersection check here anymore, 
                # because we are delegating strictness to the Vision CLASSIFIER (Step 2).
                # We want to catch charts/logos too so the classifier can reject them explicitly?
                # The user said: "The OpenCV... is cropping non-table regions... We must FIX this by adding... classification".
                # So we let OpenCV be a bit looser (candidate generator) and let LLM decide.
                
                # EXTENSION: Capture Context/Caption above table
                # Extend crop upward by 35% of height to catch titles
                pad_top = int(0.35 * h)
                new_y = max(0, y - pad_top)
                
                # Crop from new start Y to original bottom (y+h)
                cropped = open_cv_image[new_y:y+h, x:x+w]
                
                filename = f"p{page_num}_cand_{candidate_count}.png"
                path = os.path.join(output_dir, filename)
                
                # Save
                save_pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
                save_pil.save(path)
                
                candidates.append(path)
                candidate_count += 1
                
    print(f"Detection phase complete. Found {len(candidates)} candidates.")
    return candidates
