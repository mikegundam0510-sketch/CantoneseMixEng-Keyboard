#!/usr/bin/env python3
"""Retrain the existing KLM2/WLM1 models from pinned, boundary-safe TRAIN text.

Writes research assets only. No evaluation decoding, vocabulary generation,
historical-particle guesses or runtime source changes are performed here.
"""
import argparse
import base64
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zipfile

from prepare_clean_ranking import rules, spans
from prepare_phrase_relations import gram_index, overlap
from prepare_tatoeba_corpus import digest, load_training
from train_language_model import key
from sentence_features import han
from train_phrase_model import ROOT, ASSETS, scenarios

DATA = ROOT / 'tools/data/clean_language_models'
MODEL = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
PHRASE = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def evaluation_exclusions(mapping):
    """Known evaluation inputs only; historical TRAIN pairs are not test labels."""
    paths = json.loads((ROOT/'tools/data/joint_ranking/manifest.json').read_text())['known_input_sha256']
    names = {name for name in paths if name.endswith('.tsv')
             and not any(part in Path(name).name for part in ('train','pairs'))}
    names.update('tools/data/joint_ranking/'+split+'.tsv' for split in ('validation','heldout'))
    texts, hashes = set(), {}
    for name in sorted(names):
        path = ROOT/name; hashes[name] = digest(path)
        for line in path.read_text().splitlines():
            if line.startswith(('#','train:')): continue
            for text in line.split('\t'):
                if len(text)>=6 and all(han(c) for c in text):
                    texts.add(text)
                    texts.update(t for _,_,t,_ in spans(text,mapping) if len(t)>=6)
    return gram_index(texts), hashes


def hk_utterances(source, allowed):
    """Preserve every token, including spaced English and missing-speech markers."""
    with zipfile.ZipFile(source) as archive:
        for name in sorted(allowed):
            tokens, index = [], 0
            for line in archive.read(name).decode('utf-8-sig').splitlines() + ['<sent>']:
                match = re.fullmatch(r'\s*([^/<>]+?)/([^/]+)/([^/]*)/\s*', line)
                if match:
                    tokens.append(match[1].strip())
                elif '/' in line and not line.lstrip().startswith('<'):
                    if any('\u3400' <= c <= '\u9fff' or '\U00020000' <= c <= '\U0003134f' for c in line):
                        raise ValueError('Unparsed Han token: ' + name)
                    tokens.append(line.strip())
                elif '</sent_tag>' in line or '<sent>' in line:
                    if tokens:
                        yield name, index, tokens
                        index += 1
                        tokens = []


def token_spans(tokens, mapping):
    """Keep original word boundaries and code-point offsets inside each Han span."""
    original = ''.join(tokens)
    offsets, at = [], 0
    for token in tokens:
        offsets.append((at, at + len(token)))
        at += len(token)
    for start, end, text, changes in spans(original, mapping):
        words = []
        for left, right in offsets:
            a, b = max(start, left), min(end, right)
            if a < b:
                part = list(spans(original[a:b], mapping))
                if len(part) != 1 or part[0][:2] != (0, b-a):
                    raise ValueError('Token normalization changed a span boundary')
                words.append(part[0][2])
        if ''.join(words) != text:
            raise ValueError('Segmented word/character text mismatch')
        yield original, start, end, text, words, changes


