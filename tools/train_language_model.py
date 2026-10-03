#!/usr/bin/env python3
"""Deterministic 5-gram training with validation-selected interpolated backoff.

Inputs: HKCanCor UTF8 ZIP (CC BY 4.0), Rime Cantonese words (CC BY 4.0),
existing Rime Essay-derived Quick vocabulary (LGPL-3.0). Downloaded source
bytes are verified against pinned SHA256 values recorded in MODEL_REPORT.json.
No user text or online inference is involved. Split by conversation file BEFORE training.
"""
import argparse,base64,collections,gzip,hashlib,itertools,json,math,re,struct,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'app/src/main/assets'
MASK=(1<<64)-1;SEED=1469598103934665603;PRIME=1099511628211

def han(c):return '\u3400'<=c<='\u9fff' or '\U00020000'<=c<='\U0003134f'
def key(text):
 h=SEED^len(text)
 for c in text:h=((h^ord(c))*PRIME)&MASK
 return h if h<1<<63 else h-(1<<64)
def chunks(text):
 return re.findall(r'[\u3400-\u9fff\U00020000-\U0003134f]+',text)
def corpus(path):
 result=[]
 with zipfile.ZipFile(path) as z:
  for name in sorted(z.namelist()):
   if name.endswith('/') or not name.startswith('utf8/'):continue
   text=z.read(name).decode('utf-8-sig');parts=[]
   for line in text.splitlines():
    m=re.fullmatch(r'\s*([^/<>\s]+)/[^/]+/[^/]*/\s*',line)
    if m:
     word=m[1]
     if all(han(c) for c in word):parts.append(word)
     else:
      if parts:result.append((name,''.join(parts)));parts=[]
    elif '</sent_tag>' in line or '<sent>' in line:
     if parts:result.append((name,''.join(parts)));parts=[]
   if parts:result.append((name,''.join(parts)))
 return result

