# Technical Specification: Hybrid Table Extraction & Vision RAG Pipeline

**Project**: HR Chatbot Data Ingestion System  
**Document Branch**: `main-architecture/v2`  
**Date**: February 03, 2026  
**Audience**: Technical Lead / Systems Architect  
**Scope**: Ingestion, Transformation, and Vectorization of Tabular Data from Bilingual HR Laws.

---

## 1. Executive Summary & Problem Scope

This document defines the architecture specifically engineered to handle the complexities of the Sharjah HR Law PDF documents. These documents present a tri-fold challenge:
1.  **Bilingual Complexity**: Text is mixed left-to-right (English) and right-to-left (Arabic), notoriously breaking standard OCR extraction layers.
2.  **Structural Integrity**: Tables often contain merged cells, vertically spanning headers ("rowspans"), and implied values (e.g., "Ditto" marks) that standard grid parsers treat as empty nulls.
3.  **Visual Semantics**: Crucial logic is often conveyed visually—through bold text, indentation levels, or color-coded rows—which is invisible to pure text-extraction tools.

To solve this, we deploy a **Hybrid Vision-Text Pipeline**. It does not rely on a single algorithm but splits the workload: a **Deterministic Stream** for clean, programmatic extraction, and a **Probabilistic Vision Stream** for semantic interpretation of complex visual structures.

---

## 2. High-Level Architecture Diagram (Text vs. Vision)

The system is designed as two parallel processing manufacturing lines that feed into a single Vector Storage.

```mermaid
graph TD
    A[Raw PDF Document] --> B{Router Logic}
    B -->|Path 1: Standard Tables| C[Stream A: Text Extraction]
    B -->|Path 2: Complex Tables| D[Stream B: Vision Pipeline]
    
    subgraph "Stream A (Deterministic)"
    C --> C1[PDFPlumber Grid Analysis]
    C1 --> C2[Arabic Text Repair Middleware]
    C2 --> C3[DataFrame Construction]
    end
    
    subgraph "Stream B (Probabilistic)"
    D --> D1[OpenCV Contour Detection]
    D1 --> D2[LLM Classification (Is This A Table?)]
    D2 --> D3[VLM Semantic Interpretation]
    end
    
    C3 --> E[Canonicalization Layer]
    D3 --> E
    
    E -->|Structured Semantic Text| F[Embedding Model]
    F --> G[(Qdrant Vector DB)]
```

---

## 3. Stream A: Text-Based Extraction (The "Fast Path")

**Objective**: Extract data where the PDF text layer is intact. This is faster and cheaper than vision tokens but prone to encoding errors. we mitigate these errors with a custom logic layer.

### 3.1 The Arabic Text Repair Middleware
The extraction script `extract_tables_final.py` does not trust the raw PDF stream. It passes all text through a repair function (`repair_text`) before it hits the DataFrame.

#### Problem 1: The "Alif" Merge Issue
*   **The Glitch**: The PDF font encoding often treats the Arabic letter 'Alif' (أ) as a zero-width connector when adjacent to English text, resulting in merged tokens.
    *   *Raw Input*: `EmployeeأEvaluation`
    *   *Desired Output*: `Employee Evaluation`
*   **The Fix**: A generic regex replacement engine injects whitespace delimiters:
    *   `re.sub(r'([a-zA-Z])أ', r'\1 ', text)` catches English-to-Arabic merges.
    *   `re.sub(r'أ([a-zA-Z])', r' \1', text)` catches Arabic-to-English merges.

#### Problem 2: Non-Connecting Characters
*   **The Glitch**: Arabic letters like **Ra (ر)**, **Dal (د)**, and **Waw (و)** do not connect to the left. PDF streams often mistakenly fuse the subsequent character onto them visually.
*   **The Fix**: We explicitly define the set of Non-Connectors: `[اأإآدذرزوؤة]`.
    *   **Logic**: IF `[Non-Connector]` IS FOLLOWED BY `[Start-of-Word Alif]` THEN `Insert Space`.
    *   **Example**: `TablesوChairs` (Merged) becomes `Tables و Chairs`.

#### Problem 3: Logical vs. Display Order (BiDi)
*   **The Glitch**: PDF text is stored in the file in logical memory order (First-to-Last typed), but Arabic is displayed Right-to-Left. Extracting raw bytes results in reversed strings.
*   **The Fix**: We apply `bidi.algorithm.get_display` on every single cell.
    *   *Memory Order*: `(1) Hello (2) World` (L-R)
    *   *Display Logic*: `World Hello` (R-L Context)
    *   *Result*: The extracted string matches what the user *sees*, not what the computer *stores*.

---

## 4. Stream B: Vision-Based Extraction (The "Smart Path")