def prepare(hk, output):
    if output.resolve() == ASSETS.resolve() or any((output/n).exists() for n in ('corpus.jsonl.gz', 'manifest.json')):
        raise ValueError('Use a fresh research output directory')
    if digest(hk) != MODEL['source_sha256']['hkcancor_zip']:
        raise ValueError('HKCanCor source changed')
    mapping = rules()
    excluded, inputs = evaluation_exclusions(mapping)
    tt, tt_manifest = load_training(ROOT / 'tools/data/tatoeba_corpus')
    allowed = set(PHRASE['training_conversation_files'])
    rejected, records = Counter(), []
    for name, utterance, tokens in hk_utterances(hk, allowed):
        for original, start, end, text, words, changes in token_spans(tokens, mapping):
            if overlap(text, excluded):
                rejected['HK_evaluation_overlap'] += 1
                continue
            records.append(dict(domain='HK', family=name, origin=dict(file=name, utterance=utterance),
                original=original, start=start, end=end, text=text, words=words, changes=changes))
    # Reject the complete translation family if any member overlaps an evaluation.
    families = defaultdict(list)
    for row in tt:
        families[str(row['group'])].append(row)
    for family, rows in sorted(families.items()):
        parts = [(row, list(spans(row['text'], mapping))) for row in rows]
        if any(overlap(text, excluded) for _, items in parts for _, _, text, _ in items):
            rejected['Tatoeba_evaluation_families'] += 1
            continue
        for row, items in parts:
            for start, end, text, changes in items:
                records.append(dict(domain='Tatoeba', family=family,
                    origin=dict(id=str(row['id']), group=family), original=row['text'],
                    start=start, end=end, text=text, words=None, changes=changes))
    authored = defaultdict(list)
    for family, words in scenarios()['train']:
        authored[family].append(words)
    for family, rows in sorted(authored.items()):
        parts = [list(token_spans(words, mapping)) for words in rows]
        if any(overlap(text, excluded) for items in parts for _, _, _, text, _, _ in items):
            rejected['authored_evaluation_families'] += 1
            continue
        for words, items in zip(rows, parts):
            for original, start, end, text, tokens, changes in items:
                records.append(dict(domain='authored', family=family, origin=dict(family=family, tokens=words),
                    original=original, start=start, end=end, text=text, words=tokens, changes=changes))
    output.mkdir(parents=True, exist_ok=True)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records).encode()
    (output/'corpus.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    inputs.update({str(p.relative_to(ROOT)):digest(p) for p in (
        ROOT/'tools/data/tatoeba_corpus/train.jsonl', ROOT/'tools/data/tatoeba_corpus/manifest.json',
        ROOT/'tools/data/hk_chat_scenarios.json', ASSETS/'MODEL_REPORT.json', ASSETS/'PHRASE_MODEL_REPORT.json',
        ROOT/'tools/data/clean_ranking/orthography/rules.json', ROOT/'tools/data/clean_ranking/orthography/HKVariants.txt')})
    manifest = dict(parent_revision='e31fed9', hkcancor_sha256=digest(hk),
        original_training_assets_revision='5885daec1c43d676a525c543c8ab092532cb3150',
        original_training_asset_sha256=MODEL['training_asset_sha256'],
        cantonese_words_sha256=MODEL['source_sha256']['cantonese_words'],
        training_conversations=sorted(allowed), input_sha256=inputs,
        corpus_sha256=digest(output/'corpus.jsonl.gz'), records_by_domain=dict(Counter(r['domain'] for r in records)),
        characters_by_domain={d:sum(len(r['text']) for r in records if r['domain']==d) for d in ('HK','Tatoeba','authored')},
        modified_records=sum(bool(r['changes']) for r in records), modifications=sum(len(r['changes']) for r in records),
        rejected=dict(rejected), tatoeba_license=tt_manifest['license'],
        policy='All lengths and characters admitted; no cold-top24, colloquial-marker or decoder-success filtering. Only original46 HK TRAIN files and frozen Tatoeba/authored TRAIN families. NFC and six reviewed glyph pairs only. All non-Han boundaries reset spans; original HK word boundaries retained. Tatoeba is character-only because it has no verified word segmentation. Exclude known evaluation overlap6+ including normalized forms and untouched reserve500; entire related Tatoeba/authored families rejected on overlap. Pinned external lexical priors are retained separately, not derived from evaluation labels.')
    write_json(output/'manifest.json', manifest)
    print(json.dumps({k:manifest[k] for k in ('records_by_domain','characters_by_domain','modified_records','modifications','rejected')}))


def add_counts(counts, text, weight):
    for n in range(1, 6):
        for at in range(len(text)-n+1):
            counts[n][text[at:at+n]] += weight


