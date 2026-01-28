import os
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.node_parser import MarkdownElementNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.storage import StorageContext
import qdrant_client

import os
import re
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.storage import StorageContext
import qdrant_client

def extract_tables(text):
    """
    Extracts markdown tables from text.
    Returns a list of table strings and the text with placeholders.
    """
    # Regex for markdown tables (lines starting with |)
    # This is a simplified regex, but works for most standard markdown tables
    table_pattern = r'(\n\|.*?\|\n(?:\|[-:| ]+\|\n)+(?:\|.*?\|\n)+)'
    
    tables = []
    def replace_func(match):
        tables.append(match.group(1))
        return f"\n[TABLE_PLACEHOLDER_{len(tables)-1}]\n"
        
    text_without_tables = re.sub(table_pattern, replace_func, text, flags=re.DOTALL)
    return tables, text_without_tables

def run_pipeline():
    # 1. Setup Encoding (BGE-M3)
    print("Initializing BGE-M3 Embedding Model...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")
    Settings.embed_model = embed_model
    Settings.llm = None

    # 2. Load the Marker Markdown File
    md_file_path = "sharjah_hr_law 8_marker.md"
    print(f"Loading {md_file_path}...")
    
    with open(md_file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 3. Custom robust chunking
    print("Chunking document...")
    
    # First, separate tables to keep them intact
    tables, content_minus_tables = extract_tables(md_content)
    print(f"Found {len(tables)} tables.")

    # Split remaining text by Headers (#, ##, ###)
    # This regex looks for lines starting with # followed by space
    header_pattern = r'(^|\n)(#{1,3}\s.*)'
    parts = re.split(header_pattern, content_minus_tables)
    
    nodes = []
    
    # Process text sections
    current_chunk = ""
    for part in parts:
        if part.strip():
            # If it's a header, start a new chunk? 
            # Actually, standard approach is Header + Content.
            # Simple heuristic: if part starts with #, it's a header line.
            if re.match(r'^\s*#', part):
                if current_chunk:
                    nodes.append(TextNode(text=current_chunk.strip()))
                current_chunk = part # Start new chunk with header
            else:
                current_chunk += "\n" + part
                
    if current_chunk:
        nodes.append(TextNode(text=current_chunk.strip()))

    # Add Table Nodes (High Priority)
    for i, table_text in enumerate(tables):
        # We create a node specifically for the table.
        # Adding some context "Table" helps retrieval
        node = TextNode(text=f"Table {i+1}:\n{table_text}")
        node.metadata = {"type": "table", "original_index": i}
        nodes.append(node)

    print(f"Total Text Chunks (Sections): {len(nodes) - len(tables)}")
    print(f"Total Table Chunks: {len(tables)}")

    # 4. Setup Qdrant Vector DB (Local)
    print("Initializing Qdrant Database (Local)...")
    client = qdrant_client.QdrantClient(path="./qdrant_db")
    vector_store = QdrantVectorStore(client=client, collection_name="hr_law_collection")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 5. Index and Persist
    print("Generating Embeddings & Indexing...")
    # This step triggers the heavy lifting: running text through BGE-M3
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
    )

    print("--- Indexing Complete! ---")
    print("Data saved to ./qdrant_db")


if __name__ == "__main__":
    # Ensure you have installed: pip install llama-index llama-index-embeddings-huggingface llama-index-vector-stores-qdrant qdrant-client
    run_pipeline()
