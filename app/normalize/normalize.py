"""Normalize spoken aviation input to structured text.

Handles NATO phonetic alphabet, spoken numbers, aircraft registrations,
ATA chapter codes, part numbers, and measurement units.
"""

from __future__ import annotations

import re

NATO_TO_LETTER: dict[str, str] = {
    "alfa": "A", "alpha": "A", "bravo": "B", "charlie": "C", "delta": "D",
    "echo": "E", "foxtrot": "F", "golf": "G", "hotel": "H", "india": "I",
    "juliet": "J", "juliett": "J", "kilo": "K", "lima": "L", "mike": "M",
    "november": "N", "oscar": "O", "papa": "P", "quebec": "Q", "romeo": "R",
    "sierra": "S", "tango": "T", "uniform": "U", "victor": "V", "whiskey": "W",
    "xray": "X", "x-ray": "X", "yankee": "Y", "zulu": "Z",
}

WORD_TO_DIGIT: dict[str, str] = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "niner": "9", "nine": "9",
}

TEENS: dict[str, int] = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}

TENS: dict[str, int] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

ATA_CHAPTERS: dict[str, str] = {
    "21": "Air Conditioning", "24": "Electrical Power", "25": "Equipment/Furnishings",
    "26": "Fire Protection", "27": "Flight Controls", "28": "Fuel",
    "29": "Hydraulic Power", "32": "Landing Gear", "36": "Pneumatic",
    "49": "Airborne Auxiliary Power", "52": "Doors", "53": "Fuselage",
    "55": "Stabilizers", "57": "Wings", "71": "Powerplant",
    "72": "Engine", "73": "Engine Fuel and Control", "74": "Ignition",
    "76": "Engine Controls", "77": "Engine Indicating", "78": "Exhaust",
    "79": "Oil", "80": "Starting",
}

UNIT_MAP: dict[str, str] = {
    "inch pounds": "in-lbs", "inch-pounds": "in-lbs", "in lbs": "in-lbs",
    "foot pounds": "ft-lbs", "foot-pounds": "ft-lbs", "ft lbs": "ft-lbs",
    "newton meters": "Nm", "newton-meters": "Nm",
    "inches": "in", "inch": "in",
    "millimeters": "mm", "millimetres": "mm",
    "centimeters": "cm", "centimetres": "cm",
    "pounds per square inch": "PSI",
}

PART_PREFIXES = ("MS", "AN", "NAS", "BAC")


def normalize_nato_phonetic(text: str) -> str:
    """Convert NATO phonetic alphabet words to their corresponding letters.

    Adjacent NATO words are collapsed into a single letter group.
    Handles hyphen-separated and space-separated sequences.
    """
    text = re.sub(r'\bx-ray\b', 'xray', text, flags=re.IGNORECASE)

    nato_words = set(NATO_TO_LETTER.keys())
    def _replace_hyphenated_nato(m):
        parts = m.group(0).split("-")
        if all(p.lower() in nato_words for p in parts):
            return " ".join(parts)
        return m.group(0)

    text = re.sub(r'\b\w+(?:-\w+)+\b', _replace_hyphenated_nato, text)
    tokens = text.split()
    result: list[str] = []
    nato_run: list[str] = []

    def flush_run() -> None:
        if nato_run:
            result.append("".join(nato_run))
            nato_run.clear()

    for token in tokens:
        lower = token.lower()
        if lower in NATO_TO_LETTER:
            nato_run.append(NATO_TO_LETTER[lower])
        else:
            flush_run()
            result.append(token)

    flush_run()
    return " ".join(result)


def _parse_number_words(words: list[str]) -> tuple[str, int]:
    """Parse a sequence of number words starting at position 0.

    Returns (result_string, count_of_words_consumed).
    Handles: digit sequences ("one two three" -> "123"),
    compound numbers ("twenty five" -> "25"),
    hundreds ("one hundred" -> "100"),
    decimals ("two point five" -> "2.5").
    """
    if not words:
        return "", 0

    i = 0
    lower_words = [w.lower() for w in words]

    # Check for compound number (twenty five, etc.) or teen
    if lower_words[0] in TENS:
        val = TENS[lower_words[0]]
        i = 1
        if i < len(lower_words) and lower_words[i] in WORD_TO_DIGIT and lower_words[i] not in ("zero", "oh"):
            val += int(WORD_TO_DIGIT[lower_words[i]])
            i += 1
        return str(val), i

    if lower_words[0] in TEENS:
        return str(TEENS[lower_words[0]]), 1

    # Digit sequence: "one two three" -> "123"
    digits: list[str] = []
    while i < len(lower_words):
        w = lower_words[i]
        if w in WORD_TO_DIGIT:
            digits.append(WORD_TO_DIGIT[w])
            i += 1
        elif w == "hundred" and digits:
            base = int(digits[-1])
            digits[-1] = str(base)
            remaining_digits = digits[:-1]
            # e.g. "one hundred" -> 100, "two hundred" -> 200
            hundreds_val = base * 100
            # Check for trailing digits: "one hundred twenty three"
            if i + 1 < len(lower_words):
                rest, consumed = _parse_number_words(words[i + 1:])
                if consumed > 0 and rest.isdigit():
                    hundreds_val += int(rest)
                    i += 1 + consumed
                else:
                    i += 1
            else:
                i += 1
            result = "".join(remaining_digits) + str(hundreds_val)
            return result, i
        elif w == "point" and digits:
            i += 1
            decimal_digits: list[str] = []
            while i < len(lower_words) and lower_words[i] in WORD_TO_DIGIT:
                decimal_digits.append(WORD_TO_DIGIT[lower_words[i]])
                i += 1
            if decimal_digits:
                return "".join(digits) + "." + "".join(decimal_digits), i
            else:
                # "point" with nothing after — put it back
                i -= 1
                break
        else:
            break

    if digits:
        return "".join(digits), i

    return "", 0


