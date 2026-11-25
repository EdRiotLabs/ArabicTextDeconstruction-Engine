"""
Haroofie: Maqta Engine V2.1 (Python Edition)
Extracts overlapping L1/L2/L3 units, handles Wasl Elision, Madd IDs, and Iqlab.
Zero dependencies. Pure Unicode manipulation. Ideal for Colab / Kaggle.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Set
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
    
    # Floating Meem (Iqlab)
    SMALL_HIGH_MEEM = '\u06E2'
    SMALL_LOW_MEEM = '\u06ED'

IS_DIACRITIC = re.compile(r'[\u064B-\u0653\u0670\u0640]')
FLOATING_MEEM = re.compile(r'[\u06E2\u06ED]')

# ---------- Letter Codes ----------
LETTER_CODES = {
    'ا':'01', 'أ':'01', 'إ':'01', 'ٱ':'01',
    'ب':'02','ت':'03','ث':'04','ج':'05','ح':'06','خ':'07','د':'08','ذ':'09',
    'ر':'10','ز':'11','س':'12','ش':'13','ص':'14','ض':'15','ط':'16','ظ':'17',
    'ع':'18','غ':'19','ف':'20','ق':'21','ك':'22','ل':'23','م':'24','ن':'25',
    'ه':'26','ة':'26','و':'27','ؤ':'27','ي':'28','ى':'28','ئ':'28','ء':'29',
}

MADD_CANDIDATES = set(['ا','أ','إ','ٱ','و','ؤ','ي','ئ','ى'])
PREFIXES = set(['وَ', 'فَ', 'بِ', 'لِ', 'كَ'])
WASL_ALIFS = set(['ا', 'ٱ'])

# ---------- Types ----------
@dataclass
class Cluster:
    letter: str
    letter_code: str
    marks: List[str]
    mark_code: str
    position: int
    is_madd: bool
    is_leen: bool
    raw_text: str
    is_wasl: bool = False
    has_iqlab: bool = False

# ---------- Helpers ----------
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

def get_category(clusters: List[Cluster]) -> str:
    """Determines the primary category of a given list of clusters (a unit)."""
    has_sukoon = any(C.SUKOON in c.marks for c in clusters)
    has_shadda = any(C.SHADDA in c.marks for c in clusters)
    has_noon_sakinah = any(c.letter == 'ن' and C.SUKOON in c.marks for c in clusters)
    has_leen = any(c.is_leen for c in clusters)
    has_madd = any(c.mark_code in ['15', '16', '17'] or C.MADDAH in c.marks for c in clusters)
    has_tanween = any(any(m in c.marks for m in [C.FATHATAN, C.KASRATAN, C.DAMMATAN]) for c in clusters)
    has_iqlab = any(c.has_iqlab for c in clusters)

    if has_iqlab: return 'N'
    if has_leen: return 'L'
    if has_shadda and has_sukoon: return 'H'
    if has_shadda and has_madd: return 'I'
    if has_tanween and has_shadda: return 'K'
    if has_tanween and has_madd: return 'J'
    if has_shadda: return 'E'
    if has_sukoon: 
        if has_noon_sakinah: return 'F'
        if has_madd: return 'G'
        return 'D'
    if has_madd: return 'C'
    if has_tanween: return 'B'
    return 'A'

# ---------- Core Engine ----------
def build_clusters(word: str) -> List[Cluster]:
    has_floating_meem = bool(FLOATING_MEEM.search(word))
    clean_word = FLOATING_MEEM.sub('', word)
    
    raw = []
    for ch in clean_word:
        if IS_DIACRITIC.match(ch) and len(raw) > 0:
            raw[-1]['marks'].append(ch)
        elif not IS_DIACRITIC.match(ch):
            raw.append({'letter': ch, 'marks': []})

    for r in raw:
        if r['letter'] == 'آ':
            r['letter'] = 'ا'
            r['marks'].insert(0, C.MADDAH)

    out = []
    for i, r in enumerate(raw):
        prev_cluster = out[-1] if out else None
        
        # Integrated Wasl Detection
        is_wasl = False
        if r['letter'] in WASL_ALIFS and len(r['marks']) == 0:
            if i == 0: is_wasl = True
            elif i == 1 and raw[0]['letter'] in PREFIXES: is_wasl = True
            
        # Skip Wasl completely (it is elided in pronunciation)
        if is_wasl:
            continue

        # Madd Detection
        is_madd = False
        if prev_cluster and r['letter'] in MADD_CANDIDATES and len(r['marks']) == 0:
            if r['letter'] in ['ا', 'ى'] and C.FATHA in prev_cluster.marks: is_madd = True
            elif r['letter'] == 'و' and C.DAMMA in prev_cluster.marks: is_madd = True
            elif r['letter'] == 'ي' and C.KASRA in prev_cluster.marks: is_madd = True

        # Leen Detection
        is_leen = False
        if C.SUKOON in r['marks'] and r['letter'] in ['و', 'ي'] and prev_cluster and C.FATHA in prev_cluster.marks:
            is_leen = True

        # Madd ID Override & Merge
        if is_madd:
            if r['letter'] in ['ا', 'ى']: prev_cluster.mark_code = '15'
            elif r['letter'] == 'و': prev_cluster.mark_code = '16'
            elif r['letter'] == 'ي': prev_cluster.mark_code = '17'
            prev_cluster.raw_text += r['letter']
            continue # Skip adding Madd letter as a separate cluster

        out.append(Cluster(
            letter=r['letter'],
            letter_code=LETTER_CODES.get(r['letter'], '??'),
            marks=r['marks'],
            mark_code=pick_mark(r['marks']),
            position=len(out),
            is_madd=is_madd,
            is_leen=is_leen,
            raw_text=r['letter'] + ''.join(r['marks']),
            is_wasl=is_wasl,
            has_iqlab=has_floating_meem
        ))
    return out

def extract_units(clusters: List[Cluster]) -> Dict[str, Set[str]]:
    units = {'L1': set(), 'L2': set(), 'L3': set()}
    n = len(clusters)
    
    for i in range(n):
        start_c = clusters[i]
        
        # "Bad Start" Filter
        if C.SHADDA in start_c.marks or C.SUKOON in start_c.marks or start_c.is_madd or start_c.is_wasl: 
            continue
        
        units['L1'].add(start_c.raw_text)
            
        if i + 1 < n:
            next_c = clusters[i+1]
            
            # Shadda Look-back
            if C.SHADDA in next_c.marks:
                unit_text = start_c.raw_text + next_c.raw_text
                units['L2'].add(unit_text)
                if i + 2 < n and C.SHADDA not in clusters[i+2].marks and C.SUKOON not in clusters[i+2].marks:
                    units['L3'].add(unit_text + clusters[i+2].raw_text)

            # Madd Look-ahead
            elif next_c.mark_code in ['15', '16', '17']:
                unit_text = start_c.raw_text + next_c.raw_text 
                units['L2'].add(unit_text)
                if i + 2 < n and C.SUKOON in clusters[i+2].marks:
                    units['L3'].add(unit_text + clusters[i+2].raw_text)

            # Leen Look-ahead
            elif next_c.is_leen:
                unit_text = start_c.raw_text + next_c.raw_text
                units['L2'].add(unit_text)
                if i + 2 < n and C.SHADDA not in clusters[i+2].marks and C.SUKOON not in clusters[i+2].marks:
                    units['L3'].add(unit_text + clusters[i+2].raw_text)

            # Standard Sukoon
            elif C.SUKOON in next_c.marks:
                unit_text = start_c.raw_text + next_c.raw_text
                units['L2'].add(unit_text)

    return units

def get_audio_id_from_text(text: str) -> str:
    clusters = build_clusters(text)
    return '_'.join(f"{c.letter_code}_{c.mark_code}" for c in clusters)

# ---------- Batch Processing ----------
def process_corpus(words: List[str]) -> Dict[str, Any]:
    l2_inventory = {}
    l3_inventory = {}
    l4_vocabulary = []

    for w in words:
        clusters = build_clusters(w)
        if not clusters: continue
        
        word_len = len(clusters)
        units = extract_units(clusters)
        
        # 1. Process L4/L5 Words (Length >= 5)
        if word_len >= 5:
            l4_vocabulary.append({
                "word": w,
                "audio_id": get_audio_id_from_text(w)
            })

        # 2. Process L2 Units
        for u in units['L2']:
            if u not in l2_inventory:
                u_clusters = build_clusters(u)
                l2_inventory[u] = {
                    "unit": u,
                    "audio_id": get_audio_id_from_text(u),
                    "category": get_category(u_clusters),
                    "frequency": 1,
                    "atomic": True 
                }
            else:
                l2_inventory[u]["frequency"] += 1

        # 3. Process L3 Units
        for u in units['L3']:
            if u not in l3_inventory:
                u_clusters = build_clusters(u)
                l3_inventory[u] = {
                    "unit": u,
                    "audio_id": get_audio_id_from_text(u),
                    "category": get_category(u_clusters),
                    "frequency": 1,
                    "atomic": True
                }
            else:
                l3_inventory[u]["frequency"] += 1

    # Sort inventories by frequency descending
    l2_sorted = sorted(list(l2_inventory.values()), key=lambda x: x['frequency'], reverse=True)
    l3_sorted = sorted(list(l3_inventory.values()), key=lambda x: x['frequency'], reverse=True)

    return {
        "L2": l2_sorted,
        "L3": l3_sorted,
        "L4": l4_vocabulary
    }
