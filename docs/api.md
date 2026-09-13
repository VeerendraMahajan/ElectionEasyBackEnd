# REST API Reference

All endpoints are versioned under `/api/v1/`.

> [!TIP]
> **Postman Collection & Environment**: Pre-configured collection and environment files are available in the repository:
> - Collection: [`postman/VoterLens.postman_collection.json`](../postman/VoterLens.postman_collection.json)
> - Environment: [`postman/VoterLens.postman_environment.json`](../postman/VoterLens.postman_environment.json)

---

## 1. Document Endpoints

### `POST /api/v1/documents/upload`
Upload a single PDF or a ZIP archive containing multiple PDFs.
- **Request**: `multipart/form-data` with key `file`.
- **Response**: `202 Accepted`
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "QUEUED",
  "message": "Successfully queued 1 document(s) for extraction.",
  "documents": [
    {
      "id": "da33ba94-408d-4985-868b-5784f76a5775",
      "original_filename": "sample_data_1.pdf",
      "file_type": "pdf",
      "file_size": 633081,
      "sha256": "b73e...",
      "status": "QUEUED",
      "total_pages": 1,
      "created_at": "2026-09-13T13:44:18Z",
      "updated_at": "2026-09-13T13:44:18Z"
    }
  ]
}
```

### `POST /api/v1/documents/upload-tabular`
Dedicated endpoint for uploading tabular electoral rolls (such as 2-column Panchayat lists like `sample_data_1.pdf`).
- **Request**: `multipart/form-data` with key `file`.
- **Response**: `202 Accepted`
- **Routing**: Explicitly forces tabular extraction (`format_hint="TABLE_FORMAT"`), routing directly to multimodal vision slicing and digital overlay cross-validation to guarantee 100% extraction accuracy for all records.

### `GET /api/v1/documents`
List uploaded documents with pagination (`skip`, `limit`).

### `GET /api/v1/documents/{document_id}`
Retrieve metadata for a specific document.

### `GET /api/v1/documents/{document_id}/pages`
Retrieve all pages with extracted page-level electoral hierarchy (Assembly, Section, Part, Booth).

### `GET /api/v1/documents/{document_id}/records`
Retrieve extracted voter records for a document.
- **Query Parameters**:
  - `page_number` (optional int)
  - `validation_status` (optional string, e.g. `VALID`, `REVIEW_REQUIRED`)
  - `sort_by` (string, default: `"serial_number"`, supports `serial_number`, `age`, `name`)
  - `sort_order` (string, default: `"asc"`, supports `asc` for `1, 2, 3...` and `desc`)
  - `skip` (int, default: 0)
  - `limit` (int, default: 50, max: 100)
- **Ascending Order Guarantee**: By default, records are returned sorted by `serial_number ASC NULLS LAST` (`1, 2, 3, ...`).

---

## 2. Job Monitoring Endpoint

### `GET /api/v1/jobs/{job_id}`
Check status and real-time processing progress of an extraction job.
```json
{
  "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "PROCESSING",
  "total_documents": 1,
  "processed_documents": 0,
  "total_pages": 36,
  "processed_pages": 12,
  "total_records": 1200,
  "processed_records": 1200,
  "failed_records": 0,
  "started_at": "2026-09-13T13:44:20Z",
  "completed_at": null,
  "error_message": null
}
```

---

## 3. Voter Record Endpoints

### `GET /api/v1/records`
Search and filter voter records across electoral hierarchy and person fields in ascending serial number order:
- **Filters**:
  - `document_id`, `page_id`, `page_number`
  - `assembly_number`, `section_number`, `part_number`, `booth_number`
  - `gender`, `min_age`, `max_age`
  - `house_number`, `id_number`
  - `validation_status`, `min_confidence`
- **Sorting Parameters**:
  - `sort_by` (default: `"serial_number"`, options: `serial_number`, `age`, `name`)
  - `sort_order` (default: `"asc"`, options: `asc`, `desc`)
  - `skip` (default: 0)
  - `limit` (default: 50)
- **Response**: Paginated list of records sorted strictly `1, 2, 3...` by default.

### `GET /api/v1/records/review-required`
Get records flagged for human review (`validation_status = 'REVIEW_REQUIRED'`).

### `GET /api/v1/records/{record_id}`
Retrieve a single record with nested `location`, `voter`, `confidence`, and `source` information.

### `PATCH /api/v1/records/{record_id}`
Apply human review corrections while preserving full audit trail in `correction_history`.

### `POST /api/v1/records/{record_id}/validate`
Re-run validation checks on an existing record.
