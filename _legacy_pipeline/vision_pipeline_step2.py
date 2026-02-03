import os
import base64
import json
import glob
from openai import OpenAI

# Initialize Client (Expects OPENAI_API_KEY in env)
# If not found, user must set it or pass it explicitly
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except:
    print("Warning: OpenAI API Key not found. Set 'OPENAI_API_KEY' environment variable.")
    client = None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_table_image(image_path, output_dir="processed_tables"):
    """
    Step 2: Send table image to Vision LLM for semantic understanding.
    """
    if not client:
        print("Error: OpenAI client not initialized. Cannot call API.")
        return None

    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]
    
    # Create specific folder for this table
    table_dir = os.path.join(output_dir, base_name)
    if not os.path.exists(table_dir):
        os.makedirs(table_dir)
    
    print(f"Analyzing {filename} with GPT-4o...")
    
    base64_image = encode_image(image_path)
    
    prompt = """
    You are an expert document analyst.
    This image contains a complex table from an Arabic PDF document.
    The table may contain merged cells, multi-row headers, nested headers,
    Arabic RTL text, and irregular structure.

    Your job is to understand the table visually like a human would.

    Return a JSON object accurately representing the table structure and content.
    Ensure Arabic text is correctly extracted (Right-To-Left logical order).

    JSON Structure:
    {
      "table_title": "Title if present, else null",
      "table_description": "Explain in natural language what this table represents.",
      "headers_hierarchy": "Describe the header structure (e.g. 'Grade -> Salary -> Basic / Housing')",
      "rows_semantic": [
        {
           "row_id": 1,
           "fields": {"Header Name": "Value", ...},
           "meaning": "Short summary of this row's data"
        }
      ],
      "important_rules": ["List any specific rules or notes found in the table footer or context"],
      "table_summary_for_embedding": "A detailed natural language paragraph summarizing the entire table content, strictly for RAG embedding purposes."
    }
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"}, # Text generation often needs explicit JSON instruction, but Vision supports it differently. 
            # Actually GPT-4o supports json_object mode.
            max_tokens=4096,
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        # Note: If the model puts extra text, we might need to strip it.
        # But json_object mode usually enforces strict JSON.
        # However, our prompt asked for "After the JSON...". 
        # This conflict might break json_object enforcement.
        # BETTER STRATEGY: Ask ONLY for JSON, and include summary INSIDE JSON.
        
        # Let's adjust prompt above conceptually, but here I'll just save raw content if parsing fails.
        save_path = os.path.join(table_dir, "analysis.json")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Saved analysis to {save_path}")
        return content

    except Exception as e:
        print(f"Error calling GPT-4o: {e}")
        return None

def process_all_tables(input_dir="extracted_table_images"):
    images = glob.glob(os.path.join(input_dir, "*.png"))
    print(f"Found {len(images)} table images to process.")
    
    # Sort them to keep order
    # Extract page number for sorting
    # Filename format: page_X_table_Y.png
    images.sort(key=lambda x: int(os.path.basename(x).split('_')[1]))

    for img in images:
        analyze_table_image(img)

if __name__ == "__main__":
    # Ensure this runs only if user set the key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set your OpenAI API Key first!")
        # For testing purposes, we can't run this without a key.
    else:
        process_all_tables()
