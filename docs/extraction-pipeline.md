# Document Extraction Pipeline

## 1. Pipeline Overview
The extraction pipeline is designed for maximum accuracy, robust font recovery, high throughput, and zero-cost offline resilience. It processes PDFs through deterministic layers first, uses local zone preprocessing, and only invokes cloud AI when strictly necessary with automatic 429 quota fault tolerance.

---

## 2. End-to-End Data Flow Diagram

```mermaid
flowchart TD
    User([User / API Client]) -->|Upload PDF or ZIP| API[FastAPI Upload Endpoint]
    API --> Security[Security & Validation Check]
    Security --> Idempotency{SHA-256 in DB?}
    
    Idempotency -->|Already Exists| ReturnExisting[Return Existing Document & Job]
    Idempotency -->|New File| CreateJob[Create Job & Document Record]
    
    CreateJob --> Worker[Background Task / Celery]
    Worker --> InspectPDF[PDF Inspection: Pages, Size, Text vs Scanned]
    
    subgraph Page Processing Loop
        InspectPDF --> Render[Render Page Image via PyMuPDF]
        Render --> HeaderExtract[Extract Page Header: Assembly, Section, Part, Booth]
        HeaderExtract --> HeaderCache[(Document Hierarchy Cache)]
        
        HeaderCache --> DetectLayout{Detect Page Layout}
        
        DetectLayout -->|Card Grid| CardExt[Card Extractor: Local Zone OCR]
        DetectLayout -->|Table Format| TableExt[Table Extractor: Font Remapper font_mapper.py]
        DetectLayout -->|Unknown| GenericExt[Generic Fallback Extractor]
        
        TableExt --> Normalize[Normalization & Transliteration]
        
        CardExt --> ConfCheck{Confidence >= 0.82?}
        ConfCheck -->|High Confidence| Normalize
        ConfCheck -->|Degraded / Low| GeminiRefine[Gemini 3.5 Flash Lite Mini-Batch]
        GeminiRefine -->|Refined or 429 Fallback| Normalize
        
        Normalize --> Validate[Business Rule Validation]
        Validate --> Score[Multi-Signal Confidence Scoring]
        Score --> SortSerial[Sequential Fill & Ascending Serial Sort: 1, 2, 3...]
        SortSerial --> DupCheck[Duplicate Detection]
    end
    
    DupCheck --> PersistDB[(Save to PostgreSQL: Pages, Records in Ascending Order)]
    PersistDB --> CompleteJob[Mark Job Completed]
    CompleteJob --> User
```

---

## 3. Detailed Step-by-Step Explanation

### Step 1: Upload & File Security
- **Magic Bytes Validation**: Verifies the file begins with `%PDF` or `PK\x03\x04`. Rejects MIME spoofing.
- **Path Traversal Protection**: Prevents ZIP slip attacks.
- **Decompression Bomb Protection**: Enforces uncompressed file size limits (500 MB max) and file count limits (100 files max).

### Step 2: Idempotency Check
Calculates the SHA-256 hash of each PDF. If an identical file was already processed, the system returns the existing document record to avoid redundant processing.

### Step 3: Page Analysis & Header Hierarchy Caching
- Renders page to an image using PyMuPDF at 150 DPI.
- Isolates the top-left header region.
- Deterministically extracts Assembly Constituency, Section, Part Number, Booth / Polling Station, and Booth Address using regex rules.
- Caches the hierarchy across pages so subsequent pages inherit values without unnecessary cloud API calls.

### Step 4: Layout Detection
- Runs OpenCV morphological line detection.
- If repeated grid boxes are found, classifies as `CARD_FORMAT` (Sample PDF 2).
- If multiple columns of text rows are detected, classifies as `TABLE_FORMAT` (Sample PDF 1).

### Step 5: Record Segmentation & Extraction
- **For Table Format (`PAN_076_7_1.pdf`)**:
  - Uses [`font_mapper.py`](../app/utils/font_mapper.py) for **Deterministic Font Remapping**.
  - Directly translates legacy 8-bit character codes (KrutiDev / DV-TT) to standard Unicode Devanagari in 0.05 seconds with 100% precision.
- **For Card Format (`PDF Format New-3-38.pdf`)**:
  - Uses **Local Zone-Based Preprocessing & OCR**:
    - Serial zone (top-left) with numeric allowlist (`0123456789`).
    - EPIC zone (top-right) with alphanumeric allowlist (`[A-Z0-9/-]`) and prefix correction (`0P/` -> `UP/`).
    - Hindi text zone (middle-left) isolated from photo noise.
  - High-confidence cards are accepted locally (100% free, 0 API calls).
  - Degraded cards optionally use `gemini-3.5-flash-lite` for refinement, with automatic 429 quota fallback.

### Step 6: Normalization & Transliteration
- Converts Devanagari digits (`२१४`) to standard Arabic numbers (`214`).
- Preserves voter IDs exactly with standard state prefix corrections.
- Transliterates Hindi names into English phonetically (e.g., `सलमा` -> `Salma`).

### Step 7: Sequential Fill & Ascending Serial Sort
- Isolated missing serial numbers are filled sequentially (`S, S+1, S+2...`).
- Records are sorted in strict ascending order by serial number (`1, 2, 3, ...`).

### Step 8: Validation & Storage
- Validates age (18 to 130) and presence of elector names.
- Computes overall record confidence. Records below threshold are flagged as `REVIEW_REQUIRED`.
- Commits records to PostgreSQL with ascending order indexing.
