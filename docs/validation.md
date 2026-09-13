# Validation & Confidence Scoring

## 1. Validation Philosophy
In electoral extraction, incorrect data is far worse than missing data.
- Never guess missing information.
- If data cannot be reliably extracted, return `NULL` and mark `REVIEW_REQUIRED`.

## 2. Validation Statuses
Every record in `person_records` has a `validation_status`:
- **`VALID`**: All core fields (Name, Serial Number, Age, Gender) are extracted with high confidence and pass sanity checks.
- **`WARNING`**: Minor non-critical discrepancies (e.g. ID number absent, but Name, Serial, Age, and Gender are clean).
- **`REVIEW_REQUIRED`**: Important fields are uncertain, age is out of bounds, or confidence is below the threshold.
- **`CORRECTED`**: A human reviewer has verified or updated the record.
- **`FAILED`**: The record could not be extracted at all (e.g. neither name nor serial number found).

## 3. Multi-Signal Confidence Scoring
Overall confidence is calculated using multiple signals:
1. **OCR Confidence (40%)**: Average character/word confidence returned by the OCR engine.
2. **Field Presence (40%)**: Points awarded for presence of Name (15%), Serial Number (10%), Age (5%), Gender (5%), and ID (5%).
3. **Extraction Reliability (20%)**: Deterministic regex (+20%), Clean OCR (+15%), LLM (+10%).
4. **Font Corruption Penalty**: Deducts 25% if unrecovered font corruption characters are detected in the raw record text.

## 4. Human Review & Auditability
Records marked `REVIEW_REQUIRED` appear in the review queue:
`GET /api/v1/records/review-required`

When an operator updates a record via `PATCH /api/v1/records/{id}`, the system:
- Stores previous values in `correction_history` JSON.
- Updates the record fields.
- Sets `validation_status = "CORRECTED"`.
- Preserves the original raw extraction evidence.