def normalize_spoken_numbers(text: str) -> str:
    """Convert spoken number words to digits."""
    tokens = text.split()
    result: list[str] = []
    i = 0

    while i < len(tokens):
        lower = tokens[i].lower()
        if lower in WORD_TO_DIGIT or lower in TEENS or lower in TENS:
            num_str, consumed = _parse_number_words(tokens[i:])
            if consumed > 0:
                result.append(num_str)
                i += consumed
                continue
        result.append(tokens[i])
        i += 1

    return " ".join(result)


def normalize_registration(text: str) -> str:
    """Normalize aircraft registration from spoken form.

    - "november one two three" -> "N123"
    - "victor tango alpha bravo charlie" -> "VT-ABC"
    """
    cleaned = re.sub(r'\btail\s+(number\s+)?', '', text, flags=re.IGNORECASE).strip()

    # First convert NATO phonetic to letters
    converted = normalize_nato_phonetic(cleaned)
    # Then convert spoken numbers
    converted = normalize_spoken_numbers(converted)

    # Now extract the registration pattern
    # Look for letter groups followed by optional number groups followed by optional letter groups
    parts = converted.split()
    letters_and_nums: list[str] = []
    for p in parts:
        if re.match(r'^[A-Z]+$', p):
            letters_and_nums.append(p)
        elif re.match(r'^[0-9]+$', p):
            letters_and_nums.append(p)
        elif re.match(r'^[A-Z0-9]+$', p):
            letters_and_nums.append(p)

    if not letters_and_nums:
        return text

    reg = "".join(letters_and_nums)

    # Apply formatting rules
    if reg.startswith("VT") and len(reg) > 2:
        return "VT-" + reg[2:]

    return reg


def normalize_ata_chapter(text: str) -> tuple[str, str] | None:
    """Extract ATA chapter code and name from text.

    Returns (code, name) or None if no ATA chapter found.
    """
    # Normalize numbers first
    normalized = normalize_spoken_numbers(text)

    # Look for "ATA XX" or "chapter XX" patterns
    match = re.search(r'(?:ata|chapter)\s+(\d{2})', normalized, re.IGNORECASE)
    if match:
        code = match.group(1)
        name = ATA_CHAPTERS.get(code)
        if name:
            return (code, name)

    # Try with just a bare two-digit number if text starts with ata/chapter context
    match = re.search(r'(\d{2})', normalized)
    if match:
        code = match.group(1)
        if code in ATA_CHAPTERS:
            lower = text.lower()
            if "ata" in lower or "chapter" in lower:
                return (code, ATA_CHAPTERS[code])

    return None


def normalize_part_number(text: str) -> str:
    """Normalize spoken part numbers.

    - "MS two nine five one three dash zero one two" -> "MS29513-012"
    - "mike sierra two niner five one three" -> "MS29513"
    """
    # If already formatted (letters+digits with optional dash), return as-is
    stripped = text.strip()
    if re.match(r'^[A-Z]{2,3}\d[\d-]+$', stripped):
        return stripped

    # First convert NATO to letters
    converted = normalize_nato_phonetic(text)
    # Convert spoken numbers
    converted = normalize_spoken_numbers(converted)

    # Replace "dash" with actual dash
    converted = re.sub(r'\bdash\b', '-', converted, flags=re.IGNORECASE)

    # Remove spaces between parts of the part number
    # Find known prefixes and collapse everything after
    for prefix in PART_PREFIXES:
        pattern = re.compile(r'\b' + prefix + r'\b\s*', re.IGNORECASE)
        match = pattern.search(converted)
        if match:
            before = converted[:match.start()]
            after_prefix = converted[match.end():]
            # Collapse spaces in the number portion (keep dashes)
            number_part = re.sub(r'\s+', '', after_prefix)
            return before.strip() + ((" " + prefix) if before.strip() else prefix) + number_part

    # No known prefix — try to collapse if it looks like a part number
    # Remove spaces around dashes and between digit groups
    result = re.sub(r'\s*-\s*', '-', converted)
    return result


def normalize_units(text: str) -> str:
    """Normalize measurement unit names to abbreviations."""
    result = text
    # Sort by length descending to match longer phrases first
    for spoken, abbrev in sorted(UNIT_MAP.items(), key=lambda x: -len(x[0])):
        result = re.sub(re.escape(spoken), abbrev, result, flags=re.IGNORECASE)
    return result


def normalize_full_transcript(text: str) -> str:
    """Apply all normalizations to a full transcript.

    Order matters:
    1. NATO phonetic (before numbers, since NATO words can precede digit words)
    2. Spoken numbers
    3. Units
    4. Part numbers are handled contextually during extraction, not here
    """
    result = normalize_nato_phonetic(text)
    result = normalize_spoken_numbers(result)
    result = normalize_units(result)
    # Clean up extra whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    return result
