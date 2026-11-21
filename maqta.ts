/**
 * Maqta Engine
 * Single-word classifier, feature detector, and audio-ID generator for Arabic sight-reading.
 * Zero dependencies. Pure Unicode manipulation.
 */

// ---------- Unicode Constants ----------
const C = {
  fatha:    '\u064E',
  kasra:    '\u0650',
  damma:    '\u064F',
  fathatan: '\u064B',
  kasratan: '\u064D',
  dammatan: '\u064C',
  sukoon:   '\u0652',
  shadda:   '\u0651',
  maddah:   '\u0653',
  tatweel:  '\u0640', // we strip this
  dagger:   '\u0670', // we strip this
};

const IS_DIACRITIC = (ch: string) => /[\u064B-\u0653\u0670\u0640]/.test(ch);

// ---------- Letter Codes (From audio-manifest.json) ----------
const LETTER_CODES: Record<string, string> = {
  'ا':'01', 'أ':'01', 'إ':'01', 'ٱ':'01',
  'ب':'02','ت':'03','ث':'04','ج':'05','ح':'06','خ':'07','د':'08','ذ':'09',
  'ر':'10','ز':'11','س':'12','ش':'13','ص':'14','ض':'15','ط':'16','ظ':'17',
  'ع':'18','غ':'19','ف':'20','ق':'21','ك':'22','ل':'23','م':'24','ن':'25',
  'ه':'26','ة':'26','و':'27','ؤ':'27','ي':'28','ى':'28','ئ':'28','ء':'29',
};

const MADD_CANDIDATES = new Set(['ا','أ','إ','ٱ','و','ؤ','ي','ئ','ى']);

// ---------- Types ----------
export interface Cluster {
  letter: string;
  letterCode: string;
  marks: string[];
  markCode: string;
  position: number;
  isMadd: boolean;
  rawText: string;
}

export interface Features {
  sukoon: boolean;
  shadda: boolean;
  madd: boolean;
  tanween: boolean;
  noonSakinah: boolean;
  maddah: boolean;
  shaddaCount: number;
  sukoonCount: number;
}

export type Category = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' | 'J' | 'K';
export type Level = 'L1' | 'L2' | 'L3' | 'L4';

export interface Classification {
  word: string;
  baseLetters: number;
  clusters: Cluster[];
  features: Features;
  primaryCategory: Category | null;
  alsoFits: Category[];
  level: Level;
  unitCount: number;
  drillable: boolean;
  drillFilterReason?: string;
  audioId: string;
}

// ---------- Internal Logic ----------
function pickMark(marks: string[]): string {
  if (marks.includes(C.maddah)) return '14';
  if (marks.includes(C.shadda)) {
    if (marks.includes(C.fatha))    return '08';
    if (marks.includes(C.kasra))    return '09';
    if (marks.includes(C.damma))    return '10';
    if (marks.includes(C.fathatan)) return '11';
    if (marks.includes(C.kasratan)) return '12';
    if (marks.includes(C.dammatan)) return '13';
    return '08'; // fallback
  }
  if (marks.includes(C.sukoon))     return '07';
  if (marks.includes(C.fatha))      return '01';
  if (marks.includes(C.kasra))      return '02';
  if (marks.includes(C.damma))      return '03';
  if (marks.includes(C.fathatan))   return '04';
  if (marks.includes(C.kasratan))   return '05';
  if (marks.includes(C.dammatan))   return '06';
  return '00';
}

function buildClusters(word: string): Cluster[] {
  const raw: { letter: string; marks: string[] }[] = [];
  
  for (const ch of word) {
    if (IS_DIACRITIC(ch) && raw.length > 0) {
      raw[raw.length - 1].marks.push(ch);
    } else if (!IS_DIACRITIC(ch)) {
      raw.push({ letter: ch, marks: [] });
    }
  }

  // Expand آ (Alif + Maddah)
  for (const r of raw) {
    if (r.letter === 'آ') {
      r.letter = 'ا';
      r.marks.unshift(C.maddah);
    }
  }

  const out: Cluster[] = [];
  for (let i = 0; i < raw.length; i++) {
    const r = raw[i];
    const prev = out[i - 1];
    
    // Madd detection: bare letter + correct preceding vowel
    const isMadd = !!prev
      && MADD_CANDIDATES.has(r.letter)
      && r.marks.length === 0
      && (
        ((r.letter === 'ا' || r.letter === 'ى') && prev.marks.includes(C.fatha)) ||
        (r.letter === 'و' && prev.marks.includes(C.damma)) ||
        (r.letter === 'ي' && prev.marks.includes(C.kasra))
      );

    out.push({
      letter: r.letter,
      letterCode: LETTER_CODES[r.letter] ?? '??',
      marks: r.marks,
      markCode: pickMark(r.marks),
      position: i,
      isMadd,
      rawText: r.letter + r.marks.join(''),
    });
  }
  return out;
}

