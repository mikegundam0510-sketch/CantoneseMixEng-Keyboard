#!/usr/bin/env python3
"""Pretrain next-character prediction, then adapt the same model to TRAIN rivals."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import numpy as np

from prepare_sentence_pretrain import DATA, write
from prepare_tatoeba_corpus import digest
from sentence_language_model import initialize, paths, batch, forward, lm_gradient, pair_gradient, save, NAMES
from train_phrase_model import ROOT


def check(cache):
    seal = json.loads((DATA/'seal.json').read_text())
    if digest(DATA/'protocol.json') != seal['protocol_sha256']:
        raise ValueError('Sealed protocol changed')
    p = json.loads((DATA/'protocol.json').read_text())
    for name, value in p['source_sha256'].items():
        if digest(ROOT/name) != value:
            raise ValueError('Frozen source changed: ' + name)
    m = json.loads((DATA/'manifest.json').read_text())
    if digest(DATA/'manifest.json') != p['manifest_sha256']:
        raise ValueError('Frozen manifest changed')
    for name,value in m['input_sha256'].items():
        if digest(ROOT/name) != value:
            raise ValueError('Frozen original data changed: ' + name)
    for name in ('corpus', 'pairs'):
        if digest(cache/(name+'.jsonl.gz')) != m[name+'_sha256']:
            raise ValueError('Frozen cache changed')
    return p


def weights(rows, mix, paired=False):
    cases, families, rivals = defaultdict(set), defaultdict(set), Counter()
    for r in rows:
        case = (r.get('context', ''), r.get('code', ''), r.get('positive', r.get('text', '')))
        rivals[r['family'], case] += 1
        cases[r['family']].add(case)
        families[r['domain']].add(r['family'])
    values = []
    for r in rows:
        case = (r.get('context', ''), r.get('code', ''), r.get('positive', r.get('text', '')))
        values.append(mix[r['domain']]/len(families[r['domain']])/len(cases[r['family']])/rivals[r['family'], case])
    v = np.asarray(values, dtype=np.float32)
    return v/v.mean()


def fit(cache, output):
    p = check(cache)
    if output.exists():
        raise ValueError('Preserve existing fitted models')
    corpus = [json.loads(s) for s in gzip.decompress((cache/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    pairs = [json.loads(s) for s in gzip.decompress((cache/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    train = [r for r in corpus if r['split'] == 'train']
    values, chars, children, prior = initialize(train, p['architecture']['embedding'], p['architecture']['hidden'])
    vocabulary = {c:i+3 for i,c in enumerate(chars)}
    tree = paths(children, len(prior))
    output.mkdir(parents=True)
    rng = np.random.default_rng(p['seed'])
    history = {}
    def stage(kind, rows, values):
        config = p[kind]
        tr = [r for r in rows if r['split'] == 'train']
        va = [r for r in rows if r['split'] == 'validation']
        wt = weights(tr, config['source_mix'], kind == 'adaptation')
        wv = weights(va, config['source_mix'], kind == 'adaptation')
        moment = {k:np.zeros_like(v) for k,v in values.items()}
        variance = {k:np.zeros_like(v) for k,v in values.items()}
        step = 0
        def objective(rows, w):
            total = 0.
            for start in range(0, len(rows), 256):
                chunk = rows[start:start+256]
                if kind == 'pretraining':
                    _, nll = forward(values, *batch(chunk, vocabulary), tree, prior)
                    total += float(w[start:start+len(chunk)]@nll)
                else:
                    sp, nll = forward(values, *batch(chunk, vocabulary, 'positive'), tree, prior)
                    sn, _ = forward(values, *batch(chunk, vocabulary, 'negative'), tree, prior)
                    offset = np.asarray([r['offset'] for r in chunk], dtype=np.float32)
                    total += float(w[start:start+len(chunk)]@(np.logaddexp(0, -offset-.5*(sp-sn))+.05*nll))
            return total/len(rows)
        initial = objective(va, wv)
        best, best_epoch = initial, 0
        best_values = {k:v.copy() for k,v in values.items()}
        epochs = []
        for epoch in range(config['epochs']):
            order = rng.permutation(len(tr))
            total = 0.
            for start in range(0, len(tr), config['batch']):
                ix = order[start:start+config['batch']]
                chunk = [tr[i] for i in ix]
                if kind == 'pretraining':
                    loss, grad = lm_gradient(values, *batch(chunk, vocabulary), tree, prior, wt[ix])
                else:
                    loss, grad = pair_gradient(values, batch(chunk, vocabulary, 'positive'), batch(chunk, vocabulary, 'negative'),
                                               tree, prior, np.asarray([r['offset'] for r in chunk], dtype=np.float32), wt[ix])
                norm = np.sqrt(sum(float(np.sum(g*g)) for g in grad.values()))
                scale = min(1., config['gradient_clip']/max(norm, 1e-12))
                step += 1
                for key in NAMES:
                    g = grad[key]*scale
                    moment[key] = .9*moment[key]+.1*g
                    variance[key] = .999*variance[key]+.001*g*g
                    values[key] -= config['rate']*(moment[key]/(1-.9**step))/(np.sqrt(variance[key]/(1-.999**step))+1e-8)
                values['embedding'][0] = 0
                total += loss*len(chunk)
            valid = objective(va, wv)
            if not np.isfinite(valid) or not all(np.isfinite(v).all() for v in values.values()):
                raise ValueError('Nonfinite model training')
            result = dict(stage=kind, epoch=epoch+1, training_objective=total/len(tr), internal_validation_objective=valid)
            epochs.append(result)
            print(json.dumps(result), flush=True)
            if valid < best:
                best, best_epoch = valid, epoch+1
                best_values = {k:v.copy() for k,v in values.items()}
        history[kind] = dict(initial_internal_validation=initial, best_internal_validation=best,
                             best_epoch=best_epoch, train=len(tr), validation=len(va), epochs=epochs)
        return best_values
    values = stage('pretraining', corpus, values)
    if history['pretraining']['best_epoch'] == 0:
        raise ValueError('Pretraining failed to improve internal next-character loss')
    save(output/'language.b64', values, chars, children, prior)
    values = stage('adaptation', pairs, values)
    save(output/'adapted.b64', values, chars, children, prior)
    report = dict(protocol_sha256=digest(DATA/'protocol.json'), numpy=np.__version__, vocabulary=len(prior),
                  tree_nodes=len(children), tree_max_depth=tree[0].shape[1],
                  array_bytes=sum(v.nbytes for v in values.values())+children.nbytes+prior.nbytes+4*len(chars),
                  stages=history, models={n:digest(output/n) for n in ('language.b64','adapted.b64')},
                  scope='Next-character pretraining followed by same-code pair adaptation. Checkpoints use original-family-disjoint internal TRAIN validation only. These losses are not keyboard hit rates. No raw Common Voice text mirrored in Git.')
    write(output/'report.json', report)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cache', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    fit(a.cache, a.output)
