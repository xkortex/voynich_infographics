"""Shared EVA parsing conventions. No I/O or argument parsing on import.

The frequency chart retains readable spans. Word-based charts reject an entire
uncertain word. Keep these policies separate: they intentionally yield different totals.
"""

import re

LETTERS = tuple("abcdefghijklmnopqrstuvxyz")
GROUPED_FORMS = ("cfh", "ckh", "cph", "cth", "ch", "sh")
GROUP_PATTERN = re.compile("|".join(GROUPED_FORMS) + r"|[a-vxyz]")
LOCUS_PATTERN = re.compile(r"^<f[^>]*\.[^>]*>\s*(.*)")


def iter_text_loci(transcription):
    """Yield IVTFF text-locus content, excluding comments and page headers."""
    for line in transcription.splitlines():
        match = LOCUS_PATTERN.match(line)
        if match:
            yield match.group(1)


def readable_words(transcription):
    """Keep only complete basic-EVA words; reject uncertain/extended material."""
    words = []
    for locus in iter_text_loci(transcription):
        content = re.sub(r"<[^>]*>", "", locus).lower()
        for candidate in re.split(r"[.,\s\-=]+", content):
            candidate = candidate.replace("{", "").replace("}", "")
            if candidate and re.fullmatch("[a-vxyz]+", candidate):
                words.append(candidate)
    return words


def tokenize(word, mode="groups"):
    """Use longest-match groups, or individual transliteration letters."""
    return GROUP_PATTERN.findall(word) if mode == "groups" else list(word)


def readable_spans(transcription):
    """Return readable segments and a count of omitted ambiguity/rare markers."""
    segments = []
    locus_count = alternative_count = rare_count = 0
    for locus in iter_text_loci(transcription):
        locus_count += 1
        content = re.sub(r"<[^>]*>", " ", locus)
        alternative_count += len(re.findall(r"\[[^\]]*\]", content))
        content = re.sub(r"\[[^\]]*\]", " ", content)
        rare_count += len(re.findall(r"@\d+;", content))
        content = re.sub(r"@\d+;", " ", content)
        content = content.replace("{", "").replace("}", "").lower()
        segments.extend(re.findall("[a-vxyz]+", content))
    return segments, locus_count, alternative_count, rare_count
