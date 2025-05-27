import re

from spellchecker import SpellChecker
import Levenshtein


from lib import *

class OCRMerger:
    def __init__(self, custom_vocab=None):
        # Initialize spell checker with optional custom vocabulary
        self.spell = SpellChecker()
        if custom_vocab:
            self.spell.word_frequency.load_words(custom_vocab)

        # Common OCR misread characters mapping
        self.ocr_corrections = {
            '0': 'O',  # zero to capital O
            '1': 'I',  # one to capital I
            '5': 'S',
            '6': 'G',
            '8': 'B',
            '@': 'a',
            '$': 'S',
            '©': 'c',
            '€': 'E',
            # Add more based on your data
        }

        # Cache for spell check results
        self._cache = {}

    def correct_ocr_errors(self, word):
        # Detect capitalization pattern
        if word.isupper():
            cap_type = 'upper'
        elif word.istitle():
            cap_type = 'title'
        else:
            cap_type = 'lower'

        # Convert to lowercase for uniform correction
        word_lower = word.lower()

        # Apply OCR character corrections on lowercase word
        corrected_chars = []
        for ch in word_lower:
            corrected_chars.append(self.ocr_corrections.get(ch, ch))
        corrected_word = ''.join(corrected_chars).lower()

        # Restore original capitalization pattern
        if cap_type == 'upper':
            return corrected_word.upper()
        elif cap_type == 'title':
            return corrected_word.capitalize()
        else:
            return corrected_word

    def is_word_correct(self, word):
        # Check cache first
        if word in self._cache:
            return self._cache[word]
        # Check if word is known or can be corrected by spellchecker
        correct = word in self.spell or word.lower() in self.spell
        self._cache[word] = correct
        return correct

    def choose_better_word(self, w1, w2):
        # Pre-correct OCR errors
        w1_corr = self.correct_ocr_errors(w1)
        w2_corr = self.correct_ocr_errors(w2)

        # Check correctness
        w1_correct = self.is_word_correct(w1_corr)
        w2_correct = self.is_word_correct(w2_corr)

        # Priority: both correct → choose shorter edit distance to original
        # one correct → choose correct
        # none correct → choose word with smaller edit distance to dictionary suggestion

        if w1_correct and not w2_correct:
            return w1_corr
        elif w2_correct and not w1_correct:
            return w2_corr
        elif w1_correct and w2_correct:
            # Both correct, choose the one closer to original (or arbitrarily w1)
            return w1_corr
        else:
            # Neither correct, try to get best candidate from spell checker
            w1_suggestion = self.spell.correction(w1_corr)
            w2_suggestion = self.spell.correction(w2_corr)

            # Compute edit distances
            dist_w1 = Levenshtein.distance(w1_corr, w1_suggestion) if w1_suggestion else float('inf')
            dist_w2 = Levenshtein.distance(w2_corr, w2_suggestion) if w2_suggestion else float('inf')

            if dist_w1 < dist_w2:
                return w1_suggestion or w1_corr
            else:
                return w2_suggestion or w2_corr

    def align_overlapping_strings(str1, str2):
        """Removes any overlap and returns the merged string"""
        min_overlap_len = min(len(str1), len(str2))
        for i in range(min_overlap_len, 0, -1):
            if str1.endswith(str2[:i]):
                return i
        return 0

    def align_sorta_overlapping_strings(str1, str2, max_errors=1):
        """
        Removes overlap between str1 and str2 allowing up to max_errors
        (insertions, deletions, substitutions) in the overlapping part,
        then merges and returns the combined string.
        """
        min_len = min(len(str1), len(str2))

        # Try from longest possible overlap to shortest
        for overlap_len in range(min_len, 0, -1):
            # Extract the candidate overlap parts
            suffix = str1[-overlap_len:]
            prefix = str2[:overlap_len]

            # Build fuzzy regex pattern for prefix allowing max_errors
            # (?e) enables fuzzy matching, {e<=max_errors} limits errors
            pattern = f'(?e)^{regex.escape(prefix)}{{e<={max_errors}}}$'

            # Check if suffix matches prefix fuzzily within allowed errors
            if regex.match(pattern, suffix):
                # Merge by removing the overlapping part from str2
                return str2[overlap_len:]

        # No fuzzy overlap found, return concatenation
        return overlap_len

    def merge_aligned_strings(self, str1, str2):
        # Split into words (assuming perfect alignment)
        # TODO: OCR might miss whitespaces, instead of using .split()
        # apply a method that processes the entire string one word at a time
        # Perhaps combining alignment, correction & merger all in one loop?
        words1 = str1.split()
        words2 = str2.split()

        if len(words1) != len(words2):
            raise ValueError("Aligned strings must have the same number of words")

        merged_words = []
        for w1, w2 in zip(words1, words2):
            if w1 == w2:
                merged_words.append(w1)
            else:
                better_word = self.choose_better_word(w1, w2)
                merged_words.append(better_word)

        return ' '.join(merged_words)

# Example usage
if __name__ == "__main__":
    custom_vocab = ['PubMed', 'NaN']  # Add domain-specific terms here
    merger = OCRMerger(custom_vocab=custom_vocab)

    s1 = "Th1s is a samp1e text with OCR err0rs"
    s2 = "This is a sample text with OCR errors"

    merged = merger.merge_aligned_strings(s1, s2)
    print("Merged:", merged)
