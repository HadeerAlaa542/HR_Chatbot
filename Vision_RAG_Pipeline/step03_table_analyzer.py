import os
import json
import shutil
import ollama

# Local model
OLLAMA_MODEL = "llava"

def analyze_table_semantic(image_path, output_dir="final_tables_rag"):
    """
    Step 3: Deep understanding of a VALID table using Local Vision LLM (Ollama).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]
    
    # Table folder
    safe_name = base_name.replace("cand_", "tbl_")
    table_folder = os.path.join(output_dir, safe_name)
    if not os.path.exists(table_folder):
        os.makedirs(table_folder)
        
    print(f"Analyzing validated table: {filename} using {OLLAMA_MODEL}...")
    
    # LLaVA isn't great at strict JSON. We will ask for a structured text response 
    # and try to extract JSON, or just save the raw text if JSON fails.
    
    prompt = """You are a Senior Data Engineer specializing in digitizing documents.
This image contains a complex table from an HR Law document.

Your task is to CANONICALIZE this table into a semantic structure.

RULES for Canonicalization:
1. Denormalize Merged Cells: If a cell spans multiple rows (visually merged), explicitly repeat the value for EVERY row. Do not use nulls or "ditto".
2. Semantic Headers: If headers are generic (e.g. "Col 1"), infer the true meaning (e.g. "Years of Service") based on context.
3. Flattening: Flatten nested headers (e.g. "Salary" -> "Basic" becomes "Salary_Basic").
4. Visual Context: If color or indentation implies a category, create an explicit 'category' field.

Output a valid JSON object with:
{
  "table_title": "Precise Title",
  "canonical_data": [
      { "header_1": "value", "header_2": "value", "category": "derived_value" },
      ...
  ],
  "rag_summary": "A verbose, natural language paragraph explaining every rule and data point in this table for vector embedding. This is the most important field."
}

Ensure the output is ONLY valid JSON. Do not add markdown blocks like ```json.
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }
            ],
            options={'temperature': 0.1} # Low temp for valid JSON
        )
        
        content = response['message']['content']
        
        # Save results
        json_path = os.path.join(table_folder, "table.json")
        img_dest_path = os.path.join(table_folder, "image.png")
        
        # Clean markdown if present
        cleaned_content = content.replace("```json", "").replace("```", "").strip()
        
        # Try to parse JSON to valid correctness
        try:
            data = json.loads(cleaned_content)
            # Re-dump to ensure it's pretty
            final_json = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Extract summary
            explanation = data.get("rag_summary", data.get("table_summary_for_embedding", ""))
            
        except json.JSONDecodeError:
            print(f"Warning: {OLLAMA_MODEL} did not return valid JSON. Saving raw text.")
            final_json = content # Save raw output so we don't lose it
            explanation = content # Use full content as explanation for RAG

        # Save JSON/Text
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(final_json)
            
        # Save Explanation
        with open(os.path.join(table_folder, "explanation.txt"), "w", encoding="utf-8") as f:
            f.write(explanation)

        # Copy Image
        shutil.copy(image_path, img_dest_path)
            
        return content

    except Exception as e:
        print(f"Error analyzing table {filename}: {e}")
        return None
