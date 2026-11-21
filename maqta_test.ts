import { classify } from './maqta';

const cases: [string, string, string, boolean][] = [
  // [word, expected_category, expected_level, expected_drillable]
  ['بَ',   'A', 'L1', true],
  ['بً',   'B', 'L1', true],
  ['آ',    'C', 'L1', true],
  ['قَالَ', 'C', 'L2', true],
  ['مِنْ',  'F', 'L2', true],   
  ['قُلْ',  'D', 'L2', true],
  ['رَبَّ', 'E', 'L2', true],
  ['أَبَّ', 'E', 'L2', true],   // Shadda at pos 1 -> drillable
  ['بَّتْ', 'E', 'L2', false],  // Shadda at pos 0 -> NOT drillable
  ['كَتَبَ', 'A', 'L3', true],
  ['يَقُولُ', 'C', 'L3', true],
  ['مُحَمَّدٌ', 'K', 'L4', true], // also E, B
  ['اَللَّه', 'H', 'L2', true],  // shadda + sukoon
  ['رَبَّتْ', 'H', 'L2', true],
];

let pass = 0;
let fail = 0;

for (const [w, expectedCat, expectedLvl, expectedDrill] of cases) {
  const c = classify(w);
  const ok = 
    c.primaryCategory === expectedCat && 
    c.level === expectedLvl && 
    c.drillable === expectedDrill;

  if (ok) {
    pass++;
    console.log(`✓ ${w} → ${c.primaryCategory} ${c.level} [drill: ${c.drillable}] (audio: ${c.audioId})`);
  } else {
    fail++;
    console.log(`✗ ${w} → expected ${expectedCat}/${expectedLvl}/${expectedDrill}, got ${c.primaryCategory}/${c.level}/${c.drillable}`);
    if (c.drillFilterReason) console.log(`   Reason: ${c.drillFilterReason}`);
  }
}

console.log(`\nResult: ${pass} passed, ${fail} failed.`);
if (fail > 0) process.exit(1);
