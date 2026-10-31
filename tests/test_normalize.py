"""Tests for app.normalize.normalize module."""

import pytest
from app.normalize.normalize import (
    normalize_nato_phonetic,
    normalize_spoken_numbers,
    normalize_registration,
    normalize_ata_chapter,
    normalize_part_number,
    normalize_units,
    normalize_full_transcript,
)


# ---------- NATO Phonetic ----------

class TestNatoPhonetic:
    @pytest.mark.parametrize("word,letter", [
        ("alpha", "A"), ("alfa", "A"), ("bravo", "B"), ("charlie", "C"),
        ("delta", "D"), ("echo", "E"), ("foxtrot", "F"), ("golf", "G"),
        ("hotel", "H"), ("india", "I"), ("juliet", "J"), ("juliett", "J"),
        ("kilo", "K"), ("lima", "L"), ("mike", "M"), ("november", "N"),
        ("oscar", "O"), ("papa", "P"), ("quebec", "Q"), ("romeo", "R"),
        ("sierra", "S"), ("tango", "T"), ("uniform", "U"), ("victor", "V"),
        ("whiskey", "W"), ("xray", "X"), ("x-ray", "X"), ("yankee", "Y"),
        ("zulu", "Z"),
    ])
    def test_individual_letters(self, word, letter):
        assert normalize_nato_phonetic(word) == letter

    def test_sequence(self):
        assert normalize_nato_phonetic("victor tango alpha bravo charlie") == "VTABC"

    def test_hyphen_separated(self):
        assert normalize_nato_phonetic("victor-tango-alpha-bravo-charlie") == "VTABC"

    def test_mixed_with_non_nato(self):
        assert normalize_nato_phonetic("tail victor tango alpha bravo charlie") == "tail VTABC"

    def test_case_insensitive(self):
        assert normalize_nato_phonetic("Alpha BRAVO Charlie") == "ABC"

    def test_no_nato_words(self):
        assert normalize_nato_phonetic("hello world") == "hello world"

    def test_empty_string(self):
        assert normalize_nato_phonetic("") == ""

    def test_nato_between_non_nato(self):
        assert normalize_nato_phonetic("found alpha bravo on wing") == "found AB on wing"


# ---------- Spoken Numbers ----------

class TestSpokenNumbers:
    @pytest.mark.parametrize("spoken,expected", [
        ("one two three", "123"),
        ("zero zero seven", "007"),
        ("twenty five", "25"),
        ("thirty", "30"),
        ("one hundred", "100"),
        ("two point five", "2.5"),
        ("ten", "10"),
        ("eleven", "11"),
        ("nineteen", "19"),
        ("ninety nine", "99"),
    ])
    def test_basic_numbers(self, spoken, expected):
        assert normalize_spoken_numbers(spoken) == expected

    def test_niner(self):
        assert normalize_spoken_numbers("niner") == "9"

    def test_oh_as_zero(self):
        assert normalize_spoken_numbers("oh five") == "05"

    def test_mixed_with_words(self):
        result = normalize_spoken_numbers("torque at twenty five inch pounds")
        assert result == "torque at 25 inch pounds"

    def test_no_numbers(self):
        assert normalize_spoken_numbers("hello world") == "hello world"

    def test_multiple_number_groups(self):
        result = normalize_spoken_numbers("from one two to three four")
        assert result == "from 12 to 34"

    def test_point_without_following_digit(self):
        result = normalize_spoken_numbers("two point")
        # "point" without following digit word should be kept as-is
        assert "2" in result


# ---------- Registration ----------

class TestRegistration:
    def test_n_number_spoken(self):
        assert normalize_registration("november one two three") == "N123"

    def test_n_number_with_suffix(self):
        assert normalize_registration("november one two three alpha bravo") == "N123AB"

    def test_vt_registration(self):
        result = normalize_registration("victor tango alpha bravo charlie")
        assert result == "VT-ABC"

    def test_tail_number_prefix(self):
        result = normalize_registration("tail number november one two three")
        assert result == "N123"

    def test_tail_prefix_without_number(self):
        result = normalize_registration("tail november four five six")
        assert result == "N456"

    def test_vt_format(self):
        result = normalize_registration("victor tango india november delta")
        assert result == "VT-IND"


# ---------- ATA Chapter ----------

class TestAtaChapter:
    @pytest.mark.parametrize("text,code,name", [
        ("ATA 72", "72", "Engine"),
        ("ata 72", "72", "Engine"),
        ("chapter 72", "72", "Engine"),
        ("ATA 27", "27", "Flight Controls"),
        ("ATA 32", "32", "Landing Gear"),
        ("ATA 28", "28", "Fuel"),
    ])
    def test_numeric_ata(self, text, code, name):
        result = normalize_ata_chapter(text)
        assert result is not None
        assert result == (code, name)

    def test_spoken_number_ata(self):
        result = normalize_ata_chapter("ATA seven two")
        assert result == ("72", "Engine")

    def test_chapter_spoken(self):
        result = normalize_ata_chapter("chapter two seven")
        assert result == ("27", "Flight Controls")

    def test_no_ata(self):
        assert normalize_ata_chapter("hello world") is None

    def test_unknown_chapter(self):
        assert normalize_ata_chapter("ATA 99") is None


# ---------- Part Numbers ----------

class TestPartNumber:
    def test_ms_with_spoken_numbers(self):
        result = normalize_part_number("MS two nine five one three dash zero one two")
        assert result == "MS29513-012"

    def test_nato_prefix(self):
        result = normalize_part_number("mike sierra two niner five one three")
        assert result == "MS29513"

    def test_an_prefix(self):
        result = normalize_part_number("AN three six zero dash five")
        assert result == "AN360-5"

    def test_nas_prefix(self):
        result = normalize_part_number("NAS one four two eight")
        assert result == "NAS1428"

    def test_already_formatted(self):
        result = normalize_part_number("MS29513-012")
        assert result == "MS29513-012"


# ---------- Units ----------

class TestUnits:
    @pytest.mark.parametrize("spoken,expected", [
        ("inch pounds", "in-lbs"),
        ("foot pounds", "ft-lbs"),
        ("inches", "in"),
        ("millimeters", "mm"),
        ("newton meters", "Nm"),
    ])
    def test_unit_conversions(self, spoken, expected):
        assert normalize_units(spoken) == expected

    def test_psi_stays(self):
        assert normalize_units("PSI") == "PSI"

    def test_case_insensitive(self):
        assert normalize_units("Inch Pounds") == "in-lbs"

    def test_in_sentence(self):
        result = normalize_units("torque at 25 inch pounds")
        assert result == "torque at 25 in-lbs"


# ---------- Full Transcript ----------

class TestFullTranscript:
    def test_complete_spoken_log(self):
        transcript = (
            "On tail november one two three number two engine "
            "ATA seven two found oil residue around the number four bearing "
            "torque on the B-nut was below spec at twenty five inch pounds"
        )
        result = normalize_full_transcript(transcript)
        # NATO "november" -> "N", numbers "one two three" -> "123" (separate tokens)
        assert "N" in result
        assert "123" in result
        assert "25" in result
        assert "in-lbs" in result
        assert "72" in result

    def test_extra_whitespace(self):
        result = normalize_full_transcript("  alpha   bravo   charlie  ")
        assert result == "ABC"

    def test_empty(self):
        assert normalize_full_transcript("") == ""

    def test_no_special_content(self):
        assert normalize_full_transcript("the sky is blue") == "the sky is blue"

    def test_mixed_nato_and_numbers(self):
        result = normalize_full_transcript("part mike sierra two nine five one three")
        assert "MS" in result
        assert "29513" in result
