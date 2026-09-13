# Architecture Overview

## 1. Introduction
FastAPI receives the uploaded PDF or ZIP file. It does not process large documents inside the HTTP request cycle because that would block web workers and cause client timeouts. Instead, it creates an extraction job and schedules the document processing in the background.

The background worker processes the document page by page, extracting the page header and caching the hierarchy, detecting the layout, segmenting individual voter records through local zone OCR or mathematical font remapping, normalizing the data, sorting by ascending serial number (`1, 2, 3...`), and committing the results to PostgreSQL in clean transactional boundaries.

---

## 2. Core Architectural Layers

### 2.1 API Layer (`app/api/`)
Contains thin FastAPI route handlers:
- **`dependencies.py`**: Injects database sessions and service instances.
- **`documents.py`**: File uploads, document listing, page queries, and document records queries (sorted in ascending serial order by default).
- **`jobs.py`**: Real-time progress and job status monitoring.
- **`records.py`**: Search, filtering, human review, and patch corrections (sorted in ascending serial order by default).

### 2.2 Core Layer (`app/core/`)
Provides infrastructure foundations:
- **`config.py`**: Pydantic settings loading from `.env` (`GEMINI_MODEL=gemini-3.5-flash-lite`, `CASCADE_CONFIDENCE_THRESHOLD=0.82`).
- **`database.py`**: SQLAlchemy 2.x async engine with connection pooling.
- **`logging.py`**: Structured JSON logging with `request_id` context propagation.
- **`exceptions.py`**: Global exception hierarchy and JSON error responses.
- **`security.py`**: File signature validation, magic bytes, ZIP slip and bomb protection.

### 2.3 Models & Schemas (`app/models/` & `app/schemas/`)
- **SQLAlchemy Models**: Fully normalized tables linking `documents -> document_pages -> person_records -> extraction_field_results`.
  - `person_records` specifies integer indexing and ascending ordering (`PersonRecord.serial_number.asc().nulls_last()`).
  - `document.records` specifies `order_by="PersonRecord.serial_number"`.
- **Pydantic Schemas**: Structured input validation and nested API responses.

### 2.4 Service Layer (`app/services/`)
Encapsulates business and document AI logic:
- `pdf_service.py` & `zip_service.py`
- `header_extraction_service.py`: Caches hierarchy across pages.
- `ocr_service.py`: Preprocessing, `recognize_digits`, `recognize_alphanumeric`.
- `layout_service.py`: OpenCV morphology for card grid detection.
- `normalization_service.py` & `transliteration_service.py`
- `validation_service.py` & `confidence_service.py`
- `llm_service.py`: Multimodal refinement with 429 quota resilience.

### 2.5 Extractors Layer (`app/extractors/`)
Decoupled extractors for different visual layouts:
- `table_extractor.py`: Mathematical font remapping via `font_mapper.py` in 0.05s.
- `card_extractor.py`: Local Zone-Based OCR + Hybrid Confidence Cascade.
- `generic_extractor.py`: Adaptive fallback for unknown layouts.

---

## 3. Electoral Hierarchy Design Decision
The top-left header of each page contains Assembly, Section, Part, and Booth details. In this architecture:
- These fields are saved **once per page** in `document_pages`.
- They are **not duplicated** inside each voter row.
- Every voter row in `person_records` references `page_id`.
- The API responses join `document_pages` to return a convenient nested `location` object for every voter.
- Headers are cached at the document level so subsequent pages inherit values without unnecessary cloud API calls.