def character_model(counts, strength=128):
    thresholds = (0,1,2,2,3,3)
    kept = [{t:c for t,c in counts[n].items() if c >= thresholds[n]} for n in range(6)]
    totals, retained = Counter(), Counter()
    for n in range(2,6):
        for text, count in counts[n].items(): totals[text[:-1]] += count
        for text, count in kept[n].items(): retained[text[:-1]] += count
    total = sum(counts[1].values())
    denominator = total + .5*(len(counts[1])+1)
    unknown = .5/denominator
    if total <= 0: raise ValueError('Empty character model')
    items, strings = {}, {}
    for n in range(1,6):
        for text, count in sorted(kept[n].items()):
            h = key(text)
            if h in strings and strings[h] != text: raise ValueError('Hash collision')
            strings[h] = text
            probability = (count+.5)/denominator if n==1 else count/(totals[text[:-1]]+strength*2**n)
            backoff = 1-retained[text]/(totals[text]+strength*2**(n+1)) if totals[text] else 1
            items[h] = probability, backoff
    payload = struct.pack('>IIIf',0x4b4c4d32,5,len(items),unknown)
    payload += b''.join(struct.pack('>qff',h,p,b) for h,(p,b) in sorted(items.items()))
    return payload, dict(prior_strength=strength, entries=len(items),
        grams_by_order=[len(k) for k in kept[1:]], primitive_array_bytes=16*len(items),
        thresholds=thresholds[1:], character_occurrences=total)


def word_relations(unigrams, pairs, triples):
    total = sum(unigrams.values())
    outgoing, triple_outgoing = Counter(), Counter()
    for (left,right),count in pairs.items(): outgoing[left] += count
    for (one,two,three),count in triples.items(): triple_outgoing[one,two] += count
    relations = {}
    for table, denominators in ((pairs,outgoing),(triples,triple_outgoing)):
        for words,count in sorted(table.items()):
            text = ''.join(words)
            if count < 2 or len(text)>12 or not any(len(w)>1 for w in words): continue
            denominator = denominators[words[0] if len(words)==2 else words[:2]]
            marginal = (unigrams[words[-1]]+.5)/(total+.5*len(unigrams))
            conditional = (count+4*marginal)/(denominator+4)
            value = min(3,max(0,math.log(conditional/marginal)))*count/(count+4)
            if value>.1: relations[text] = max(relations.get(text,0),value)
    return relations


def phrase_model(relations, strength=1):
    trie = {'children':{},'value':0}
    for text,value in sorted(relations.items()):
        node = trie
        for c in reversed(text): node = node['children'].setdefault(ord(c),{'children':{},'value':0})
        node['value'] = value
    nodes = []
    def visit(node):
        node['id'] = len(nodes); nodes.append(node)
        for _,child in sorted(node['children'].items()): visit(child)
    visit(trie)
    edges, records = [], []
    for node in nodes:
        records.append((len(edges),len(node['children']),node['value']))
        edges.extend((c,child['id']) for c,child in sorted(node['children'].items()))
    payload = struct.pack('>IIIIf',0x574c4d31,12,len(nodes),len(edges),strength)
    payload += b''.join(struct.pack('>IIf',*row) for row in records)
    payload += b''.join(struct.pack('>II',*row) for row in edges)
    return payload, dict(strength=strength, relations=len(relations), trie_nodes=len(nodes),
        primitive_array_bytes=12*len(nodes)+8*len(edges)+4*65536)


