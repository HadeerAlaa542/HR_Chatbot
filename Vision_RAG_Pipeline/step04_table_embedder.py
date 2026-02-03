import os
import glob
import json
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

QDRANT_PATH = "./qdrant_vision_db"
COLLECTION_NAME = "vision_tables"

def embed_tables_for_rag(tables_dir="final_tables_rag"):
    """
    Step 4/5: Embed the natural language explanations into Qdrant.
    """
    print(f"\n[Step 4] Embedding Tables from {tables_dir}...")
    
    # 1. Setup Qdrant
    client = QdrantClient(path=QDRANT_PATH)
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
        )

    # 2. Load Model
    print("Loading Embedding Model (BGE-M3)...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")

    # 3. Scan for processed tables
    # Structure: tables_dir/tbl_page_X_.../explanation.txt
    table_folders = glob.glob(os.path.join(tables_dir, "*"))
    
    points = []
    
    for i, folder in enumerate(table_folders):
        # json_path = os.path.join(folder, "table.json") # Unused: We rely on the Canonicalized Summary text only
        txt_path = os.path.join(folder, "explanation.txt")
        image_path = os.path.join(folder, "image.png") # If we decided to copy/move it here
        
        # If image wasn't copied to folder, we might need to find original?
        # My analyzer script didn't move the image. It kept it in 'candidates_temp'? 
        # Actually my analyzer saved 'image.png' (implied copy? No, I wrote logic comments but didn't actually shutil copy).
        # Let's assume analyzer saves `explanation.txt`.
        
        if not os.path.exists(txt_path):
            continue
            
        with open(txt_path, "r", encoding="utf-8") as f:
            summary = f.read()

        vector = embed_model.get_text_embedding(summary)
        
        # Original Image Path logic is tricky if we deleted candidates.
        # But 'valid_tables' in pipeline exists.
        # For a robust system, analyzer SHOULD copy the image to the final folder.
        
        points.append(models.PointStruct(
            id=i,
            vector=vector,
            payload={
                "summary": summary,
                "folder": folder,
                "type": "table_rag"
            }
        ))
        
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"Indexed {len(points)} tables.")
    else:
        print("No tables found to index.")
