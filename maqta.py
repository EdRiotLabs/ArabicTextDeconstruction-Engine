"""
Maqta Engine (Python Edition)
Single-word classifier, feature detector, and audio-ID generator for Arabic sight-reading.
Zero dependencies. Pure Unicode manipulation. Ideal for Colab / Kaggle.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import re

# ---------- Unicode Constants ----------
class C:
    FATHA = '\u064E'
    KASRA = '\u0650'
    DAMMA = '\u064F'
    FATHATAN = '\u064B'
    KASRATAN = '\u064D'
    DAMMATAN = '\u064C'
    SUKOON = '\u0652'
    SHADDA = '\u0651'
    MADDAH = '\u0653'
    TATWEEL = '\u0640'
    DAGGER = '\u0670'

IS_DIACRITIC = re.compile(r'[\u064B-\u0653\u0670\u0640]')

# ---------- Letter Codes ----------
LETTER_CODES = {
    'ا':'01', 'أ':'01', 'إ':'01', 'ٱ':'01',
    'ب':'02','ت':'03','ث':'04','ج':'05','ح':'06','خ':'07','د':'08','ذ':'09',
    'ر':'10','ز':'11','س':'12','ش':'13','ص':'14','ض':'15','ط':'16','ظ':'17',
    'ع':'18','غ':'19','ف':'20','ق':'21','ك':'22','ل':'23','م':'24','ن':'25',
    'ه':'26','ة':'26','و':'27','ؤ':'27','ي':'28','ى':'28','ئ':'28','ء':'29',
}

MADD_CANDIDATES = set(['ا','أ','إ','ٱ','و','ؤ','ي','ئ','ى'])

# ---------- Types ----------
@dataclass
class Cluster:
    letter: str
    letter_code: str
    marks: List[str]
    mark_code: str
    position: int
    is_madd: bool
    raw_text: str

@dataclass
class Features:
    sukoon: bool = False
    shadda: bool = False
    madd: bool = False
    tanween: bool = False
    noon_sakinah: bool = False
    maddah: bool = False
    shadda_count: int = 0
    sukoon_count: int = 0

@dataclass
class Classification:
    word: str
    base_letters: int
    clusters: List[Cluster]
    features: Features
    primary_category: Optional[str]
    also_fits: List[str]
    level: str
    unit_count: float
    drillable: bool
    drill_filter_reason: Optional[str]
    audio_id: str

# ---------- Internal Logic ----------
def pick_mark(marks: List[str]) -> str:
    if C.MADDAH in marks: return '14'
    if C.SHADDA in marks:
        if C.FATHA in marks: return '08'
        if C.KASRA in marks: return '09'
        if C.DAMMA in marks: return '10'
        if C.FATHATAN in marks: return '11'
        if C.KASRATAN in marks: return '12'
        if C.DAMMATAN in marks: return '13'
        return '08'
    if C.SUKOON in marks: return '07'
    if C.FATHA in marks: return '01'
    if C.KASRA in marks: return '02'
    if C.DAMMA in marks: return '03'
    if C.FATHATAN in marks: return '04'
    if C.KASRATAN in marks: return '05'
    if C.DAMMATAN in marks: return '06'
    return '00'

def build_clusters(word: str) -> List[Cluster]:
    raw = []
    for ch in word:
        if IS_DIACRITIC.match(ch) and len(raw) > 0:
            raw[-1]['marks'].append(ch)
        elif not IS_DIACRITIC.match(ch):
            raw.append({'letter': ch, 'marks': []})

    # Expand آ (Alif + Maddah)
    for r in raw:
        if r['letter'] == 'آ':
            r['letter'] = 'ا'
            r['marks'].insert(0, C.MADDAH)

    out = []
    for i, r in enumerate(raw):
        prev = out[i - 1] if i > 0 else None
        
        is_madd = False
        if prev and r['letter'] in MADD_CANDIDATES and len(r['marks']) == 0:
            if r['letter'] in ['ا', 'ى'] and C.FATHA in prev.marks: is_madd = True
            elif r['letter'] == 'و' and C.DAMMA in prev.marks: is_madd = True
            elif r['letter'] == 'ي' and C.KASRA in prev.marks: is_madd = True

        out.append(Cluster(
            letter=r['letter'],
            letter_code=LETTER_CODES.get(r['letter'], '??'),
            marks=r['marks'],
            mark_code=pick_mark(r['marks']),
            position=i,
            is_madd=is_madd,
            raw_text=r['letter'] + ''.join(r['marks'])
        ))
    return out

def detect_features(clusters: List[Cluster]) -> Features:
    f = Features()
    for c in clusters:
        if C.SHADDA in c.marks:
            f.shadda_count += 1
            f.shadda = True
        if C.SUKOON in c.marks:
            f.sukoon_count += 1
            f.sukoon = True
            if c.letter == 'ن':
                f.noon_sakinah = True
        if c.is_madd:
            f.madd = True
        if C.MADDAH in c.marks:
            f.maddah = True
            f.madd = True
        if any(m in c.marks for m in [C.FATHATAN, C.KASRATAN, C.DAMMATAN]):
            f.tanween = True
    return f

def assign_categories(f: Features) -> Tuple[Optional[str], List[str]]:
    fits = []
    if f.shadda and f.sukoon: fits.append('H')
    if f.shadda and f.madd: fits.append('I')
    if f.tanween and f.shadda: fits.append('K')
    if f.tanween and f.madd: fits.append('J')
    if f.shadda: fits.append('E')
    if f.sukoon: fits.append('D')
    if f.noon_sakinah: fits.append('F')
    if f.madd and f.sukoon: fits.append('G')
    if f.madd: fits.append('C')
    if f.tanween: fits.append('B')
    if not (f.shadda or f.sukoon or f.madd or f.tanween): fits.append('A')

    return (fits[0] if fits else None, fits[1:])

def compute_unit_count(clusters: List[Cluster]) -> float:
    total = 0.0
    for c in clusters:
        if c.is_madd or C.SUKOON in c.marks or len(c.marks) == 0:
            total += 0.5
        else:
            total += 1.0
    return total

def get_level(u: float) -> str:
    if u <= 1.0: return 'L1'
    if u <= 2.5: return 'L2'
    if u <= 3.5: return 'L3'
    return 'L4'

def check_drillability(clusters: List[Cluster], level: str) -> Tuple[bool, Optional[str]]:
    for i, c in enumerate(clusters):
        if C.SHADDA in c.marks and i == 0:
            return False, 'shadda at position 0'
            
    n = len(clusters)
    if level == 'L2' and n > 3: return False, 'L2 length cap exceeded'
    if level == 'L3' and n > 4: return False, 'L3 length cap exceeded'
    if level == 'L1' and n != 1: return False, 'L1 must be 1 letter'
    
    return True, None

# ---------- Public API ----------
def classify(word: str) -> Classification:
    clusters = build_clusters(word)
    features = detect_features(clusters)
    primary, also_fits = assign_categories(features)
    unit_count = compute_unit_count(clusters)
    level = get_level(unit_count)
    drillable, reason = check_drillability(clusters, level)
    
    audio_id = '_'.join(f"{c.letter_code}_{c.mark_code}" for c in clusters)

    return Classification(
        word=word,
        base_letters=len(clusters),
        clusters=clusters,
        features=features,
        primary_category=primary,
        also_fits=also_fits,
        level=level,
        unit_count=unit_count,
        drillable=drillable,
        drill_filter_reason=reason,
        audio_id=audio_id
    )

def classify_batch(words: List[str]) -> Dict[str, Any]:
    all_results = [classify(w) for w in words]
    by_category = {}
    by_level = {}
    audio_ids = set()

    for c in all_results:
        if not c.drillable:
            continue
            
        if c.primary_category:
            by_category.setdefault(c.primary_category, []).append(c)
            
        by_level.setdefault(c.level, []).append(c)
        audio_ids.add(c.audio_id)

    return {
        "all": all_results,
        "by_category": by_category,
        "by_level": by_level,
        "audio_ids": list(audio_ids)
    }