def fit(data, cantonese, training_assets, output):
    if output.resolve()==ASSETS.resolve() or any((output/n).exists() for n in ('language_model.b64','phrase_model.b64')):
        raise ValueError('Use a fresh research model directory')
    manifest = json.loads((data/'manifest.json').read_text())
    protocol = json.loads((data/'protocol.json').read_text())
    if digest(data/'corpus.jsonl.gz') != manifest['corpus_sha256'] or digest(data/'manifest.json') != protocol['manifest_sha256']:
        raise ValueError('Frozen training corpus changed')
    for name,value in protocol['source_sha256'].items():
        if digest(ROOT/name) != value: raise ValueError('Frozen source changed: '+name)
    for name,value in manifest['input_sha256'].items():
        if digest(ROOT/name) != value: raise ValueError('Pinned input changed: '+name)
    if digest(cantonese) != manifest['cantonese_words_sha256']: raise ValueError('Cantonese lexical source changed')
    for name,value in manifest['original_training_asset_sha256'].items():
        if digest(training_assets/name) != value: raise ValueError('Original lexical prior changed: '+name)
    records = [json.loads(s) for s in gzip.decompress((data/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    mapping = rules(); counts = [Counter() for _ in range(6)]
    written = {}
    for name in ('quick_phrases.tsv','hk_phrases.tsv'):
        for line in (training_assets/name).read_text().splitlines():
            f=line.split('\t')
            if len(f)==3:
                for _,_,text,_ in spans(f[1],mapping): written[text]=max(written.get(text,0),int(f[2]))
    for text,count in sorted(written.items()): add_counts(counts,text,min(12,max(1,int(math.log1p(count)))))
    reverse = set()
    for line in (training_assets/'cangjie5.base.dict.yaml').read_text().splitlines():
        f=line.split('\t')
        if len(f)>=2 and len(f[0])==1 and re.fullmatch('[a-z]{1,5}',f[1]): reverse.add(f[0])
    lexical = set()
    for line in cantonese.read_text().splitlines():
        f=line.split('\t'); text=f[0]
        if len(f)>=2 and 2<=len(text)<=8 and all(c in reverse for c in text):
            lexical.update(t for _,_,t,_ in spans(text,mapping))
    for text in sorted(lexical): add_counts(counts,text,2)
    families = defaultdict(set)
    unigrams,pairs,triples = Counter(),Counter(),Counter()
    authored = defaultdict(lambda:(set(),set(),set()))
    for row in records:
        if row['domain']=='HK':
            add_counts(counts,row['text'],12)
            words=row['words'];unigrams.update(words);pairs.update(zip(words,words[1:]));triples.update(zip(words,words[1:],words[2:]))
        elif row['domain']=='Tatoeba':
            text=row['text']
            families[row['family']].update(text[at:at+n] for n in range(1,6) for at in range(len(text)-n+1))
        elif row['domain']=='authored':
            words=row['words']; tables=authored[row['family']]
            tables[0].update(words);tables[1].update(zip(words,words[1:]));tables[2].update(zip(words,words[1:],words[2:]))
        else: raise ValueError('Unknown corpus domain')
    for grams in families.values():
        for gram in sorted(grams): counts[len(gram)][gram]+=2
    for tables in authored.values():
        for values,table in zip(tables,(unigrams,pairs,triples)): table.update({v:3 for v in values})
    cp,cr = character_model(counts)
    relations = word_relations(unigrams,pairs,triples)
    wp,wr = phrase_model(relations)
    output.mkdir(parents=True,exist_ok=True)
    for name,payload in (('language_model.b64',cp),('phrase_model.b64',wp)):
        (output/name).write_bytes(base64.encodebytes(gzip.compress(payload,mtime=0)))
    report = dict(manifest_sha256=digest(data/'manifest.json'),protocol_sha256=digest(data/'protocol.json'),
        models={n:digest(output/n) for n in ('language_model.b64','phrase_model.b64')},
        character=cr,word=wr,lexical_prior_words=dict(written=len(written),cantonese=len(lexical)),
        weights=dict(HK_character=12,Tatoeba_character_per_family=2,HK_word=1,authored_word_per_family=3),
        limits='Same model formats, fixed original strengths128/1, thresholds, smoothing and inference. Full vocabulary/dictionary assets frozen; no new phrase tokens. No Tatoeba word-boundary guesses or held-out probability optimization. Research only, adoption requires separate native validation.')
    write_json(output/'report.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    s=sub.add_parser('prepare');s.add_argument('hk',type=Path);s.add_argument('output',type=Path)
    s=sub.add_parser('fit');s.add_argument('data',type=Path);s.add_argument('cantonese',type=Path);s.add_argument('training_assets',type=Path);s.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.hk,a.output)
    else:fit(a.data,a.cantonese,a.training_assets,a.output)
