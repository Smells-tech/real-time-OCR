import re

from spellchecker import SpellChecker
import Levenshtein
from Bio import Align

from lib import *

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
    def __init__(self, custom_vocab=None, ocr_corrections=DEFAULT_CORRECTIONS):
        # Initialize spell checker with optional custom vocabulary
        self.spell = SpellChecker()
        if custom_vocab:
            self.spell.word_frequency.load_words(custom_vocab)

        # Common OCR misread characters mapping
        self.ocr_corrections = ocr_corrections

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
        correct = word in self.spell or word.lower() in self.spell # 2 lookups? Does casing really matter for this dictionary lookup?
        self._cache[word] = correct
        return correct

    def choose_better_word(self, w1, w2):
        # Pre-correct OCR errors
        if self.ocr_corrections is not None:
            w1 = self.correct_ocr_errors(w1)
            w2 = self.correct_ocr_errors(w2)

        # Check correctness
        w1_correct = self.is_word_correct(w1)
        w2_correct = self.is_word_correct(w2)

        # Priority: both correct → choose shorter edit distance to original
        # one correct → choose correct
        # none correct → choose word with smaller edit distance to dictionary suggestion

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

            # Compute edit distances
            dist_w1 = Levenshtein.distance(w1, w1_suggestion) if w1_suggestion else float('inf')
            dist_w2 = Levenshtein.distance(w2, w2_suggestion) if w2_suggestion else float('inf')

            if dist_w1 < dist_w2:
                return w1_suggestion or w1
            else:
                return w2_suggestion or w2

    def merge_aligned_words(self, words1, words2):

        if len(words1) != len(words2):
            raise ValueError("Aligned strings must have the same number of words")

        merged_words = []
        for w1, w2 in zip(words1, words2):
            if w1 == w2:
                merged_words.append(w1)
            else:
                better_word = self.choose_better_word(w1, w2)
                merged_words.append(better_word)

        return merged_words

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

def word_distance(w1, w2):
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

def align_sequences(str1, str2, mode='global', match_score=2, mismatch_score=-1, open_gap_score=-.5, extend_gap_score=-.1):
    m, n = len(str1), len(str2)

    best_score = 0
    best_overlap = 0

    aligner = Align.PairwiseAligner(mode=mode, match_score=match_score, mismatch_score=mismatch_score)
    aligner.open_gap_score = open_gap_score
    aligner.extend_gap_score = extend_gap_score
    aligner.target_end_gap_score = 0.0
    aligner.query_end_gap_score = 0.0
    norm = max(m, n) * aligner.match_score

    alignments = aligner.align(str1, str2)

    print(f"Alignments:\t{len(alignments):>15}")
    stores = []
    amalgamations = []
    residues = []
    for alignment in alignments:
        print(f"Score: \t{alignment.score/norm:>15}")
        indices1, indices2 = alignment.indices
        blocks1, blocks2 = alignment.aligned

        # Non-overlapping prefix
        start1 = blocks1[0, 0]
        store = str1[:start1]
        stores.append(store)

        # Non-overlapping suffix
        fin2 = blocks2[-1, -1]
        residue = str2[fin2:]
        residues.append(residue)

        # Array of possible amalgamations
        amalgamations = [""]

        # Build set of possible amalgamations
        for i1, i2 in zip(indices1, indices2):
            if i1<start1 or i2>fin2:
                continue # Only take aligned regions
            for a, amalg in enumerate(amalgamations.copy()):
                if i1>=0:
                    if i2>=0:
                        if str1[i1] != str2[i2]:
                            amalgamations.append(amalg + str2[i2])
                    amalgamations[a] = amalg + str1[i1]
                elif i2>=0:
                    amalgamations[a] = amalg + str2[i2]

            # for i, j in zip(*alignment.aligned):
                # amalg1 = amalg1 + str1[slice(*i)]
                # amalg2 = amalg2 + str2[slice(*j)]

        print("Store", "\n", store, end='\n')
        pass
        for i, amalg in enumerate(amalgamations):
            print(f"Amalgamation {i+1}/{len(amalgamations)}", "\n", amalg, end='\n')
            pass
        print("Residue", "\n", residue, end='\n')
        pass

    return best_overlap, best_score

# def align_sorta_overlapping_words(words1, words2, max_error=.05):

#     max_overlap = min(len(words1), len(words2))
#     if max_overlap == 0:
#         return 0, None

#     rng = range(max_overlap, 0, -1)
#     distances = []
#     for overlap_len in rng:
#         block1 = words1[-overlap_len:]
#         block2 = words2[:overlap_len]
#         dist = sum(word_distance(w1, w2) for w1, w2 in zip(block1, block2))
#         if dist == 0:
#             # Exact match, early return
#             return overlap_len, None
#         distances.append(dist)

#     # Find best match
#     i = distances.index(min(distances))
    # overlap_len = rng[i]

#     # TODO: Write an error check function that uses words instead of strings
#     str1 = ' '.join(words1[-overlap_len:])
#     dist = distances[i]
#     if dist>max_error:
#         print('\n'*100)
#         print(f"Store:\n\n{words1[:-overlap_len]}", end="\n\n")
#         print(f"Storeblock:\n\n{words1[-overlap_len:]}", end="\n\n")
#         print(f"Textblock:\n\n{words2[:overlap_len]}", end="\n\n")
#         print(f"Residual:\n\n{words2[overlap_len:]}", end="\n\n")
#         print(f"Abort merger, maximum error of {max_error*100}% exceeded")
#         print(f"Overlap is             \t{str(overlap_len)}")
#         print(f"Amalgamation length is \t{len(str1)}")
#         print(f"distance is            \t{dist}")
#         input(f"Press enter to continue")
#         return 0, None

#     return overlap_len, dist
