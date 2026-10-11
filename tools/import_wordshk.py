#!/usr/bin/env python3
"""Import the three public-domain words.hk exports without article text or examples.

The source pages distinguish these exports from the full dictionary and articles.
Weights are bounded ranking priors, not sentence probabilities or chat frequencies.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = '# words.hk public-domain supplement; see licenses/wordshk/SOURCE.json.'
EXPECTED = {
    'charcount.json': 'c0bf3bfebcf77b152626d132208b9262cb103510a9fb30b246c4e6eafecadba3',
    'existingwordcount.json': '9067db92fa1f1002e498ea59dcb831f559d62fa6d4855191976f1a4159d46bbd',
    'wordslist.json': '0ea376604451f43401b4b6e574cea28c63d4dedd4aaf5b32e86f920382969886',
}


def han(cp):
    return any(lo <= ord(cp) <= hi for lo, hi in (
        (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
        (0x20000, 0x2A6DF), (0x2A700, 0x2EE5F), (0x2F800, 0x2FA1F),
        (0x30000, 0x3347F)))


def base_text(path):
    return path.read_text(encoding='utf-8').split(MARKER, 1)[0].rstrip() + '\n'


def load(path):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if EXPECTED and digest != EXPECTED[path.name]:
        raise ValueError('Unexpected words.hk snapshot: ' + path.name)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object: ' + path.name)
    return data, digest


def import_data(chars_path, counts_path, words_path, assets):
    chars, char_sha = load(chars_path)
    counts, count_sha = load(counts_path)
    words, word_sha = load(words_path)
    for values in (chars, counts):
        if any(type(v) is not int or v < 0 for v in values.values()):
            raise ValueError('Frequency values must be non-negative integers')
    if any(not isinstance(v, list) or not all(isinstance(p, str) for p in v) for v in words.values()):
        raise ValueError('Unexpected word-list format')
    reverse = {}
    for line in (assets / 'cangjie5.base.dict.yaml').read_text(encoding='utf-8').splitlines():
        f = line.split('\t')
        if len(f) >= 2 and len(f[0]) == 1 and re.fullmatch('[a-z]{1,5}', f[1]):
            code = f[1] if len(f[1]) == 1 else f[1][0] + f[1][-1]
            reverse.setdefault(f[0], set()).add(code)
    target = assets / 'cantonese_phrases.tsv'
    original = base_text(target)
    existing = {}
    for filename in ('quick_phrases.tsv', 'hk_phrases.tsv', 'cantonese_phrases.tsv'):
        for line in base_text(assets / filename).splitlines():
            f = line.split('\t')
            if len(f) == 3 and not line.startswith('#'):
                existing[f[0], f[1]] = max(existing.get((f[0], f[1]), 0), int(f[2]))
    additions, imported, reasons = {}, {}, Counter()
    for word in sorted(words):
        if not 2 <= len(word) <= 8:
            reasons['outside_2_to_8_characters'] += 1
            continue
        if not all(han(c) for c in word):
            reasons['mixed_text_or_variant_marker'] += 1
            continue
        if not all(c in reverse for c in word):
            reasons['missing_existing_character_code'] += 1
            continue
        observed = counts.get(word, 0)
        # Counts reflect an unsegmented written corpus, not current HK chat usage.
        priority = min(3000, max(10, observed * 30))
        imported[word] = observed
        variants = [sorted(reverse[c], key=lambda s: (-len(s), s)) for c in word]
        for parts in itertools.islice(itertools.product(*variants), 8):
            key = (''.join(parts), word)
            if priority > existing.get(key, 0):
                additions[key] = (priority, observed)
            elif observed > 0:
                # Keep corpus evidence even when an older dictionary weight is
                # higher. The fourth field is an observed occurrence count.
                additions[key] = (priority, observed)
    target.write_text(original + '\n' + MARKER + '\n' + ''.join(
        f'{code}\t{word}\t{priority}\t{observed}\n'
        for (code, word), (priority, observed) in sorted(additions.items())), encoding='utf-8')

    target = assets / 'character_frequencies.tsv'
    original = base_text(target)
    base = dict((f[0], int(f[1])) for line in original.splitlines()
                if not line.startswith('#') and len(f := line.split('\t')) == 2)
    usable = {c: n for c, n in chars.items() if len(c) == 1 and han(c) and c in reverse and n > 0}
    scale = sum(base.get(c, 1) for c in usable) / sum(usable.values())
    adjusted = {}
    for c, n in sorted(usable.items()):
        old = max(1, base.get(c, 1))
        # A 15% log blend, limited to +/-30% per character. Missing observations
        # never penalize names/rare characters or remove a dictionary entry.
        delta = max(-math.log(1.3), min(math.log(1.3), .15 * math.log(max(1, n * scale) / old)))
        updated = max(1, round(old * math.exp(delta)))
        if updated != old:
            adjusted[c] = updated
    target.write_text(original + '\n' + MARKER + '\n' + ''.join(
        f'{c}\t{n}\n' for c, n in sorted(adjusted.items())), encoding='utf-8')
    manifest = {
        'source_page': 'https://words.hk/faiman/analysis/',
        'license': 'Public domain, explicitly stated for these three datasets on the supplied source page',
        'credit': 'words.hk 粵典',
        'snapshot_received': '2026-10-11',
        'exports': {name: {'url': 'https://words.hk/faiman/analysis/' + name, 'sha256': sha, 'entries': len(data)}
                    for name, sha, data in [('charcount.json', char_sha, chars),
                        ('existingwordcount.json', count_sha, counts), ('wordslist.json', word_sha, words)]},
        'selected_words': len(imported),
        'new_vocabulary_words': len(set(imported) - {word for code, word in existing}),
        'observed_selected_words': sum(n > 0 for n in imported.values()),
        'supplemental_exact_code_rows': len(additions),
        'additional_or_increased_exact_code_rows': sum(priority > existing.get(key, 0)
            for key, (priority, observed) in additions.items()),
        'usable_character_counts': len(usable), 'adjusted_character_weights': len(adjusted),
        'excluded_words': dict(sorted(reasons.items())),
        'word_transform': 'Pure Han 2-8 characters with existing codes; at most eight exact Quick code variants, two-code roots first; weight=max(10,min(3000,30*observed_count)); existing stronger weights retained; fourth column preserves observed corpus count for independent bounded phrase evidence',
        'corpus_evidence_transform': 'For observed 2-4 character words, evidence=.75*(length-1)*min(1,log(1+count)/log(301)) at the completed suffix across token boundaries; fuse with existing phrase evidence using max, not sum, to avoid double-counting overlapping corpora; duplicate code variants use max; existing combined lexical evidence cap of 4 per character retained',
        'character_transform': 'Normalize corpus counts to existing overlapping character total; 15% log blend, per-character ratio limited to [1/1.3,1.3]; absent counts leave original weights unchanged; HK-common runtime floor retained',
        'limitations': ['Word occurrences are counted without segmentation; overlapping words may be double-counted.',
            'Words missing from the corpus have no measured frequency, not zero validity.',
            'No article bodies, full dictionary definitions/examples, personal text, or evaluation sentences imported.',
            'Jyutping is not a Cangjie/Quick code source; existing character codes alone supply every imported code.']}
    directory = assets / 'licenses/wordshk'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'SOURCE.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('charcount', type=Path)
    parser.add_argument('existingwordcount', type=Path)
    parser.add_argument('wordslist', type=Path)
    parser.add_argument('--assets', type=Path, default=ROOT / 'app/src/main/assets')
    args = parser.parse_args()
    import_data(args.charcount, args.existingwordcount, args.wordslist, args.assets)
