"""Causal GRU with a normalized hierarchical-softmax character distribution.

Pretraining predicts each next character. The deployed bounded residual is the
mean conditional log-likelihood improvement over TRAIN unigram probabilities.
Pair adaptation differentiates exactly that same score, never a sentence lookup.
"""
import base64
from collections import Counter, defaultdict
import gzip
import heapq
import struct
from pathlib import Path
import numpy as np

from context_gru import tail, sigmoid

MAGIC = 0x534c4d31
NAMES = ('embedding', 'input', 'recurrent', 'bias', 'output', 'output_bias')


def make_tree(counts):
    heap = [(float(c), i, -i-1) for i, c in enumerate(counts) if i not in (0, 2)]
    heapq.heapify(heap)
    children = []
    serial = len(counts)
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        children.append((a[2], b[2]))
        heapq.heappush(heap, (a[0]+b[0], serial, len(children)-1))
        serial += 1
    # Preorder numbering makes every internal child greater than its parent.
    ordered = []
    def visit(node):
        if node < 0:
            return node
        at = len(ordered)
        ordered.append(None)
        ordered[at] = (visit(children[node][0]), visit(children[node][1]))
        return at
    visit(heap[0][2])
    return np.asarray(ordered, dtype=np.int32)


def paths(children, size):
    found = {}
    def visit(node, nodes, bits):
        if node < 0:
            found[-node-1] = (nodes, bits)
            return
        for bit in (0, 1):
            visit(int(children[node, bit]), nodes+[node], bits+[bit])
    visit(0, [], [])
    depth = max(len(n) for n, _ in found.values())
    indices = np.zeros((size, depth), dtype=np.int32)
    targets = np.zeros((size, depth), dtype=np.float32)
    mask = np.zeros((size, depth), dtype=np.float32)
    for token, (nodes, bits) in found.items():
        indices[token, :len(nodes)] = nodes
        targets[token, :len(nodes)] = bits
        mask[token, :len(nodes)] = 1
    return indices, targets, mask


def initialize(rows, dimension=32, hidden=32, seed=20261017):
    counts, families = Counter(), defaultdict(set)
    for r in rows:
        counts.update(r['text'])
        for c in r['text']:
            families[c].add(r['family'])
    characters = sorted(sorted((c for c in counts if counts[c] >= 3 and len(families[c]) >= 2),
                               key=lambda c: (-counts[c], ord(c)))[:4093])
    if len(characters) < 2:
        raise ValueError('Insufficient independently supported vocabulary')
    vocabulary = {c: i+3 for i, c in enumerate(characters)}
    frequencies = np.full(len(characters)+3, .5)
    frequencies[0] = frequencies[2] = 0
    for c, n in counts.items():
        frequencies[vocabulary.get(c, 1)] += n
    children = make_tree(frequencies)
    prior = np.log(np.maximum(frequencies, .5)/frequencies.sum()).astype(np.float32)
    rng = np.random.default_rng(seed)
    values = dict(embedding=rng.normal(0, .12, (len(prior), dimension)),
                  input=rng.normal(0, 1/np.sqrt(dimension), (dimension, 3*hidden)),
                  recurrent=rng.normal(0, .1, (hidden, 3*hidden)), bias=np.zeros(3*hidden),
                  output=np.zeros((len(children), hidden)), output_bias=np.zeros(len(children)))
    def mass(node):
        if node < 0:
            return frequencies[-node-1]
        left, right = (mass(int(c)) for c in children[node])
        values['output_bias'][node] = np.log(right/left)
        return left+right
    mass(0)
    values = {k: v.astype(np.float32) for k, v in values.items()}
    values['embedding'][0] = 0
    values['bias'][:hidden] = -1
    return values, characters, children, prior


def encode(context, text, vocabulary):
    context = tail(context)
    return [2]+[vocabulary.get(c, 1) for c in context+text], len(context)


def batch(rows, vocabulary, key='text'):
    encoded = [encode(r.get('context', ''), r[key], vocabulary) for r in rows]
    ids = np.zeros((len(rows), max(len(s) for s, _ in encoded)), dtype=np.int32)
    targets = np.zeros((len(rows), ids.shape[1]-1), dtype=np.float32)
    for i, (seq, context) in enumerate(encoded):
        ids[i, :len(seq)] = seq
        targets[i, context:len(seq)-1] = 1
    return ids, targets


def forward(values, ids, target_mask, tree_paths, prior, cache=False):
    indices, bits, branch_mask = tree_paths
    hidden = values['recurrent'].shape[0]
    h = np.zeros((len(ids), hidden), dtype=values['embedding'].dtype)
    sums = np.zeros(len(ids), dtype=h.dtype)
    steps = []
    for at in range(ids.shape[1]-1):
        token, target = ids[:, at], ids[:, at+1]
        active = (token != 0).astype(h.dtype)[:, None]
        x = values['embedding'][token]
        a = x@values['input']+values['bias']
        b = h@values['recurrent']
        z = sigmoid(a[:, :hidden]+b[:, :hidden])
        r = sigmoid(a[:, hidden:2*hidden]+b[:, hidden:2*hidden])
        g = np.tanh(a[:, 2*hidden:]+r*b[:, 2*hidden:])
        new = active*((1-z)*h+z*g)+(1-active)*h
        ix, bit = indices[target], bits[target]
        mask = branch_mask[target]*target_mask[:, at, None]
        logits = np.einsum('bph,bh->bp', values['output'][ix], new)+values['output_bias'][ix]
        logp = np.sum(mask*(bit*logits-np.logaddexp(0, logits)), axis=1)
        sums += logp
        if cache:
            steps.append((token, active, x, h, z, r, g, b, new, ix, bit, mask, logits))
        h = new
    count = target_mask.sum(axis=1)
    if np.any(count <= 0):
        raise ValueError('At least one candidate target required')
    unigram = (prior[ids[:, 1:]]*target_mask).sum(axis=1)
    raw = (sums-unigram)/count
    score = 2*np.tanh(raw)
    nll = -sums/count
    return (score, nll, (steps, count, raw)) if cache else (score, nll)