**Objective**: Handle tables that are essentially "Graphics"—scans, complex layouts, or tables with no detectable text layer.

### 4.1 Step 1: Candidate Detection (Computer Vision / OpenCV)
This step is purely geometric. We do not read text; we look for "Table Shapes".
*   **Pre-Processing**: We convert the PDF page to a high-resolution PNG (300 DPI).
*   **Morphological Dilation**: We apply a `cv2.dilate` filter using a large kernel (e.g., `(20,10)`).
    *   *Why?* Dilation blurs the empty whitespace between words, causing text lines to fuse into solid rectangles.
*   **Contour Analysis**: We run `cv2.findContours`. A "Table" looks like a large, roughly rectangular blob with a high fill rate.
*   **Filtration**: We discard contours that are too small (<10% page width) or too flat (likely footer lines), saving strictly the "Candidates".

### 4.2 Step 2: Classification (Discriminator Model)
Detected rectangles might include diagrams or border decorations. We use a lightweight Vision Language Model (Moondream/LLaVA) as a gatekeeper.
*   **Prompt**: *"Is this image a table? Return specific JSON boolean."*
*   **Strictness**: We employ a low temperature (`0.1`) to ensure deterministic Yes/No answers.

### 4.3 Step 3: Semantic Interpretation & Canonicalization
This is the most critical step. We pass the cropped table image to a Large Vision Model (GPT-4o or LLaVA-13b) with instructions to **interpret** rather than just **transcribe**.

#### **The Canonicalization Prompt Strategy**
We do not ask the model to "give me JSON". We ask it to "Canonicalize the Data".

**The Canonicalization Rules (Injected into System Prompt):**
1.  **Denormalization (Crucial)**:
    *   *Visual Table*: Cell A1 says "Department: IT", Cell A2 and A3 are blank (meaning "Ditto").
    *   *Canonical Output*: Record 1: `{Dept: "IT"}`, Record 2: `{Dept: "IT"}`, Record 3: `{Dept: "IT"}`.
    *   *Why?* Vector databases retrieve atomic chunks. If Record 3 is retrieved alone, it MUST say "IT" explicitly, or it is useless context.
    
2.  **Semantic Headers**:
    *   *Visual Table*: Col 1 header is "Duration", Col 2 header is "%".
    *   *Canonical Output*: `{"entitlement_percentage": "..."}`
    *   *Why?* "%" is meaningless without "Entitlement". The model infers the full meaning.

3.  **Metadata Injection**:
    *   The model must explicitly read the "Table Title" (often located *above* the grid) and inject it into every record's metadata.

---

## 5. Storage Strategy: Direct Embedding (No JSON Files)

Traditional pipelines save the extraction as a `.json` file on disk. We consider this an anti-pattern for RAG.

**The "Store-Embed-Retrieved" Protocol:**

1.  **Generation**: The Vision Model outputs a rich, verbose, natural-language explanation of the table data (The "Canonicalized Summary").
2.  **Immediate Embedding**: This text block is immediately passed to the embedding model (`text-embedding-3-large`).
    *   *Reason*: Embedding models (like BGE-M3) are trained on semantic sentences, not JSON syntax. Embedding a raw JSON string `{ "key": "val" }` often degrades vector quality because the braces and quotes are noise.
    *   *Strategy*: We embed a sentence like *"For Grade 1 employees with 5 years experience, the gratuity is 20 days."* This matches User Natural Language Queries perfectly.
3.  **Vector Persistence**: The resulting 1536-dim vector is pushed to **Qdrant**.
4.  **Payload**: The original JSON structure is stored *only* as a payload for display purposes, but the *search retrieval* happens purely on the semantic explanation vector.

---

## 6. Implementation Status

| Component                     | Status        | Code Reference                             |
| :---------------------------- | :------------ | :----------------------------------------- |
| **PDF Ingestion**             | ✅ Complete    | `extract_tables_final.py`                  |
| **Text Repair (Arabic)**      | ✅ Verified    | `extract_tables_final.py` (Lines 12-44)    |
| **Vision Detection (OpenCV)** | ✅ Complete    | `step01_table_detector.py`                 |
| **Vision Classification**     | ✅ Complete    | `step02_table_classifier.py`               |
| **Semantic Canonicalization** | ⚠️ In Progress | `step03_table_analyzer.py` (Prompt Tuning) |
| **Vector DB Connection**      | 🔄 Pending     | `step04_table_embedder.py`                 |

---

## 7. Conclusion

This architecture shifts the complexity from **Query Time** to **Ingestion Time**. By spending compute power up-front to "Canonicalize" and "Denormalize" complex PDF tables into rich semantic text, we ensure that the RAG retrieval at runtime is simple, fast, and highly accurate.
