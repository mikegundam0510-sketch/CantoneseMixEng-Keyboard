"""Small train-only lexical tokenizer and bounded Cantonese phrase relations.

Untrained relations have zero evidence, never a ban. Role/category sharing permits
unseen noun/action combinations; complete sentences never become features.
"""
import base64
from collections import Counter
import gzip
import math
import struct
from sentence_features import han

ROLES='PNVQMA DRFC TOB'.replace(' ','')+'XZU'
OVERRIDES={}
for role,words in {
    'P':'我 你 佢 我哋 你哋 佢哋 您 大家 自己',
    'X':'唔 冇 未 唔好 唔使 唔洗 唔駛 毋須 咪 毋',
    'Z':'咗 緊 過',
    'Q':'個 件 張 本 碟 杯 支 間 條 架 份 次 位 隻 部 對 塊 張 座 袋 碗 盒 瓶 啲',
    'D':'咁 噉 就 先 再 都 又 啱啱 而家 今日 聽日',
    'M':'一 二 三 四 五 六 七 八 九 十 百 千 萬 兩 幾',
    'R':'畀 俾 比 給 同 對 向 喺 在 到 從',
    'C':'但 但係 所以 因為 如果 或者 同埋 而且 不過',
    'T':'呀 啊 喇 啦 㗎 囉 喎 呢 啫 咩 嗎',
    'V':'係 有 要 會 想 可以 能夠 應該 需要 繼續 完善 改善 研究 修改 調整 檢查 打字 返工 收工',
    'U':'乜 乜嘢 點 點解 點樣 幾時 邊 邊度 邊個 幾多 係咪 有冇 會唔會 要唔要 可唔可以',
}.items():
    OVERRIDES.update({word:role for word in words.split()})
QUESTION={'未':'Y','咩':'W','嗎':'Y','呢':'U'}
NOUN_GROUPS={
    'F':'飯 粉 麵 粥 餅 包 菜 湯 茶 水 汁 酒 肉 魚 蛋 糖 果 餸 豬腸粉 腸粉 米粉 河粉 意粉 炒飯 湯麵 牛腩麵 奶茶 咖啡 可樂 汽水 啤酒 豆漿 涼茶 麵包 菠蘿包 蛋糕 雞蛋 雞翼 牛肉 豬肉 雞肉 水果 蘋果 香蕉 花生 木瓜 三文治 沙律 甜品 雪糕 麥皮 麥片',
    'D':'功課 文件 報告 資料 表格 電郵 訊息 紙 紙張 書 書本 報紙 信 信件 筆記 清單 名單 帳單 賬單 收據 合約 合同 表 申請表',
    'H':'人 老細 同事 朋友 同學 老師 學生 家人 哥哥 姐姐 妹妹 弟弟 爸爸 媽媽 阿哥 阿爸 阿媽 司機 主席 議員 客人 員工 職員 醫生 病人 市民 小朋友',
    'L':'屋企 公司 學校 餐廳 車站 屋 房 屋苑 街 市場 超市 商場 地鐵站 巴士站 港鐵站 公園 工廠 醫院 住宅 地址',
    'E':'車 汽車 巴士 的士 電腦 手機 相機 電視 冷氣 雪櫃 洗衣機 機器 單車 船 飛機 收音機',
}
NOUN_CATEGORIES={w:tag for tag,words in NOUN_GROUPS.items() for w in words.split()}
OVERRIDES.update({w:'N' for w in NOUN_CATEGORIES if w not in OVERRIDES})

def category(word):
    # Conservative exact categories: 錢包 is not food, 司機 is not equipment,
    # and 花生 is not a person. Unlisted nouns stay generic.
    return NOUN_CATEGORIES.get(word,'G')

def trailing(preceding):
    result=[]
    for c in reversed(preceding):
        if not han(c) or len(result)==12:break
        result.append(c)
    return ''.join(reversed(result))

def tokens(preceding,text,lexicon):
    prefix=trailing(preceding);whole=prefix+text;boundary=len(prefix);result=[];at=0
    while at<len(whole):
        if not han(whole[at]):
            result.append((whole[at],'B',at+1>boundary));at+=1;continue
        word=whole[at];role=OVERRIDES.get(word,lexicon.get(word,('O',0))[0])
        for n in range(min(4,len(whole)-at),1,-1):
            value=whole[at:at+n]
            if not all(han(c) for c in value):continue
            if value in OVERRIDES or value in lexicon:
                word=value;role=OVERRIDES.get(word,lexicon.get(word,('O',0))[0]);break
        end=at+len(word)
        if end==len(whole) and word in QUESTION:role='T'
        result.append((word,role,end>boundary));at=end
    return result

