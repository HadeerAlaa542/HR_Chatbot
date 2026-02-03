import os
import json
import glob
from vision_pipeline_step1 import extract_tables_from_pdf
from vision_pipeline_step2 import analyze_table_image
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Initialize Qdrant
QDRANT_PATH = "./qdrant_vision_db"
COLLECTION_NAME = "vision_tables"

def setup_qdrant():
    client = QdrantClient(path=QDRANT_PATH)
    # Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    
    if not exists:
        print(f"Creating Qdrant collection: {COLLECTION_NAME}")
        # BGE-M3 dimension is 1024
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
        )
    return client

def process_pdf_for_table_rag(pdf_path):
    print("=== Starting Vision-First Table RAG Pipeline ===")
    
    # 1. Extract Images
    image_dir = "extracted_table_images"
    images = extract_tables_from_pdf(pdf_path, output_dir=image_dir)
    
    if not images:
        print("No tables found or extraction failed.")
        return

    # 2. Analyze with Vision LLM
    processed_dir = "processed_tables"
    
    # Check for API Key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nCRITICAL: OPENAI_API_KEY is missing!")
        print("Steps 2 (Analysis) and 4 (Embedding) cannot proceed without the LLM output.")
        print("Please set the environment variable and re-run.")
        return

    print("\n=== Step 2: Vision Analysis (GPT-4o) ===")
    json_results = []
    
    for img_path in images:
        # Check if already processed to save money/time
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        json_path = os.path.join(processed_dir, base_name, "analysis.json")
        
        if os.path.exists(json_path):
            print(f"Skipping {base_name} (Already processed)")
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = analyze_table_image(img_path, output_dir=processed_dir)
        
        if content:
            try:
                data = json.loads(content)
                data['image_path'] = img_path
                data['json_path'] = json_path
                json_results.append(data)
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {base_name}")

    # 3 & 4. Embed and Store
    if not json_results:
        print("No analysis results to embed.")
        return

    print("\n=== Step 3 & 4: Embedding & Storage ===")
    client = setup_qdrant()
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

    points = []
    for i, item in enumerate(json_results):
        summary = item.get("table_summary_for_embedding", "")
        if not summary:
            continue
            
        print(f"Embedding table {i+1}/{len(json_results)}...")
        vector = embed_model.get_text_embedding(summary)
        
        # Prepare Payload
        payload = {
            "type": "table_vision",
            "image_path": item['image_path'],
            "json_path": item['json_path'],
            "summary": summary,
            "title": item.get("table_title", "Untitled Table"),
            # Store full logical JSON as string for retrieval if needed
            "full_json_str": json.dumps(item, ensure_ascii=False)
        }
        
        points.append(models.PointStruct(
            id=i, # Use simple integer ID or UUID
            vector=vector,
            payload=payload
        ))

    # Upload to Qdrant
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"Successfully indexed {len(points)} tables into Qdrant.")
    else:
        print("No valid points created.")

if __name__ == "__main__":
    process_pdf_for_table_rag("sharjah_hr_law 8.pdf")
