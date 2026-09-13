import re
from typing import Optional, Dict

# Standard Hindi vowel and consonant transliteration mapping
VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n',
    'ः': 'h', '्': ''
}

CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
    'ष': 'sh', 'स': 's', 'ह': 'h', 'ड़': 'r', 'ढ़': 'rh',
    'फ़': 'f', 'ज़': 'z', 'क़': 'q', 'ख़': 'kh', 'ग़': 'gh',
    'फ़': 'f', 'ज़': 'z', 'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ड़': 'r', 'ढ़': 'rh'
}

# Administrative place terms only (NO personal names)
KNOWN_TRANSLITERATIONS: Dict[str, str] = {
    "आर्य नगर": "Arya Nagar",
    "सन्दलपुर": "Sandalpur",
    "कानपुर देहात": "Kanpur Dehat",
    "रिजर्व पुलिस कॉलोनी": "Reserve Police Colony",
    "सिविल लाइन्स": "Civil Lines",
    "अजान": "Azaan",
    "अज़ान": "Azaan",
}


class TransliterationService:
    """Service to transliterate Hindi names and places into English and vice-versa."""

    @staticmethod
    def hindi_to_english(hindi_text: Optional[str]) -> Optional[str]:
        """Convert Hindi text to English using phonetic transliteration."""
        if not hindi_text:
            return None

        text = hindi_text.strip()
        if not text:
            return None

        # Check known dictionary first
        if text in KNOWN_TRANSLITERATIONS:
            return KNOWN_TRANSLITERATIONS[text]

        words = text.split()
        result_words = []

        for word in words:
            if word in KNOWN_TRANSLITERATIONS:
                result_words.append(KNOWN_TRANSLITERATIONS[word])
                continue

            trans = []
            n = len(word)
            i = 0
            while i < n:
                ch = word[i]

                # Combine explicit nuqta if followed by Devanagari sign nukta (U+093C)
                if i + 1 < n and word[i + 1] == '़':
                    combined = ch + '़'
                    if combined in CONSONANTS:
                        ch = combined
                        i += 1

                # Special conjunct 'ज्ञ' (ज + ् + ञ) in Hindi is pronounced and romanized as 'gy' (e.g. ज्ञान -> Gyan)
                if ch == 'ज' and i + 2 < n and word[i + 1] == '्' and word[i + 2] == 'ञ':
                    base_c = 'gy'
                    i += 3
                    if i < n:
                        next_ch = word[i]
                        if next_ch in VOWELS:
                            trans.append(base_c + VOWELS[next_ch])
                            i += 1
                            continue
                        elif next_ch == '्':
                            trans.append(base_c)
                            i += 1
                            continue
                        else:
                            trans.append(base_c + 'a')
                            continue
                    else:
                        trans.append(base_c)
                        continue

                if ch in CONSONANTS:
                    base_c = CONSONANTS[ch]

                    # Phonetic rule for 'फ': In Indian personal names, 'फ' is romanized as 'f'
                    # (e.g. फिरोज -> Firoz, अफसर -> Afsar, फरहत -> Farhat, फुरकान -> Furkan)
                    # except Sanskrit roots like 'फूल' (Phoolwati).
                    if ch == 'फ':
                        if not (i + 1 < n and word[i + 1] == 'ू' and word.startswith('फूल')):
                            base_c = 'f'

                    # Phonetic rule for 'ज' in Persian/Urdu name roots
                    # (e.g. अजान -> Azaan, आजाद -> Azad, शहजाद -> Shahzad, अयाज -> Ayaz, फिरोज -> Firoz)
                    if ch in ['ज', 'ज़']:
                        if word.startswith(('अजा', 'अज़ा', 'फैजा', 'फ़ैज़ा', 'रमजा', 'रमज़ा', 'आजा', 'शहजा', 'सहजा', 'ऐजा', 'एजा', 'मुअज्')):
                            base_c = 'z'
                        elif i > 0 and (word[i - 1] in ['ो', 'े', 'ा', 'या'] or word.endswith(('याज', 'याज़', 'जाद', 'ज़ाद', 'रोज', 'रोज़'))):
                            base_c = 'z'

                    # Check next character
                    if i + 1 < n:
                        next_ch = word[i + 1]
                        if next_ch == '्':  # Halant / virama (conjunct consonant)
                            trans.append(base_c)
                            i += 2
                            continue
                        elif next_ch in VOWELS:  # Explicit vowel matra
                            vowel_str = VOWELS[next_ch]
                            if next_ch == 'ा' and (word.startswith(('अजा', 'अज़ा', 'फैजा', 'फ़ैज़ा')) and i <= 2):
                                vowel_str = 'aa'
                            trans.append(base_c + vowel_str)
                            i += 2
                            continue
                        else:
                            # Non-final consonant: retains inherent 'a' (e.g. सुमन -> Suman, कमल -> Kamal, पवन -> Pavan)
                            trans.append(base_c + 'a')
                            i += 1
                            continue
                    else:
                        # Word-final consonant: modern Hindi schwa deletion (e.g. राम -> Ram, सुमन -> Suman)
                        trans.append(base_c)
                        i += 1
                elif ch in VOWELS:
                    trans.append(VOWELS[ch])
                    i += 1
                else:
                    trans.append(ch)
                    i += 1

            word_en = "".join(trans).capitalize()
            # Standard Indian romanization: ee -> i, oo -> u
            word_en = word_en.replace("ee", "i").replace("oo", "u")
            # Clean duplicate trailing 'a' if redundant (e.g. 'aa' -> 'a' for long names)
            if word_en.endswith("aa") and len(word_en) > 3:
                word_en = word_en[:-1]
            # Clean any triple repetitions
            word_en = re.sub(r'([a-zA-Z])\1{2,}', r'\1', word_en)
            result_words.append(word_en)

        return " ".join(result_words)

    @staticmethod
    def english_to_hindi(english_text: Optional[str]) -> Optional[str]:
        """Simple English to Hindi phonetic transliteration fallback."""
        if not english_text:
            return None
        # Invert known dictionary
        inv = {v.lower(): k for k, v in KNOWN_TRANSLITERATIONS.items()}
        return inv.get(english_text.strip().lower(), english_text)