def features(preceding,text,lexicon):
    rows=tokens(preceding,text,lexicon);result=Counter();history=[]
    def add(key):result[key]+=1
    for word,role,active in rows:
        if role=='B':history=[];continue
        if active:
            sequence=[r for _,r in history[-3:]]+[role]
            for n in range(2,min(4,len(sequence))+1):add('G|'+''.join(sequence[-n:]))
            if history:
                left,lrole=history[-1];add(f'B|{lrole}|{role}')
            if role=='V':
                for left,lrole in reversed(history[-4:]):
                    if lrole=='P':add(f'SV|{left}|{word}');add(f'SR|P|{word}');break
                    if lrole in ('C','T'):break
                for left,lrole in reversed(history[-3:]):
                    if lrole=='X':add(f'NV|{left}|{word}');break
                    if lrole in ('P','C','T','V'):break
                for left,lrole in reversed(history[-4:]):
                    if lrole=='U':add(f'AV|{"Y" if left in ("係咪","有冇","會唔會","要唔要","可唔可以") else "W"}|{word}');break
                    if lrole in ('C','T'):break
            if role=='N':
                cat=category(word)
                for left,lrole in reversed(history[-3:]):
                    if lrole=='Q':add(f'CN|{left}|{cat}');add(f'CH|{left}|{word[-1]}');break
                    if lrole not in ('A','D','M'):break
                for pos in range(len(history)-1,max(-1,len(history)-5),-1):
                    left,lrole=history[pos]
                    if lrole=='V':
                        add(f'VO|{left}|{cat}');add(f'VH|{left}|{word[-1]}')
                        before=history[max(0,pos-3):pos]
                        if any(r=='P' for _,r in before):add(f'SVO|P|{left}|{cat}')
                        for neg,nrole in reversed(before):
                            if nrole=='X':add(f'NVO|{neg}|{left}|{cat}');break
                            if nrole in ('V','C','T'):break
                        break
                    if lrole in ('P','C','T'):break
            if role=='T' and word in QUESTION:
                for left,lrole in reversed(history[-6:]):
                    if lrole=='V':add(f'VQ|{left}|{QUESTION[word]}');break
                    if lrole in ('C','T'):break
                add(f'Q|{QUESTION[word]}|'+''.join(r for _,r in history[-3:]))
            if role=='U':
                for left,lrole in reversed(history[-4:]):
                    if lrole=='V':add(f'VQ|{left}|W');break
                    if lrole in ('C','T'):break
        history.append((word,role));history=history[-6:]
    return Counter({k:min(2,v) for k,v in result.items()})

def stored(weights):return {k:struct.unpack('>f',struct.pack('>f',v))[0] for k,v in weights.items()}

def encode(lexicon,weights,strength=1):
    if not math.isfinite(strength) or not 0<=strength<=1.5 or len(lexicon)>20000 or len(weights)>6000:
        raise ValueError('Relation model bounds')
    payload=struct.pack('>IIIff',0x50525231,len(lexicon),len(weights),strength,2)
    for word,(role,count) in sorted(lexicon.items()):
        b=word.encode()
        if not 1<=len(word)<=4 or not all(han(c) for c in word) or role not in ROLES or not 1<=count<=65535:raise ValueError('Invalid lexicon')
        payload+=struct.pack('>H',len(b))+b+struct.pack('>BH',ord(role),count)
    for key,value in sorted(weights.items()):
        b=key.encode()
        if not 3<=len(b)<=96 or not math.isfinite(value) or abs(value)>1.5:raise ValueError('Invalid relation weight')
        payload+=struct.pack('>H',len(b))+b+struct.pack('>f',value)
    return base64.encodebytes(gzip.compress(payload,mtime=0))

def evidence(weights,preceding,text,lexicon):
    return sum(weights.get(k,0)*v for k,v in features(preceding,text,lexicon).items())

def correction(weights,preceding,text,reference,lexicon,strength):
    delta=evidence(weights,preceding,text,lexicon)-reference
    return max(0,strength*max(-2,min(2,delta))-.1)
