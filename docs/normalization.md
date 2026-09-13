# Normalization & Transliteration

## 1. Bilingual Storage Requirement
The database stores both Hindi and English values for key fields:
- `name_hi` and `name_en`
- `relation_name_hi` and `relation_name_en`
- `gender_hi` and `gender_en`
- `assembly_name_hi` and `assembly_name_en`
- `section_name_hi` and `section_name_en`
- `booth_name_hi` and `booth_name_en`
- `booth_address_hi` and `booth_address_en`

## 2. Names Must Be Transliterated, NOT Translated
Names are proper nouns and must be transliterated phonetically, never translated by their semantic meaning:
- `सलमा` -> `Salma` (NOT translated)
- `सुरेश कुमार` -> `Suresh Kumar`
- `आर्य नगर` -> `Arya Nagar`

## 3. Voter IDs Must NEVER Be Modified
Voter ID / EPIC / SVN numbers (e.g. `SNPFAA002`, `WGX1896653`, `UP/65/289/0099047`):
- Must **NEVER** be translated or transliterated.
- Must preserve exact alphanumeric characters and forward slashes.

## 4. Devanagari Numeral Normalization
Devanagari digits are normalized 1:1 to ASCII digits:
- `०` -> `0`
- `१` -> `1`
- `२` -> `2`
- `३` -> `3`
- `४` -> `4`
- `५` -> `5`
- `६` -> `6`
- `७` -> `7`
- `८` -> `8`
- `९` -> `9`

Example: Assembly `२१४` becomes `214`, Part `२६` becomes `26`, Age `३७` becomes `37`.

## 5. House Numbers
House numbers are always stored as **strings** to preserve alphanumeric values like:
`1`, `1ब`, `15/102`, `20ब/3`, `001`.
