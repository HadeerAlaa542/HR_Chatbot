import re
import os
from llama_index.core.schema import TextNode

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

def load_and_chunk(md_file_path="sharjah_hr_law 8_marker.md"):
    print(f"Loading {md_file_path}...")
    
    if not os.path.exists(md_file_path):
        raise FileNotFoundError(f"File not found: {md_file_path}")

    with open(md_file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Custom robust chunking
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

    # DEBUG: Save chunks to file for inspection
    print("Saving chunks to 'chunks_debug.txt' and printing to console...")
    with open("chunks_debug.txt", "w", encoding="utf-8") as f:
        for i, node in enumerate(nodes):
            header = f"--- CHUNK {i+1} ({node.metadata.get('type', 'text')}) ---"
            content = node.text
            divider = "="*50
            
            # Write key information to file
            f.write(f"{header}\n{content}\n\n{divider}\n\n")
            
            # Print to console for immediate feedback
            print(header)
            # print(content) # Optional: Commented out to avoid cluttering console during import, uncomment if needed
            # print(f"\n{divider}\n")
            
    print(f"Chunking complete. Created {len(nodes)} nodes.")
    return nodes

if __name__ == "__main__":
    # Test the chunking independently
    load_and_chunk()
