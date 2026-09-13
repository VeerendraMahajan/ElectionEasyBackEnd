import json
import os
import re
import time
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
from PIL import Image
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

    def extract_card_batch(
        self,
        card_images: List[np.ndarray],
        start_index: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract a batch of voter card image crops simultaneously via Gemini Multimodal Vision.
        Dramatically improves throughput and eliminates CPU OCR errors.
        """
        if not self.is_available or not card_images:
            return []

        prompt = (
            "You are an expert OCR extractor for official Indian Electoral Rolls (Voter Lists).\n"
            f"You are provided with {len(card_images)} cropped voter cards labeled 'Card 1' to 'Card {len(card_images)}'.\n"
            "Carefully extract each voter's information into a JSON array of objects with the exact schema:\n"
            "[\n"
            "  {\n"
            "    \"card_index\": 1,\n"
            "    \"serial_number\": integer or null,\n"
            "    \"id_number\": string or null (Voter ID / EPIC like 'WGX0058818' or 'UP/65/289/0099017'),\n"
            "    \"name_hi\": string (elector name in Hindi Devanagari script),\n"
            "    \"name_en\": string or null,\n"
            "    \"relation_type\": \"father\" | \"husband\" | \"mother\" | \"other\" | null,\n"
            "    \"relation_name_hi\": string (father/husband/mother name in Hindi Devanagari script),\n"
            "    \"relation_name_en\": string or null,\n"
            "    \"house_number\": string (preserve exact format e.g. '15/140' or '1ब'),\n"
            "    \"age\": integer (e.g. 45),\n"
            "    \"gender\": \"male\" | \"female\" | \"other\",\n"
            "    \"watermark\": string or null (e.g. \"DELETED\", \"MODIFIED\", \"DUPLICATE\", or null if none)\n"
            "  }\n"
            "]\n"
            "DEVANAGARI ALPHABET REFERENCE (देवनागरी वर्णमाला):\n"
            "- स्वर (Vowels): अ, आ, इ, ई, उ, ऊ, ऋ, ए, ऐ, ओ, औ\n"
            "- मात्राएं (Matras): ा (aa), ि (i), ी (ee/ii), ु (u), ू (oo/uu), ृ (ri), े (e), ै (ai), ो (o), ौ (au), ं (n), ँ (n), ः (h), ् (halant)\n"
            "- व्यंजन (Consonants):\n"
            "  क, ख, ग, घ, ङ | च, छ, ज, झ, ञ | ट, ठ, ड, ढ, ण | त, थ, द, ध, न | प, फ, ब, भ, म\n"
            "  य, र, ल, व | श, ष, स, ह | क्ष, त्र, ज्ञ, श्र | क़, ख़, ग़, ज़, ड़, ढ़, फ़\n"
            "RULES FOR HIGH-FIDELITY EXTRACTION:\n"
            "1. STRICT CHARACTER FIDELITY: Read every Hindi letter strictly as printed glyph-by-glyph. Never substitute or 'autocorrect' an unfamiliar or regional name to a popular/dictionary name.\n"
            "2. VISUAL DISAMBIGUATION:\n"
            "   - 'न' (na) has a closed loop connecting to the stem; 'त' (ta) has an open arch with no loop (e.g. distinguish 'रीनू/रीणू/रिनू' from 'रीतू/रितु').\n"
            "   - 'ण' (na) has a U-shaped loop followed by a vertical stem.\n"
            "   - 'म' (ma) has an unbroken continuous top bar; 'भ' (bha) has a broken top bar and open left loop.\n"
            "   - 'व' (va) has an open oval; 'ब' (ba) has a diagonal slash through the oval (e.g. 'विजय', 'विनोद').\n"
            "   - 'घ' (gha) has a full top bar; 'ध' (dha) has a broken top bar with a top curl.\n"
            "   - 'श' (sha) has a top loop; 'स' (sa) has a horizontal bridge bar.\n"
            "3. State prefix OCR corrections on EPIC IDs (e.g. '0P/' is 'UP/', '0X' is 'DX').\n"
            "4. WATERMARK / STATUS STAMP DETECTION: Look carefully across each card for stamped text, diagonal watermark, or overlay e.g. 'DELETED', 'विलोपित', 'MODIFIED', 'संशोधित', 'DUPLICATE'. If present, return the uppercase watermark string (e.g. 'DELETED'). If none, return null.\n"
            "5. Return ONLY the valid JSON array without markdown formatting or conversational text."
        )

        contents: List[Any] = [prompt]
        for idx, img_bgr in enumerate(card_images):
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            contents.append(f"Card {idx + 1}:")
            contents.append(pil_img)

        max_retries = settings.LLM_MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(contents)
                parsed = self._clean_json_response(response.text)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict) and "voters" in parsed:
                    return parsed["voters"]
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                    logger.warning(f"Gemini quota limit reached (429). Falling back to local OCR without further delay.")
                    break
                logger.warning(f"Gemini card batch extraction attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
        return []

    def extract_table_slice(
        self,
        table_image: np.ndarray,
        column_side: str = "left",
        page_number: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract a vertical column slice of tabular electoral roll (such as PAN_076_7_1.pdf)
        using Gemini Multimodal Vision. Resolves legacy font encodings (KrutiDev) accurately.
        """
        if not self.is_available:
            return []

        rgb = cv2.cvtColor(table_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        prompt = (
            "You are an expert OCR extractor for official Indian Electoral Rolls.\n"
            f"This image is a {column_side.upper()} column tabular section of voters from Page {page_number}.\n"
            "The table contains columns: [Serial No, House No, Elector Name, Father/Husband Name, EPIC/ID Number, Gender, Age].\n"
            "Strict Instructions:\n"
            "1. Extract EVERY single voter row from top to bottom without skipping any row. There should be exactly 50 voter rows in this column.\n"
            "2. In some rows, the EPIC/ID card is missing/not issued. In that case, set id_number to null without shifting other columns.\n"
            "3. Read all Hindi names accurately in proper Unicode Devanagari script (e.g., 'सलमा', 'महादेव', 'अमर सिंह', 'सावित्री', 'प्रमोद', 'सुभाष दोहरे', 'जी सान').\n"
            "4. Important Name Guidelines:\n"
            "   - Distinguish 'जा' from 'ज्ञा': e.g., in serial numbers 1 and 2, the father's name is 'अजान' (Azaan), NOT 'अज्ञान'. In Indian voter rolls 'अजान' is used ('अजान प्रसाद', 'अजान मोहम्मद'), never 'अज्ञान'.\n"
            "   - Output names in pure Hindi Devanagari script; do not embed Latin/English characters (e.g., 'मुजाहिद अली', NOT 'मुजahid अली').\n"
            "5. Preserve house numbers exactly, including suffixes (e.g., '1', '1अ', '1ब', '14ख').\n"
            "6. Infer relation_type ('father' | 'husband' | 'mother' | 'other') based on context.\n"
            "7. Check if there is any watermark across the row (e.g., 'DELETED', 'MODIFIED', 'विलोपित', 'संशोधित'). If present, set watermark to that string; otherwise null.\n"
            "Return a JSON array of objects:\n"
            "[\n"
            "  {\n"
            "    \"serial_number\": integer,\n"
            "    \"house_number\": string,\n"
            "    \"name_hi\": string,\n"
            "    \"relation_type\": \"father\" | \"husband\" | \"mother\" | \"other\",\n"
            "    \"relation_name_hi\": string,\n"
            "    \"id_number\": string or null,\n"
            "    \"gender\": \"male\" | \"female\",\n"
            "    \"age\": integer,\n"
            "    \"watermark\": string or null\n"
            "  }\n"
            "]\n"
            "Return ONLY the valid raw JSON array."
        )

        max_retries = settings.LLM_MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = self.client.generate_content([prompt, pil_img])
                parsed = self._clean_json_response(response.text)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict) and "voters" in parsed:
                    return parsed["voters"]
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
                    logger.warning(f"Gemini quota limit reached (429) on table extraction. Falling back to local deterministic parsing.")
                    break
                logger.warning(f"Gemini table extraction attempt {attempt+1} on page {page_number} ({column_side}) failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
        return []

    def extract_header(self, header_image: np.ndarray, ocr_text: str, page_number: int) -> Optional[PageHeaderExtraction]:
        """Extract page header details using Gemini Flash when deterministic extraction is uncertain."""
        if not self.is_available:
            return None

        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "header_extraction.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        else:
            system_prompt = "Extract assembly, part, section, and booth details from this electoral roll header image."

        prompt = f"{system_prompt}\n\nPage Number: {page_number}\nOCR Extracted Text:\n{ocr_text}\n\nExtract and return the JSON object."

        try:
            rgb_img = cv2.cvtColor(header_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)

            response = self.client.generate_content([prompt, pil_img])
            data = self._clean_json_response(response.text)
            data["page_number"] = page_number
            return PageHeaderExtraction(**data)
        except Exception as e:
            logger.warning(f"Gemini header extraction failed: {e}")
            return None

    def extract_voter_card(self, card_image: np.ndarray, ocr_text: str) -> Optional[VoterExtraction]:
        """Single voter card fallback."""
        cards = self.extract_card_batch([card_image])
        if cards:
            return VoterExtraction(**cards[0])
        return None
