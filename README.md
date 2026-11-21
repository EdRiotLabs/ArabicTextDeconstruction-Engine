# Maqta Engine

**Maqta Engine** (from Arabic *maqta'* / مقطع, meaning "segment" or "syllable") is a zero-dependency TypeScript module for analyzing fully vocalized Arabic words.

It is the core logic powering **IqraSpeed's drill generation system**.

The engine takes an Arabic word, decomposes it into phonetic clusters, identifies its grammatical and phonetic features (Madd, Sukoon, Shadda, etc.), assigns learning categories and levels, and generates a deterministic audio ID that matches the `audio-manifest.json` naming convention.

Maqta Engine is completely independent of UI frameworks, React, databases, and the Quran corpus. It is designed as a pure string-processing module.

---

## 1. Features

Given a fully vocalized Arabic word, the engine produces:

- **Clusters:** Breaks the word down letter by letter, grouping each base letter with its attached diacritics.
- **Features:** Detects phonetic features and rules, including Sukoon, Shadda, Madd, and Noon Sakinah.
- **Categories:** Assigns one primary category (A–K) and any applicable secondary categories (`alsoFits`), following a strict priority order.
- **Levels:** Automatically places the word into L1, L2, L3, or L4 based on its syllabic weight.
- **Drillability:** Determines whether a word qualifies for a standalone drill based on positional and length restrictions.
- **Audio ID:** Generates the exact audio filename (without the `.mp3` extension) required by the audio bank.

## 2. Usage

The engine exports two primary functions:

- `classify()` — Analyzes a single Arabic word.
- `classifyBatch()` — Processes an array of words and groups the results for consumption by the Pack Builder.

### Single Word Classification

```typescript
import { classify } from './lib/maqta';

const result = classify('مِنْ');

console.log(result);
```

**Example output:**

```typescript
{
  word: 'مِنْ',
  baseLetters: 2,
  clusters: [ ... ],
  features: {
    sukoon: true,
    noonSakinah: true,
    ...
  },
  primaryCategory: 'F',
  alsoFits: ['D'],
  level: 'L2',
  unitCount: 1.5,
  drillable: true,
  audioId: '24_02_25_07'
}
```

### Batch Processing

For large word collections, such as a Quran wordlist, use `classifyBatch()`.

The function automatically ignores non-drillable words and organizes the remaining results for easy consumption by the Pack Builder.

```typescript
import { classifyBatch } from './lib/maqta';

const words = ['بَ', 'مِنْ', 'بَّتْ', 'يَقُولُ'];

const results = classifyBatch(words);

console.log(results.byCategory);
// { A: [...], F: [...], C: [...] }
//
// Note: 'بَّتْ' is skipped because it is not drillable.

console.log(results.audioIds);
// [
//   '02_01',
//   '24_02_25_07',
//   '28_01_21_03_27_00_23_03'
// ]
```

---

## 3. Core Concepts & Rules

### 3.1. Cluster Formation

Arabic text is represented in Unicode using base letters followed by combining marks (diacritics).

The engine groups each base letter with all its immediately following diacritical marks into a single **Cluster**.

For example:

- A base letter with Fatha forms one cluster.
- A base letter with Shadda and Fatha forms one cluster.
- A base letter with Sukoon forms one cluster.

**Special Case: Alif Maddah (آ)**

Alif Maddah is represented by a single Unicode codepoint. The engine detects it, splits it into:

- `ا` — Alif
- `ٓ` — Maddah

It then processes the resulting components normally, generating mark code `14`.

### 3.2. Madd Detection

Madd (long vowel) is detected positionally.

A bare `ا`, `و`, or `ي` is considered Madd only when all the following conditions are met:

1. The letter has no diacritical marks of its own.
2. It is immediately preceded by a letter carrying the corresponding short vowel:
   - Fatha (`َ`) before Alif (`ا`).
   - Damma (`ُ`) before Waw (`و`).
   - Kasra (`ِ`) before Ya (`ي`).

**Wasla Exception**

A word-initial Alif is never treated as Madd.

It falls through to the applicable alternative categories (or `null`) without generating false Madd classifications.

### 3.3. Unit Count & Level Assignment

The engine calculates a `unitCount` to determine the difficulty level of a word.

| Letter Condition | Unit Value |
|---|---:|
| Letter with a short vowel | 1.0 |
| Letter with Shadda + vowel | 1.0 |
| Madd letter | 0.5 |
| Letter with Sukoon | 0.5 |
| Bare letter | 0.5 |

The resulting `unitCount` determines the word's level:

| Level | Unit Count |
|---|---|
| L1 | ≤ 1.0 |
| L2 | > 1.0 and ≤ 2.5 |
| L3 | > 2.5 and ≤ 3.5 |
| L4 | > 3.5 |

### 3.4. Category Assignment & Priority

A word can match multiple categories simultaneously.

For example, a word may contain both Shadda and Sukoon, making it eligible for more than one category.

The engine assigns exactly one **primary category** based on the following priority order:

```text
H > I > K > J > E > D > F > G > C > B > A
```

All other matching categories are included in the `alsoFits` array.

This ensures that category assignment remains deterministic and consistent.

### 3.5. Drillability Filter

Not every classified word is suitable for a standalone drill.

The engine marks a word as `drillable: false` when it violates either of the following restrictions.

#### A. Shadda Position Restriction

A letter carrying Shadda cannot appear at position `0` (the first letter of the word).

| Word | Result | Reason |
|---|---|---|
| `بَّتْ` | Not drillable | Shadda on the first letter |
| `رَبَّ` | Drillable | Shadda is not on the first letter |

#### B. Length Restrictions

Words assigned to L2 or L3 have maximum base-letter limits.

| Level | Maximum Base Letters |
|---|---:|
| L2 | 3 |
| L3 | 4 |

If a word exceeds its level's maximum length, it is marked as non-drillable.

When a word fails the drillability checks, the engine provides a `drillFilterReason` explaining why it was rejected.

---

## 4. Audio ID Contract

The generated `audioId` must exactly match the filename convention used by the audio bank.

Each letter contributes exactly two codes:

```text
[letter_code]_[mark_code]
```

These pairs are concatenated in the original reading order to produce the final audio ID.

### Example: `يَقُولُ`

| Cluster | Letter | Mark | Generated Code |
|---|---|---|---|
| `يَ` | Ya | Fatha | `28_01` |
| `قُ` | Qaf | Damma | `21_03` |
| `و` | Waw | Madd | `27_00` |
| `لُ` | Lam | Damma | `23_03` |

**Generated Audio ID:**

```text
28_01_21_03_27_00_23_03
```

This corresponds to the following audio filename:

```text
28_01_21_03_27_00_23_03.mp3
```

The generated ID must remain fully compatible with:

- `audio-manifest.json`
- `NAMING_GUIDE.md`

The engine does not generate or manage audio files. It only produces the deterministic identifier needed to locate the corresponding audio asset.

---

## 5. Scope & Limitations

Maqta Engine is intentionally limited to analyzing individual Arabic words in isolation.

### What It Does Not Do

**Cross-Word Analysis**

The engine does not analyze relationships between adjacent words.

This includes:

- Madd Munfasil.
- Idgham across word boundaries.
- Izhar across word boundaries.

These rules belong to the planned **Wasla Engine**, which will handle cross-word phonetic analysis.

**Standing Harakat**

The engine does not detect Indo-Pakistani standing Harakat, as these are not represented using standard Unicode diacritic characters.

**Muqatta'at**

Disjointed Quranic letters (Muqatta'at) are not specially classified.

They may be returned as `null` or treated as standard words, depending on their structure.

If these need to be excluded from standard drill categories, the Pack Builder must filter them separately.

---

## 6. Testing

Maqta Engine is designed to be strictly deterministic and does not require mocking.

The provided test fixture covers **14 test cases** across different levels and categories.

It specifically verifies:

- Classification across all supported levels.
- Primary and secondary category assignment.
- Madd detection.
- Tanween + Shadda combinations.
- Shadda-at-position-0 rejection.
- Drillability restrictions.
- Audio ID generation.

### Running the Tests

Run the following command from the project root:

```bash
npx tsx lib/maqta.test.ts
```

All assertions should pass for the engine to be considered verified against the provided test fixture.

---

## 7. Design Philosophy

Maqta Engine follows a few core principles:

- **Zero Dependencies:** No external runtime libraries.
- **Deterministic:** Identical input always produces identical output.
- **Framework Independent:** No UI, React, or application-specific dependencies.
- **Corpus Independent:** Analyzes words without requiring access to the Quran corpus or a database.
- **Audio Compatible:** Generated IDs follow the established audio naming convention.
- **Modular:** Designed to work independently while integrating with IqraSpeed's drill generation pipeline.

The engine handles the phonetic classification of individual words. Higher-level systems, such as the Pack Builder and the future Wasla Engine, are responsible for corpus management, drill organization, and cross-word analysis.

---

**Maqta Engine**  
*The phonetic classification core of IqraSpeed.*
