import re

from spellchecker import SpellChecker
import Levenshtein
from Bio import Align

from controls import *
from timer import tracker

DEFAULT_CORRECTIONS = {
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

class OCRMerger:
    def __init__(self, custom_vocab=None, ocr_corrections=DEFAULT_CORRECTIONS, language='nl'):
        # Initialize spell checker with optional custom vocabulary
        self.spell = SpellChecker(language=language)
        if custom_vocab:
            self.spell.word_frequency.load_words(custom_vocab)

        # Common OCR misread characters mapping
        self.ocr_corrections = ocr_corrections

        # Cache for spell check results
        self._cache = {}

    def correct_ocr_errors(self, word:str):
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

    def is_word_correct(self, word:str):
        # Check cache first
        if word in self._cache:
            return self._cache[word]
        # Check if word is known or can be corrected by spellchecker
        correct = word in self.spell or word.lower() in self.spell # 2 lookups? Does casing really matter for this dictionary lookup?
        self._cache[word] = correct
        return correct

    def choose_better_word(self, w1:str, w2:str):
        # Pre-correct OCR errors
        if self.ocr_corrections is not None:
            w1 = self.correct_ocr_errors(w1)
            w2 = self.correct_ocr_errors(w2)

        # Check correctness
        w1_correct = self.is_word_correct(w1)
        w2_correct = self.is_word_correct(w2)

        if w1_correct and not w2_correct:
            return w1
        elif w2_correct and not w1_correct:
            return w2
        elif w1_correct and w2_correct:
            # Both correct, choose the one closer to original (or arbitrarily w1)
            return w1
        else:
            # Neither correct, try to get best candidate from spell checker
            w1_suggestion = self.spell.correction(w1)
            w2_suggestion = self.spell.correction(w2)

            dist_w1 = Levenshtein.distance(w1, w1_suggestion) if w1_suggestion else float('inf')
            dist_w2 = Levenshtein.distance(w2, w2_suggestion) if w2_suggestion else float('inf')

            if dist_w1 < dist_w2:
                return w1_suggestion or w1
            else:
                return w2_suggestion or w2

    def correction(self, string:str):
        """Correct words in the given string."""
        # Split into words, keep newlines
        words = split_keep_newlines(string)

        # Correct each word
        for i, w in enumerate(words):
            corr = self.spell.correction(w)
            if corr:
                words[i] = corr

        # Join with newlines
        return join_with_newlines(words)

    def choose_best_word_among(self, *words:str):
        """
        Given a list of words (strings), pick the best one using pairwise comparisons.
        """
        # Filter unique entries
        words = list(set(words))

        # If all words are identical, just return one
        if len(words) == 1:
            return words[0]

        # Iteratively pick best word by pairwise comparison
        best_word = words[0]
        for w in words[1:]:
            best_word = self.choose_better_word(best_word, w)
        return best_word

    def merge_aligned_words(self, *word_lists:list[str]):
        """
        Merge any number of aligned word sequences.
        All sequences must have the same length.
        """
        if not word_lists:
            return []

        length = len(word_lists[0])
        for wl in word_lists:
            if len(wl) != length:
                raise ValueError("All aligned sequences must have the same length")

        merged_words = []
        for i in range(length):
            candidates = [wl[i] for wl in word_lists]
            # If all candidates are identical, no need to choose
            if len(set(candidates)) == 1:
                merged_words.append(candidates[0])
            else:
                best_word = self.choose_best_word_among(*candidates)
                merged_words.append(best_word)

        return merged_words

    def align_sequences(self, str1:str, str2:str, mode='global', match_score=2, mismatch_score=-1, open_gap_score=-.5, extend_gap_score=-.1, max_alignments=1):

        tracker.start('align_sequences: Prep')

        Aligner = Align.PairwiseAligner(mode=mode, match_score=match_score, mismatch_score=mismatch_score)
        Aligner.open_gap_score = open_gap_score
        Aligner.extend_gap_score = extend_gap_score
        Aligner.target_end_gap_score = 0.0
        Aligner.query_end_gap_score = 0.0

        alignments = Aligner.align(str1, str2)

        variants = []

        tracker.stop('align_sequences: Prep')

        for alignment in alignments:

            tracker.start('align_sequences: Alignment prep')

            indices1, indices2 = alignment.indices
            blocks1, blocks2 = alignment.aligned

            # Non-overlapping prefix
            start1 = blocks1[0, 0]
            words = split_keep_newlines(str1[:start1])

            # Non-overlapping suffix
            fin2 = blocks2[-1, -1]
            residue = split_keep_newlines(str2[fin2:])

            # Build set of possible amalgamations
            amalgamations = [""] # Start with a single branch

            tracker.stop('align_sequences: Alignment prep')
            tracker.start('align_sequences: Construct amalgamations')

            for i1, i2 in zip(indices1, indices2):
                if i1<start1 or i2>fin2:
                    continue # Only take aligned regions
                for a, amalg in enumerate(amalgamations.copy()):
                    if i1>=0:
                        if i2>=0:
                            if str1[i1] != str2[i2]:
                                amalgamations.append(amalg + str2[i2]) # 2 options, add branch
                        amalgamations[a] = amalg + str1[i1]
                    elif i2>=0:
                        amalgamations[a] = amalg + str2[i2]

            tracker.stop('align_sequences: Construct amalgamations')
            tracker.start('align_sequences: Merge amalgamations')

            # Choose best set of words
            amalgamations = [split_keep_newlines(a) for a in amalgamations]
            prime_amalgamation = [self.choose_best_word_among(*w) for w in zip(*amalgamations)]

            words.extend(prime_amalgamation)
            words.extend(residue)
            variants.append(words)

            tracker.stop('align_sequences: Merge amalgamations')

            if len(variants) >= max_alignments:
                break

        assert all(len(v) == len(variants[0]) for v in variants), "Variants must all have equal word count"

        tracker.start('align_sequences: Merge variants')

        prime_amalgamation = join_with_newlines([self.choose_best_word_among(*w) for w in zip(*variants)])

        tracker.stop('align_sequences: Merge variants')

        return prime_amalgamation

def split_keep_newlines(text: str) -> list[str]:
    # This regex matches either sequences of non-whitespace except newline OR a newline character
    pattern = r'[^\s\n]+|\n'
    return re.findall(pattern, text)

def join_with_newlines(words: list[str]) -> str:
    if not words:
        return ''

    result = [words[0]]
    for prev, curr in zip(words, words[1:]):
        if prev == '\n' or curr == '\n':
            # No space around newlines
            result.append(curr)
        else:
            # Add space between words
            result.append(' ' + curr)
    return ''.join(result)

def fuzzy_contains(body, target, max_error=1):
    """
    Returns True if str2 is found within str1 allowing up to max_error
    (insertions, deletions, substitutions) in the match, else False.
    """
    # Build a fuzzy regex pattern for str2 allowing up to max_error
    # (?e) enables fuzzy matching, {e<=max_error} limits errors

    body = ' '.join(body)
    target = ' '.join(target)

    pattern = f'(?e){regex.escape(target)}{{e<={max_error}}}'

    # Search for fuzzy match anywhere in str1
    match = regex.search(pattern, body)
    return match is not None

def word_distance(w1:str, w2:str):
    # Normalized Levenshtein distance between two words
    max_len = max(len(w1), len(w2))
    if max_len == 0:
        return 0
    return Levenshtein.distance(w1, w2) / max_len

def needleman_wunsch(seq1, seq2, gap_penalty):
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize dp matrix
    for i in range(1, m + 1):
        dp[i][0] = i * gap_penalty
    for j in range(1, n + 1):
        dp[0][j] = j * gap_penalty

    # Fill dp matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost_sub = dp[i - 1][j - 1] + word_distance(seq1[i - 1], seq2[j - 1])
            cost_del = dp[i - 1][j] + gap_penalty
            cost_ins = dp[i][j - 1] + gap_penalty
            dp[i][j] = min(cost_sub, cost_del, cost_ins)

    return dp[m][n]

def align_sequences_nw(words1, words2, gap_penalty=1, max_error=0.1):
    m, n = len(words1), len(words2)

    best_score = float('inf')
    best_overlap = 0

    for overlap_len in range(1, min(m, n) + 1):
        suffix = words1[m - overlap_len:]
        prefix = words2[:overlap_len]

        # NW expects sequences as strings or lists
        # Compute alignment distance with gap penalty
        dist = needleman_wunsch(suffix, prefix, gap_penalty)

        # Normalize distance by overlap length
        norm_dist = dist / overlap_len

        if norm_dist < best_score:
            best_score = norm_dist
            best_overlap = overlap_len

    if best_score > max_error:
        # No good overlap found, treat as no overlap
        return 0, None

    return best_overlap, best_score
