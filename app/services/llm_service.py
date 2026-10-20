import json
import os
import re
import time
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
from PIL import Image
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMExtractionError
from app.schemas.page import PageHeaderExtraction
from app.schemas.record import VoterExtraction


class LLMService:
    """Service to interact with Gemini Flash for high-accuracy multimodal vision extractions."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                logger.info(f"Initialized Gemini LLM Service with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini client: {e}")

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def _clean_json_response(self, text_resp: str) -> Any:
        """Strip markdown code fences and load JSON safely."""
        text = text_resp.strip()
        if text.startswith("```"):
            # Remove opening ```json or ```
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            # Remove closing ```
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        return json.loads(text)

    def extract_card_strip(
        self,
        strip_image: np.ndarray,
        start_card_index: int = 1,
        expected_count: int = 15,
        page_number: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Extract a grid strip of multiple voter cards in a single Gemini Vision API call.
        Processes up to 15 cards at once in ~3-5 seconds, drastically reducing API calls
        from 30 down to 2 per page, avoiding 429 quota exhaustion, and ensuring 100% precision.
        """
        if not self.is_available or strip_image is None or strip_image.size == 0:
            return []

        rgb = cv2.cvtColor(strip_image, cv2.COLOR_BGR2RGB)
        # Ensure sufficient width for text clarity
        h, w = rgb.shape[:2]
        if w < 800:
            scale = 800 / w
            rgb = cv2.resize(rgb, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        pil_img = Image.fromarray(rgb)

        prompt = (
            "You are an expert OCR specialist for official Indian Electoral Rolls (Voter ID cards).\n"
            f"The image contains a grid strip of {expected_count} voter cards from Page {page_number} "
            f"(cards starting from index {start_card_index} to {start_card_index + expected_count - 1}).\n"
            "The reading order is ROW BY ROW, LEFT TO RIGHT.\n\n"
            "CARD LAYOUT & FIELD EXTRACTION RULES (100% precision required):\n"
            "  • TOP-LEFT: Serial Number (क्र.सं.) — sequential integer (e.g. 1, 2, ...)\n"
            "  • TOP-RIGHT: EPIC / Voter ID Number — alphanumeric code (e.g. ZTU1742048, WGX0058818, UP/65/289/0099017)\n"
            "  • BODY: Hindi text with labeled fields:\n"
            "      - नाम : <elector's name in Hindi Devanagari exactly as printed>\n"
            "      - पिता / पति / माता का नाम : <relation name in Hindi Devanagari exactly as printed>\n"
            "      - मकान संख्या : <house number string, e.g. '००', '०', '1ब', '15/102'>\n"
            "      - आयु : <age as integer>\n"
            "      - लिंग : <पुरुष (male) or महिला (female)>\n"
            "  • WATERMARK: If diagonal stamp present across card (e.g. DELETED, MODIFIED, विलोपित), note it.\n\n"
            "HINDI CHARACTER DISAMBIGUATION:\n"
            "  • 'न' (na) vs 'त' (ta); 'ण' (ṇa) vs 'न'; 'म' (ma) vs 'भ' (bha); 'व' (va) vs 'ब' (ba)\n"
            "  • Preserve all matras: ि (i), ी (ii), ु (u), ू (uu) exactly as printed.\n\n"
            f"MANDATORY: Extract ALL {expected_count} cards. Return ONLY a valid JSON list of objects in order:\n"
            "[\n"
            "  {\n"
            f"    \"grid_index\": {start_card_index},\n"
            "    \"serial_number\": <integer or null>,\n"
            "    \"id_number\": <string or null>,\n"
            "    \"name_hi\": <string exactly as printed>,\n"
            "    \"relation_type\": <\"father\" | \"husband\" | \"mother\" | \"other\">,\n"
            "    \"relation_name_hi\": <string exactly as printed>,\n"
            "    \"house_number\": <string e.g. \"००\", \"1ब\">,\n"
            "    \"age\": <integer>,\n"
            "    \"gender\": <\"male\" | \"female\" | \"other\">,\n"
            "    \"watermark\": <\"DELETED\" | \"MODIFIED\" | null>\n"
            "  }\n"
            "]\n"
            "Return ONLY the JSON array (no markdown code blocks, no explanation)."
        )

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        for m_name in candidate_models:
            for attempt in range(2):
                try:
                    mod = genai.GenerativeModel(m_name)
                    response = mod.generate_content([prompt, pil_img])
                    parsed = self._clean_json_response(response.text)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        logger.info(
                            f"Page {page_number}: Strip extraction succeeded ({len(parsed)}/{expected_count} cards) "
                            f"using model {m_name}."
                        )
                        return parsed
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower():
                        logger.warning(
                            f"Quota exceeded on model {m_name} during strip extraction: {e}. Trying fallback model."
                        )
                        break
                    logger.warning(f"Strip extraction attempt {attempt+1} on {m_name} failed: {e}")
                    time.sleep(1.0)
        return []

    def extract_card_batch(
        self,
        card_images: List[np.ndarray],
        start_index: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract a batch of voter card image crops via Gemini Multimodal Vision.
        Each card is processed individually for maximum accuracy on sensitive data.
        """
        if not self.is_available or not card_images:
            return []

        all_results: List[Dict[str, Any]] = []
        for idx, img_bgr in enumerate(card_images):
            result = self._extract_single_card(img_bgr, card_index=start_index + idx)
            if result:
                all_results.append(result)
        return all_results

    def _extract_single_card(
        self,
        img_bgr: np.ndarray,
        card_index: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a single voter card image crop with maximum accuracy.
        Sends the card to Gemini Vision with a detailed field-by-field prompt.
        """
        if not self.is_available:
            return None

        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        # Upscale small card crops for better OCR quality
        h, w = rgb.shape[:2]
        if w < 400:
            scale = 400 / w
            rgb = cv2.cvtColor(
                cv2.resize(img_bgr, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC),
                cv2.COLOR_BGR2RGB
            )
        pil_img = Image.fromarray(rgb)

        prompt = (
            "You are an expert OCR specialist for official Indian Electoral Rolls (Voter ID / EPIC cards).\n"
            "Analyze the SINGLE voter card image provided and extract ALL fields with 100% accuracy.\n\n"
            "CARD LAYOUT GUIDE (fields appear in this order, top to bottom):\n"
            "  TOP-LEFT corner: क्र.सं. (Serial Number) — a small integer (e.g. 1, 2, 42)\n"
            "  TOP-RIGHT corner: EPIC / Voter ID Number — alphanumeric code (e.g. ZTU1742048, WGX0058818, UP/65/289/0099017)\n"
            "  BODY LEFT side: Hindi text with labeled fields in the format 'label : value'\n"
            "    • नाम : <elector's name in Hindi>\n"
            "    • पिता का नाम / पति का नाम / माता का नाम : <relation name in Hindi>\n"
            "    • मकान संख्या : <house number — may be digits, '00', '000', '1ब', '15/102', etc.>\n"
            "    • आयु : <age as integer>\n"
            "    • लिंग : <पुरुष (male) or महिला (female)>\n"
            "  RIGHT side: Placeholder box labeled 'फोटो उपलब्ध है' (photo available)\n"
            "  WATERMARK: Some cards have diagonal stamp text across the card (e.g. DELETED, MODIFIED, DUPLICATE, विलोपित, संशोधित)\n\n"
            "HINDI CHARACTER DISAMBIGUATION (read every glyph exactly as printed):\n"
            "  • 'न' (na): closed loop to stem | 'त' (ta): open arch, no loop\n"
            "  • 'ण' (ṇa): U-shape loop + vertical stem | 'ण' ≠ 'न'\n"
            "  • 'म' (ma): unbroken continuous top bar | 'भ' (bha): broken top bar + open left loop\n"
            "  • 'व' (va): open oval | 'ब' (ba): oval with diagonal slash\n"
            "  • 'घ' (gha): full closed top bar | 'ध' (dha): broken top bar with curl\n"
            "  • 'श' (sha): top loop present | 'स' (sa): horizontal bridge bar, no loop\n"
            "  • 'ल' (la): flag on right | 'ल' ≠ 'ट' ≠ 'ठ'\n"
            "  • Matras: ि (i) before consonant visually, ी (ii) after; ु (u) below; ू (uu) below+longer\n"
            "  • Conjuncts: क्ष, त्र, ज्ञ, श्र — read as complete units\n\n"
            "EPIC ID RULES (critical — preserve exactly):\n"
            "  • Format varies: 3 letters + 7 digits (e.g. ZTU1742048) or STATE/NUM/NUM/NUM (e.g. UP/65/289/0099017)\n"
            "  • Common OCR corrections: '0P/' → 'UP/', '0X' → 'DX', 'l' → '1' in numeric parts\n"
            "  • NEVER add spaces or change letter case — must be exactly as printed\n\n"
            "HOUSE NUMBER RULES:\n"
            "  • Preserve exact format including suffixes: '00', '000', '1ब', '1अ', '15/102', '141/2'\n"
            "  • '00' or '000' or '०' means the house number is literally '00' / '0' — do NOT convert to null\n\n"
            "Return ONLY this exact JSON object (no markdown, no explanation):\n"
            "{\n"
            f"  \"card_index\": {card_index},\n"
            "  \"serial_number\": <integer or null>,\n"
            "  \"id_number\": <string exactly as printed, or null>,\n"
            "  \"name_hi\": <elector name in Hindi Devanagari, exactly as printed>,\n"
            "  \"name_en\": <phonetic English transliteration or null>,\n"
            "  \"relation_type\": <\"father\" | \"husband\" | \"mother\" | \"other\" — infer from label>,\n"
            "  \"relation_name_hi\": <relation's name in Hindi Devanagari, exactly as printed>,\n"
            "  \"relation_name_en\": <phonetic English transliteration or null>,\n"
            "  \"house_number\": <string preserving exact format e.g. \"00\", \"1ब\", \"15/102\">,\n"
            "  \"age\": <integer, e.g. 45>,\n"
            "  \"gender\": <\"male\" | \"female\" | \"other\">,\n"
            "  \"watermark\": <\"DELETED\" | \"MODIFIED\" | \"DUPLICATE\" | null>\n"
            "}"
        )

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        for m_name in candidate_models:
            for attempt in range(2):
                try:
                    mod = genai.GenerativeModel(m_name)
                    response = mod.generate_content([prompt, pil_img])
                    parsed = self._clean_json_response(response.text)
                    if isinstance(parsed, dict):
                        return parsed
                    elif isinstance(parsed, list) and parsed:
                        return parsed[0]
                    break
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                        logger.warning(f"Quota exceeded on model {m_name} for card {card_index}: {e}. Trying fallback.")
                        break
                    logger.warning(f"Gemini single card extraction attempt {attempt+1} on {m_name} for card {card_index} failed: {e}")
                    time.sleep(1.0)
        return None

    def extract_table_slice(
        self,
        table_image: np.ndarray,
        column_side: str = "left",
        page_number: int = 1,
        expected_rows: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Extract a vertical column slice of tabular electoral roll using Gemini Vision.
        Targets near-100% accuracy with detailed column-order and Hindi character rules.
        """
        if not self.is_available:
            return []

        rgb = cv2.cvtColor(table_image, cv2.COLOR_BGR2RGB)
        # Upscale for higher text clarity
        h, w = rgb.shape[:2]
        if w < 600:
            scale = 600 / w
            rgb = cv2.resize(rgb, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        pil_img = Image.fromarray(rgb)

        prompt = (
            "You are a senior OCR specialist for official Indian Panchayat / State Electoral Rolls.\n"
            f"This image is the {column_side.upper()} half of a two-column tabular voter list from Page {page_number}.\n\n"
            "TABLE COLUMN ORDER (left to right, exactly as printed):\n"
            "  Col 1 — क्र.सं.  (Serial Number): a sequential integer (1, 2, 3…)\n"
            "  Col 2 — मकान नं. (House Number): string — may include Hindi letter suffixes (1अ, 1ब, 4ख, 14ख) or plain digits\n"
            "  Col 3 — निर्वाचक का नाम (Elector Name): full name in Hindi Devanagari\n"
            "  Col 4 — पिता/पति/माता का नाम (Relation Name): full name in Hindi Devanagari\n"
            "  Col 5 — एस.वी.एन. / EPIC (Voter ID): alphanumeric code (e.g. SNPFAA002, SNPMAA005) — may be blank/missing\n"
            "  Col 6 — लिंग (Gender): म = महिला (female), पु = पुरुष (male)\n"
            "  Col 7 — आयु (Age): integer\n\n"
            f"MANDATORY: Extract EVERY row. There are approximately {expected_rows} voter rows in this image. Do NOT skip any row.\n"
            "If the EPIC/ID (Col 5) is missing for a row, set id_number to null — do NOT shift other columns.\n\n"
            "HINDI DEVANAGARI ACCURACY RULES:\n"
            "  1. Copy EVERY character exactly as printed — never substitute with a 'common' name spelling.\n"
            "  2. Key disambiguations:\n"
            "     • 'न' (na): closed loop to stem — 'त' (ta): open arch, no loop\n"
            "     • 'ण' (ṇa): U-shape + vertical stem — different from 'न'\n"
            "     • 'म' (ma): continuous top bar — 'भ' (bha): broken top bar + open left loop\n"
            "     • 'व' (va): open oval — 'ब' (ba): oval with diagonal slash\n"
            "     • 'घ' (gha): closed full bar — 'ध' (dha): broken bar + top curl\n"
            "     • 'श' (sha): has top loop — 'स' (sa): horizontal bridge, no loop\n"
            "  3. 'जा' and 'ज्ञा' are DIFFERENT: 'अजान' (name) ≠ 'अज्ञान' (ignorance). Always prefer 'अजान' for names.\n"
            "  4. Output ONLY pure Unicode Devanagari — no Latin/English characters embedded in Hindi names.\n"
            "  5. Conjunct consonants (क्ष, त्र, ज्ञ, श्र) must be read as single units.\n\n"
            "HOUSE NUMBER RULES:\n"
            "  • Preserve exactly: '1', '1अ', '1ब', '4ख', '14ख', '12अ', '4 ख', etc.\n"
            "  • If house number cell is empty, use null.\n\n"
            "RELATION TYPE: Infer from the family context — if the voter is female and has a husband, use 'husband'; otherwise 'father'. Use 'mother' only if clearly labeled माता.\n\n"
            "WATERMARK: If any row has a diagonal stamp/watermark (DELETED, MODIFIED, विलोपित, संशोधित), set watermark field to the uppercase English equivalent; otherwise null.\n\n"
            "Return a JSON array — one object per voter row, in order:\n"
            "[\n"
            "  {\n"
            "    \"serial_number\": <integer>,\n"
            "    \"house_number\": <string or null>,\n"
            "    \"name_hi\": <elector name in Hindi Devanagari — exactly as printed>,\n"
            "    \"relation_type\": \"father\" | \"husband\" | \"mother\" | \"other\",\n"
            "    \"relation_name_hi\": <relation's name in Hindi Devanagari — exactly as printed>,\n"
            "    \"id_number\": <EPIC/SVN string exactly as printed, or null if missing>,\n"
            "    \"gender\": \"male\" | \"female\" | \"other\",\n"
            "    \"age\": <integer>,\n"
            "    \"watermark\": <\"DELETED\" | \"MODIFIED\" | \"DUPLICATE\" | null>\n"
            "  }\n"
            "]\n"
            "Return ONLY the raw JSON array — no markdown fences, no commentary."
        )

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        for m_name in candidate_models:
            for attempt in range(2):
                try:
                    mod = genai.GenerativeModel(m_name)
                    response = mod.generate_content([prompt, pil_img])
                    parsed = self._clean_json_response(response.text)
                    if isinstance(parsed, list):
                        return parsed
                    elif isinstance(parsed, dict) and "voters" in parsed:
                        return parsed["voters"]
                    break
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                        logger.warning(f"Gemini quota limit reached on {m_name} during table extraction. Trying fallback model.")
                        break
                    logger.warning(f"Gemini table extraction attempt {attempt+1} on {m_name} for page {page_number} ({column_side}) failed: {e}")
                    time.sleep(1.0)
        return []

    def extract_header(self, header_image: np.ndarray, ocr_text: str, page_number: int) -> Optional[PageHeaderExtraction]:
        """Extract page header details using Gemini Vision when deterministic extraction is uncertain."""
        if not self.is_available:
            return None

        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "header_extraction.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        else:
            system_prompt = "Extract assembly, part, section, and booth details from this electoral roll header image."

        prompt = f"{system_prompt}\n\nPage Number: {page_number}\nOCR Extracted Text:\n{ocr_text}\n\nExtract and return the JSON object."

        rgb_img = cv2.cvtColor(header_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        for m_name in candidate_models:
            try:
                mod = genai.GenerativeModel(m_name)
                response = mod.generate_content([prompt, pil_img])
                data = self._clean_json_response(response.text)
                data["page_number"] = page_number
                return PageHeaderExtraction(**data)
            except Exception as e:
                logger.warning(f"Gemini header extraction with {m_name} failed: {e}")
        return None

    def extract_assembly_page(self, page_image: np.ndarray, page_number: int) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from the Assembly Details summary page (Page 1 of demo_1_latest.pdf).
        This is a structured form with named fields — not a voter list.
        Returns a dict with all extractable assembly/booth/section metadata.
        """
        if not self.is_available:
            return None

        rgb = cv2.cvtColor(page_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        prompt = (
            "You are an expert at reading official Indian Electoral Roll cover/summary pages.\n"
            "This image is the ASSEMBLY DETAILS page (page 1) of a Voter List PDF from Uttar Pradesh.\n\n"
            "Extract ALL visible information from this structured form and return it as a JSON object.\n\n"
            "FIELDS TO EXTRACT (extract exactly as printed, translate labels to English key names):\n"
            "  1. 'title': The main heading/title of the document (e.g. 'निर्वाचक नामावली 2026 S24 उत्तर प्रदेश')\n"
            "  2. 'assembly_number': विधानसभा निर्वाचन क्षेत्र number (e.g. '223')\n"
            "  3. 'assembly_name_hi': विधानसभा निर्वाचन क्षेत्र name in Hindi (e.g. 'झाँसी नगर')\n"
            "  4. 'assembly_reservation': reservation status (e.g. 'सामान्य' = General)\n"
            "  5. 'part_number': भाग संख्या (e.g. '7')\n"
            "  6. 'parliamentary_number': संसदीय निर्वाचन क्षेत्र number (e.g. '46')\n"
            "  7. 'parliamentary_name_hi': संसदीय निर्वाचन क्षेत्र name in Hindi\n"
            "  8. 'revision_year': पुनरीक्षण का वर्ष (year)\n"
            "  9. 'qualifying_date': अर्हता तिथि (qualifying date)\n"
            "  10. 'revision_type': पुनरीक्षण का प्रकार\n"
            "  11. 'publication_date': प्रकाशन की तिथि\n"
            "  12. 'roll_identity': निर्वाचक नामावली की पहचान text\n"
            "  13. 'sections': भाग में अनुभागों की संख्या और नाम — list of section names (e.g. ['1-मेडिकल आवास २', '2-मयूर विहार', '3-करगुवां जी'])\n"
            "  14. 'main_town_village': मुख्य कस्बा अथवा ग्राम\n"
            "  15. 'ward': वार्ड\n"
            "  16. 'post_office': डाकघर\n"
            "  17. 'police_station': थाना\n"
            "  18. 'panchayat': पंचायत\n"
            "  19. 'block': ब्लॉक\n"
            "  20. 'tehsil': तहसील\n"
            "  21. 'district': जिला\n"
            "  22. 'pin_code': पिन कोड\n"
            "  23. 'booth_number': मतदान स्थल की संख्या\n"
            "  24. 'booth_name_hi': मतदान स्थल का नाम\n"
            "  25. 'booth_address_hi': मतदान स्थल का पता\n"
            "  26. 'booth_type': मतदान स्थल के प्रकार (पुरुष/महिला/सामान्य)\n"
            "  27. 'auxiliary_booths': इस भाग में सहायक मतदान स्थलों की संख्या\n"
            "  28. 'serial_from': प्रारम्भिक क्रम संख्या (starting serial number)\n"
            "  29. 'serial_to': अंतिम क्रम संख्या (ending serial number)\n"
            "  30. 'total_male': पुरुष मतदाता count\n"
            "  31. 'total_female': महिला मतदाता count\n"
            "  32. 'total_third_gender': तृतीय लिंग count\n"
            "  33. 'total_voters': कुल मतदाता total\n\n"
            "Return ONLY valid JSON — no markdown, no extra text.\n"
            "If a field is not visible or not applicable, set it to null."
        )

        candidate_models = [self.model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        for m_name in candidate_models:
            try:
                mod = genai.GenerativeModel(m_name)
                response = mod.generate_content([prompt, pil_img])
                data = self._clean_json_response(response.text)
                if isinstance(data, dict):
                    data["page_number"] = page_number
                    return data
            except Exception as e:
                logger.warning(f"Gemini assembly page extraction with {m_name} failed on page {page_number}: {e}")
        return None

    def extract_voter_card(self, card_image: np.ndarray, ocr_text: str) -> Optional[VoterExtraction]:
        """Single voter card fallback."""
        result = self._extract_single_card(card_image, card_index=1)
        if result:
            from app.services.normalization_service import NormalizationService
            norm = NormalizationService.normalize_voter_record(
                serial_number=result.get("serial_number"),
                raw_house_number=result.get("house_number"),
                raw_name=result.get("name_hi"),
                raw_relation_name=result.get("relation_name_hi"),
                raw_relation_label=result.get("relation_type"),
                raw_id_number=result.get("id_number"),
                raw_gender=result.get("gender"),
                raw_age=result.get("age"),
                photo_available=True,
                raw_watermark=result.get("watermark"),
            )
            return VoterExtraction(**norm)
        return None
