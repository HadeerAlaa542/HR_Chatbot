import ollama
from PIL import Image
import io

# Local model to use (Ensure you ran 'ollama pull llava' or 'ollama pull qwen2.5-vl')
# You can change this to "qwen2.5-vl" if you have it.
OLLAMA_MODEL = "llava"

def is_table_image(image_path):
    """
    Classifies whether the image contains a TABLE or NOT_TABLE using local Ollama.
    """
    try:
        # Ollama takes image paths directly or bytes
        # We can just pass the path string to 'images' list
        
        prompt = """This image is a cropped region from a PDF page.
Your task is to classify whether this image contains a TABLE or NOT_TABLE.

A TABLE means:
- Data arranged in rows and columns
- Headers and cells aligned in a grid-like structure
- Information organized for comparison

NOT a table includes:
- Logos
- Charts or graphs
- Text paragraphs inside a box
- Signatures
- Stamps
- Decorative frames

Answer ONLY with one word:
TABLE
or
NOT_TABLE"""

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path] # Pass direct path
                }
            ]
        )
        
        answer = response['message']['content'].strip().upper()
        
        # Debug print
        # print(f"Classifier Output for {image_path}: {answer}")
        
        if "NOT_TABLE" in answer:
            return False
        elif "TABLE" in answer:
            return True
        else:
            # Fallback for verbose answers
            if "NOT A TABLE" in answer: return False
            if "IS A TABLE" in answer: return True
            return False # Default safe reject? Or accept? Let's reject to be clean.

    except Exception as e:
        print(f"Error classifying with Ollama: {e}")
        # If Ollama isn't running, this will fail.
        # Ensure user knows to run 'ollama serve'
        return False