function detectFeatures(clusters: Cluster[]): Features {
  let shaddaCount = 0, sukoonCount = 0;
  let madd = false, tanween = false, maddah = false, noonSakinah = false;

  for (const c of clusters) {
    if (c.marks.includes(C.shadda)) shaddaCount++;
    if (c.marks.includes(C.sukoon)) {
      sukoonCount++;
      if (c.letter === 'ن') noonSakinah = true;
    }
    if (c.isMadd) madd = true;
    if (c.marks.includes(C.maddah)) {
      maddah = true;
      madd = true;
    }
    if (c.marks.includes(C.fathatan) || c.marks.includes(C.kasratan) || c.marks.includes(C.dammatan)) {
      tanween = true;
    }
  }

  return {
    sukoon: sukoonCount > 0,
    shadda: shaddaCount > 0,
    madd,
    tanween,
    noonSakinah,
    maddah,
    shaddaCount,
    sukoonCount,
  };
}

function assignCategories(f: Features): { primary: Category | null; alsoFits: Category[] } {
  const fits: Category[] = [];
  
  // Priority order: H, I, K, J, E, D, F, G, C, B, A
  if (f.shadda && f.sukoon)    fits.push('H');
  if (f.shadda && f.madd)      fits.push('I');
  if (f.tanween && f.shadda)   fits.push('K');
  if (f.tanween && f.madd)     fits.push('J');
  if (f.shadda)                fits.push('E');
  if (f.sukoon)                fits.push('D');
  if (f.noonSakinah)           fits.push('F');
  if (f.madd && f.sukoon)      fits.push('G');
  if (f.madd)                  fits.push('C');
  if (f.tanween)               fits.push('B');
  if (!f.shadda && !f.sukoon && !f.madd && !f.tanween) fits.push('A');

  return {
    primary: fits[0] ?? null,
    alsoFits: fits.slice(1),
  };
}

function computeUnitCount(clusters: Cluster[]): number {
  let total = 0;
  for (const c of clusters) {
    if (c.isMadd) total += 0.5;
    else if (c.marks.includes(C.sukoon)) total += 0.5;
    else if (c.marks.length === 0) total += 0.5;
    else total += 1.0; // harkat (incl. shadda+harkat)
  }
  return total;
}

function getLevel(u: number): Level {
  if (u <= 1.0) return 'L1';
  if (u <= 2.5) return 'L2';
  if (u <= 3.5) return 'L3';
  return 'L4';
}

function checkDrillability(clusters: Cluster[], level: Level): { ok: boolean; reason?: string } {
  // Shadda position rule
  for (let i = 0; i < clusters.length; i++) {
    if (clusters[i].marks.includes(C.shadda) && i === 0) {
      return { ok: false, reason: 'shadda at position 0' };
    }
  }
  
  // Length caps
  const n = clusters.length;
  if (level === 'L2' && n > 3) return { ok: false, reason: 'L2 length cap exceeded' };
  if (level === 'L3' && n > 4) return { ok: false, reason: 'L3 length cap exceeded' };
  if (level === 'L1' && n !== 1) return { ok: false, reason: 'L1 must be 1 letter' };
  
  return { ok: true };
}

// ---------- Public API ----------
export function classify(word: string): Classification {
  const clusters = buildClusters(word);
  const features = detectFeatures(clusters);
  const { primary, alsoFits } = assignCategories(features);
  const unitCount = computeUnitCount(clusters);
  const level = getLevel(unitCount);
  const drill = checkDrillability(clusters, level);
  
  const audioId = clusters.map(c => `${c.letterCode}_${c.markCode}`).join('_');

  return {
    word,
    baseLetters: clusters.length,
    clusters,
    features,
    primaryCategory: primary,
    alsoFits,
    level,
    unitCount,
    drillable: drill.ok,
    drillFilterReason: drill.reason,
    audioId,
  };
}

export function classifyBatch(words: string[]) {
  const all = words.map(classify);
  const byCategory: Record<string, Classification[]> = {};
  const byLevel: Record<string, Classification[]> = {};
  const audioIds = new Set<string>();

  for (const c of all) {
    if (!c.drillable) continue;
    
    if (c.primaryCategory) {
      if (!byCategory[c.primaryCategory]) byCategory[c.primaryCategory] = [];
      byCategory[c.primaryCategory].push(c);
    }
    
    if (!byLevel[c.level]) byLevel[c.level] = [];
    byLevel[c.level].push(c);
    
    audioIds.add(c.audioId);
  }

  return { all, byCategory, byLevel, audioIds: Array.from(audioIds) };
}