def backward(values, cached, sum_derivative):
    steps, _, _ = cached
    grad = {k: np.zeros_like(v) for k, v in values.items()}
    hidden = values['recurrent'].shape[0]
    dh = np.zeros((len(sum_derivative), hidden), dtype=values['embedding'].dtype)
    for token, active, x, previous, z, r, g, b, new, ix, bit, mask, logits in reversed(steps):
        dl = sum_derivative[:, None]*mask*(bit-sigmoid(logits))
        np.add.at(grad['output'], ix, dl[:, :, None]*new[:, None, :])
        np.add.at(grad['output_bias'], ix, dl)
        dh += np.einsum('bp,bph->bh', dl, values['output'][ix])
        used = dh*active
        old = dh*(1-active)+used*(1-z)
        dg = used*z*(1-g*g)
        dz = used*(g-previous)*z*(1-z)
        dr = dg*b[:, 2*hidden:]*r*(1-r)
        da = np.concatenate((dz, dr, dg), axis=1)
        db = np.concatenate((dz, dr, dg*r), axis=1)
        grad['input'] += x.T@da
        grad['recurrent'] += previous.T@db
        grad['bias'] += da.sum(axis=0)
        np.add.at(grad['embedding'], token, da@values['input'].T)
        dh = old+db@values['recurrent'].T
    grad['embedding'][0] = 0
    return grad


def lm_gradient(values, ids, mask, tree_paths, prior, weights):
    _, nll, cache = forward(values, ids, mask, tree_paths, prior, True)
    return float(np.mean(weights*nll)), backward(values, cache, -weights/(len(ids)*cache[1]))


def pair_gradient(values, positive, negative, tree_paths, prior, offset, weights, auxiliary=.05):
    sp, nll, cp = forward(values, *positive, tree_paths, prior, True)
    sn, _, cn = forward(values, *negative, tree_paths, prior, True)
    gap = offset+.5*(sp-sn)  # Exact fixed deployment strength.
    loss = np.mean(weights*(np.logaddexp(0, -gap)+auxiliary*nll))
    d = -weights*sigmoid(-gap)/len(weights)*.5
    gp = backward(values, cp, (d*2*(1-np.tanh(cp[2])**2)-auxiliary*weights/len(weights))/cp[1])
    gn = backward(values, cn, -d*2*(1-np.tanh(cn[2])**2)/cn[1])
    return float(loss), {k: gp[k]+gn[k] for k in NAMES}


def save(path, values, characters, children, prior, strength=.5):
    dimension = values['embedding'].shape[1]
    hidden = values['recurrent'].shape[0]
    raw = struct.pack('>IIIIIIff', MAGIC, dimension, hidden, len(prior), 12, 48, 2., strength)
    raw += b''.join(struct.pack('>I', ord(c)) for c in characters)
    raw += np.asarray(children, dtype='>i4').tobytes()+np.asarray(prior, dtype='>f4').tobytes()
    raw += b''.join(np.asarray(values[k], dtype='>f4').tobytes() for k in NAMES)
    Path(path).write_bytes(base64.encodebytes(gzip.compress(raw, mtime=0)))


def read(path):
    raw = gzip.decompress(base64.b64decode(Path(path).read_bytes()))
    magic, dimension, hidden, size, context, maximum, cap, strength = struct.unpack_from('>IIIIIIff', raw)
    if magic != MAGIC or context != 12 or maximum != 48 or cap != 2:
        raise ValueError('Unsupported sentence language model')
    characters = [chr(struct.unpack_from('>I', raw, 32+4*i)[0]) for i in range(size-3)]
    at = 32+4*(size-3)
    children = np.frombuffer(raw, dtype='>i4', count=2*(size-3), offset=at).astype(np.int32).reshape(-1, 2)
    at += 8*(size-3)
    prior = np.frombuffer(raw, dtype='>f4', count=size, offset=at).astype(np.float32)
    at += 4*size
    shapes = [(size, dimension), (dimension, 3*hidden), (hidden, 3*hidden),
              (3*hidden,), (size-3, hidden), (size-3,)]
    values = {}
    for key, shape in zip(NAMES, shapes):
        count = int(np.prod(shape))
        values[key] = np.frombuffer(raw, dtype='>f4', count=count, offset=at).astype(np.float32).reshape(shape)
        at += 4*count
    if at != len(raw):
        raise ValueError('Unexpected sentence model bytes')
    return values, characters, children, prior, strength
