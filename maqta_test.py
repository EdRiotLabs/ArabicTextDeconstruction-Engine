# Colab Test Cell
from maqta import classify

cases = [
    # [word, expected_category, expected_level, expected_drillable]
    ('بَ',   'A', 'L1', True),
    ('بً',   'B', 'L1', True),
    ('آ',    'C', 'L1', True),
    ('قَالَ', 'C', 'L2', True),
    ('مِنْ',  'F', 'L2', True),   
    ('قُلْ',  'D', 'L2', True),
    ('رَبَّ', 'E', 'L2', True),
    ('أَبَّ', 'E', 'L2', True),   # Shadda at pos 1 -> drillable
    ('بَّتْ', 'E', 'L2', False),  # Shadda at pos 0 -> NOT drillable
    ('كَتَبَ', 'A', 'L3', True),
    ('يَقُولُ', 'C', 'L3', True),
    ('مُحَمَّدٌ', 'K', 'L4', True), # also E, B
    ('اَللَّه', 'H', 'L2', True),  # shadda + sukoon
    ('رَبَّتْ', 'H', 'L2', True),
]

passed = 0
failed = 0

for w, expected_cat, expected_lvl, expected_drill in cases:
    c = classify(w)
    ok = (c.primary_category == expected_cat and 
          c.level == expected_lvl and 
          c.drillable == expected_drill)
          
    if ok:
        passed += 1
        print(f"✓ {w} → {c.primary_category} {c.level} [drill: {c.drillable}] (audio: {c.audio_id})")
    else:
        failed += 1
        print(f"✗ {w} → expected {expected_cat}/{expected_lvl}/{expected_drill}, got {c.primary_category}/{c.level}/{c.drillable}")
        if c.drill_filter_reason:
            print(f"   Reason: {c.drill_filter_reason}")

print(f"\nResult: {passed} passed, {failed} failed.")