def train(args):
 expected={'corpus':'09223963b8756254e15353cad843f8a4b0cbc4b9223dc8a8fa27fb1cf846057e',
           'cantonese':'54d174ad2bb997e4a678b7b076b84e4dc5914481b32467cdea3b43e88b7d5474'}
 for name,digest in expected.items():
  if hashlib.sha256(getattr(args,name).read_bytes()).hexdigest()!=digest:
   raise ValueError('Source hash mismatch: '+name)
 reverse={}
 for line in (ASSETS/'cangjie5.base.dict.yaml').read_text().splitlines():
  f=line.split('\t')
  if len(f)>=2 and len(f[0])==1 and re.fullmatch('[a-z]{1,5}',f[1]):
   c=f[1] if len(f[1])==1 else f[1][0]+f[1][-1];reverse.setdefault(f[0],set()).add(c)
 counts=[collections.Counter() for _ in range(6)]
 def add(text,weight):
  for segment in chunks(text):
   for n in range(1,6):
    for at in range(len(segment)-n+1):counts[n][segment[at:at+n]]+=weight
 # Phrase counts are capped to stop famous written words overwhelming conversational data.
 written={}
 for asset in ['quick_phrases.tsv','hk_phrases.tsv']:
  for line in (ASSETS/asset).read_text().splitlines():
   f=line.split('\t')
   if len(f)==3:written[f[1]]=max(written.get(f[1],0),int(f[2]))
 for text,count in written.items():add(text,min(12,max(1,int(math.log1p(count)))))
 words={}
 for line in args.cantonese.read_text().splitlines():
  f=line.split('\t');text=f[0]
  if len(f)>=2 and 2<=len(text)<=8 and all(c in reverse for c in text):words[text]=2
 data=corpus(args.corpus)
 held={name for name,_ in data if int(hashlib.sha256(name.encode()).hexdigest()[:8],16)%10==0}
 validation={name for name,_ in data if int(hashlib.sha256(name.encode()).hexdigest()[:8],16)%10==1}
 train_data=[text for name,text in data if name not in held and name not in validation]
 valid_data=[text for name,text in data if name in validation]
 test_data=[text for name,text in data if name in held]
 for text in words:add(text,2)
 for text in train_data:add(text,12)
 # Reachable, observed multi-character words expand the Quick lattice; do not memorize held-out utterances.
 observed=collections.Counter()
 for text in train_data:
  for n in range(2,min(8,len(text))+1):
   for at in range(len(text)-n+1):
    word=text[at:at+n]
    if all(c in reverse for c in word):observed[word]+=1
 for text,count in observed.items():
  if count>=3:words[text]=max(words.get(text,0),min(100,count*3))
 rows=set()
 for word,count in words.items():
  options=[sorted(reverse[c],key=lambda x:(len(x),x)) for c in word]
  for parts in itertools.islice(itertools.product(*options),8):rows.add((''.join(parts),word,count))
 (ASSETS/'cantonese_phrases.tsv').write_text('# Derived from HKCanCor training conversations and Rime Cantonese (CC BY 4.0); see MODEL_REPORT.json.\n'+''.join(f'{c}\t{w}\t{v}\n' for c,w,v in sorted(rows)))
 # Additive interpolation strength is selected on separate validation conversations.
 thresholds=[0,1,2,2,3,3];kept=[{t:c for t,c in counts[n].items() if c>=thresholds[n]} for n in range(6)]
 totals=collections.Counter();retained=collections.Counter()
 for n in range(2,6):
  for text,count in counts[n].items():totals[text[:-1]]+=count
  for text,count in kept[n].items():retained[text[:-1]]+=count
 total=sum(counts[1].values());unknown=.5/(total+.5*(len(counts[1])+1))
 def probability(history,c,order,strength):
  text=history+c;p=(counts[1].get(c,0)+.5)/(total+.5*(len(counts[1])+1))
  for n in range(2,min(order,len(text))+1):
   gram=text[-n:];context=gram[:-1];tau=strength*(2**n)
   if totals[context]:p=kept[n].get(gram,0)/(totals[context]+tau)+(1-retained[context]/(totals[context]+tau))*p
  return max(unknown,p)
 def entropy(dataset,order,strength):
  loss=0;chars=0
  for text in dataset:
   for at,c in enumerate(text):loss-=math.log(probability(text[max(0,at-4):at],c,order,strength));chars+=1
  return {'characters':chars,'cross_entropy_nats':loss/chars,'perplexity':math.exp(loss/chars)}
 validation_scores={v:entropy(valid_data,5,v)['cross_entropy_nats'] for v in [2,4,8,16,32,64,128]}
 strength=min(validation_scores,key=validation_scores.get)
 items={};collisions={}
 for n in range(1,6):
  for text,count in kept[n].items():
   h=key(text)
   if h in collisions and collisions[h]!=text:raise ValueError('64-bit model hash collision')
   collisions[h]=text
   probability_value=(count+.5)/(total+.5*(len(counts[1])+1)) if n==1 else count/(totals[text[:-1]]+strength*2**n)
   backoff=1-retained[text]/(totals[text]+strength*2**(n+1)) if totals[text] else 1
   items[h]=(probability_value,backoff)
 payload=struct.pack('>IIIf',0x4B4C4D32,5,len(items),unknown)+b''.join(struct.pack('>qff',h,p,b) for h,(p,b) in sorted(items.items()))
 compressed=gzip.compress(payload,compresslevel=9,mtime=0)
 (ASSETS/'language_model.b64').write_bytes(base64.encodebytes(compressed))
 # Held-out decoding snippets with genuine preceding context. None is written into training data.
 cases=[];seen=set()
 for text in test_data:
  if len(text)<8:continue
  for at in range(4,len(text)-3,4):
   target=text[at:at+6];context=text[max(0,at-4):at]
   if not all(c in reverse for c in target) or target in seen:continue
   code=''.join(sorted(reverse[c],key=lambda x:(-len(x),x))[0] for c in target)
   cases.append({'context':context,'code':code,'text':target});seen.add(target)
 cases.sort(key=lambda x:hashlib.sha256((x['context']+x['text']).encode()).hexdigest())
 (ROOT/'tools/lm_heldout_cases.json').write_text(json.dumps(cases[:120],ensure_ascii=False,indent=2)+'\n')
 report={'algorithm':'character 5-gram, count interpolation with validation-selected prior mass and pruning-aware backoff','context_characters':4,
 'source_revisions':{'hkcancor':'39aeadf920e0b5ca93d0ad7792c59e740e7bdd65','rime_cantonese':'259f0e48bba840c3a2e0d117539e96937f3d89bc','rime_essay':'054920de4f54c9e5994276a96a4fc2a35cb51aa3'},
 'source_sha256':{'hkcancor_zip':hashlib.sha256(args.corpus.read_bytes()).hexdigest(),'cantonese_words':hashlib.sha256(args.cantonese.read_bytes()).hexdigest()},
 'training_conversation_files':len({n for n,_ in data}-held-validation),'validation_conversation_files':sorted(validation),'validation_scores_nats':validation_scores,'prior_strength':strength,'heldout_conversation_files':sorted(held),'training_utterance_chunks':len(train_data),'heldout_utterance_chunks':len(test_data),
 'grams_by_order':[len(x) for x in kept[1:]],'entries':len(items),'model_primitive_array_bytes':len(items)*16,'compressed_model_bytes':len(compressed),'additional_quick_entries':len(rows),'additional_unique_words':len(words),
 'heldout_bigram':entropy(test_data,2,strength),'heldout_fivegram':entropy(test_data,5,strength),'note':'Held-out conversations are excluded from both n-gram training and learned corpus phrase additions; base external dictionaries can naturally contain their words. Perplexity measures next-character probability, not keyboard sentence accuracy.'}
 (ASSETS/'MODEL_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('cantonese',type=Path);train(p.parse_args())
