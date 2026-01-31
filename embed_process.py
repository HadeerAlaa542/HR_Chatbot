from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.storage import StorageContext
import qdrant_client
from chunk_process import load_and_chunk

def run_embedding():
    # 1. Get Nodes from the chunking module
    # This calls the function solely dedicated to preparing the data
    nodes = load_and_chunk("sharjah_hr_law 8_marker.md")

    # 2. Setup Encoding (BGE-M3)
    print("Initializing BGE-M3 Embedding Model...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3")
    Settings.embed_model = embed_model
    Settings.llm = None

    # 3. Setup Qdrant Vector DB (Local)
    print("Initializing Qdrant Database (Local)...")
    client = qdrant_client.QdrantClient(path="./qdrant_db")
    vector_store = QdrantVectorStore(client=client, collection_name="hr_law_collection")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 4. Index and Persist
    print("Generating Embeddings & Indexing...")
    # This step triggers the heavy lifting: running text through BGE-M3
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
    )

    print("--- Indexing Complete! ---")
    print("Data saved to ./qdrant_db")

if __name__ == "__main__":
    run_embedding()
