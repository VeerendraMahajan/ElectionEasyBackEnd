# Vision AI & Hybrid Confidence Cascade Strategy

## 1. Selected Model: Gemini 3.5 Flash Lite
The platform uses **Google Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`) as its secondary multimodal vision engine.
- Provides fast multimodal vision inference with high accuracy.
- Operates under Google's standard free-tier quota (15 requests/min, 1,500 requests/day), avoiding the 20 requests/day cap enforced on experimental preview models.

---

## 2. Hybrid Confidence Cascade Architecture
VoterLens does **not** send every page or voter card to cloud AI. Instead, it follows a **Local-First Confidence Cascade**:

1. **Step 1: Local Zone OCR**:
   All cards on a page are processed locally first using OpenCV preprocessing and EasyOCR allowlists.
2. **Step 2: Confidence Evaluation**:
   If a card has high confidence (`>= 0.82`) and valid fields (Name, Serial, EPIC/House No, Age, Gender), it is accepted immediately.
   **Result:** 80–95% of cards require 0 cloud API calls.
3. **Step 3: Selective Mini-Batch Refinement**:
   Only degraded or low-confidence cards are bundled into a single mini-batch request to Gemini.
4. **Step 4: 429 Quota Fault Tolerance**:
   If a cloud rate limit (`429 Quota Exceeded`) occurs, the system logs a clean warning and **gracefully keeps the local OCR extraction**.
   **Guarantee:** Processing never crashes or aborts due to cloud API limits.

---

## 3. Header Hierarchy Caching
To eliminate repetitive cloud calls for page headers:
- The Assembly, Part, Section, and Booth numbers extracted from early pages are cached at the document level.
- Subsequent pages automatically inherit the hierarchy rather than making redundant LLM calls.

---

## 4. Anti-Hallucination Rules
The system prompt enforces strict constraints:
1. Extract only clearly visible information.
2. NEVER guess, invent, or hallucinate missing data.
3. If an item is unreadable, return `null`.
4. IDs must be preserved exactly as printed with auto-correction of state prefixes (`0P/` -> `UP/`).
5. Structured JSON output validated through Pydantic schemas.

---

## 5. Devanagari Alphabet Grounding & Character-Level Disambiguation

To prevent models from defaulting to training priors or common name substitutions (such as substituting `रीतु` for `रीनू`), the extraction prompt includes an explicit Devanagari reference matrix:
- **Complete Varnamala Reference**: स्वर (`अ` to `औ`), मात्राएं (`ा`, `ि`, `ी`, `ु`, `ू`, `े`, `ै`, `ो`, `ौ`, `ं`, `्`), व्यंजन (`क` to `ह`), संयुक्त (`क्ष`, `त्र`, `ज्ञ`, `श्र`), and नुक़्ता (`क़`, `ख़`, `ग़`, `ज़`, `फ़`, `ड़`, `ढ़`).
- **Visual Character Disambiguation Rules**:
  - `न` (na) vs `त` (ta): `न` has a closed inner triangular/circular loop; `त` is an open downward curved arch with no loop.
  - `म` (ma) vs `भ` (bha): `म` has a solid shirorekha; `भ` has a broken top shirorekha with an open left spiral.
  - `व` (va) vs `ब` (ba): `व` has an empty circle; `ब` has a diagonal strike-through slash.
  - `घ` (gha) vs `ध` (dha): `घ` connects directly to the top shirorekha; `ध` has a curled open spiral at top-left.
  - `श` (sha) vs `स` (sa): `श` features an ornate loop head; `स` has a simple curved arch with a middle connector.
- **Zero Hardcoded Names**: The downstream transliterator relies purely on standard Indian phonetics (`ी` -> `i`, `ू` -> `u`, etc.), handling any Hindi name accurately without maintenance overhead.
