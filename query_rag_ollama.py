import qdrant_client
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.ollama import Ollama

def query_rag_with_ollama():
    # 1. Setup Encoding (BGE-M3)
    print("Initializing BGE-M3 Embedding Model...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3", device="cpu") # Force CPU to avoid VRAM conflicts if small GPU
    Settings.embed_model = embed_model
    
    # 2. Setup Ollama (The Brain)
    # User confirmed model: qwen3:8b
    model_name = "qwen3:8b" 
    print(f"Initializing Ollama ({model_name})...")
    llm = Ollama(model=model_name, request_timeout=360.0)
    Settings.llm = llm

    # 3. Connect to Local Qdrant
    print("Connecting to Database...")
    client = qdrant_client.QdrantClient(path="./qdrant_db")
    vector_store = QdrantVectorStore(client=client, collection_name="hr_law_collection")
    
    # 4. Load Index & Create Query Engine
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    
    # Create the engine
    # similarity_top_k=5: Gives the LLM 5 pieces of evidence (tables/articles) to read before answering
    query_engine = index.as_query_engine(similarity_top_k=5)
    
    print("\n" + "="*50)
    print(f"RAG System Ready! (Using {model_name})")
    print("Ask about HR laws, benefits tables, grades, etc.")
    print("="*50)

    while True:
        query_text = input("\nQuestion [q to quit]: ")
        if query_text.lower() == 'q':
            break
            
        print("Thinking...")
        response = query_engine.query(query_text)
        
        print("\n--- Answer ---")
        print(response)
        
        # Verify Sources (Optional - good for debugging)
        # print("\n(Sources used:)")
        # for node in response.source_nodes:
        #     print(f"- Score {node.score:.2f}: {node.node.get_content()[:50]}...")

if __name__ == "__main__":
    query_rag_with_ollama()
