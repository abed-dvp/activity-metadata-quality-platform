# Location anomaly adjudication

## Executive summary

The first address-coordinate diagnostic produced 12 reviewable cases from a 30-row deterministic sample:

- 7 suspicious
- 2 uncertain
- 3 unresolved

Root-cause routing reduced those to two Priority-1 address-coordinate mismatch candidates:

1. Acorn 20/20
2. The Corrib Rest

Independent evidence review found that **neither case supports automatically changing the stored coordinate**.

## Case 1 — Acorn 20/20

Source metadata:

- address: `20 Richmond Rd`
- source coordinate: `51.41304021, -0.300514441`
- initial geocoder distance: `26.9 km`

The first geocoder resolved the short address to a different Richmond Road in Leytonstone.

Kingston Council licensing records independently identify **Acorn 20 at 20 Richmond Road, Kingston upon Thames, KT2 5BE**.

Adjudication:

```text
root cause       = ADDRESS_CONTEXT_INCOMPLETE
address action   = add Kingston upon Thames + postcode
coordinate action= keep/review; no evidence it is wrong
```

Evidence:

- https://moderngov.kingston.gov.uk/mgAi.aspx?ID=33697
- https://kingston.moderngov.co.uk/documents/g8041/Public%20reports%20pack%20Monday%2020-Feb-2017%2010.30%20Licensing%20Sub-Committee.pdf?T=10

## Case 2 — The Corrib Rest

Source metadata:

- address: `82 Salisbury Rd`
- source coordinate: `51.53711593, -0.206589439`
- initial geocoder distance: `13.2 km`

Independent references identify the venue at **76–78 Salusbury Road, Queen's Park, NW6 6PA**. The source uses `Salisbury` instead of `Salusbury`.

CAMRA/WhatPub also provides a sat-nav reference around `51.53759, -0.20731`, about 73 m from the source coordinate.

Adjudication:

```text
root cause       = ADDRESS_STREET_NAME_TYPO
address action   = correct Salisbury → Salusbury
coordinate action= KEEP_PIN
```

Evidence:

- https://whatpub.com/pubs/NLD/6158/corrib-rest-queens-park
- https://camra.org.uk/pubs/corrib-rest-queens-park-125366

## Product / architecture implication

A naive rule such as:

```text
geocoder_distance > threshold → bad pin
```

would have produced two false coordinate-defect conclusions in this sample.

The safer sequence is:

```text
address completeness / spelling
        ↓
entity-aware geocoding
        ↓
distance anomaly
        ↓
evidence review
        ↓
address correction OR coordinate correction
```

This is directly relevant to supplier metadata QA: the system should identify **which field is likely wrong**, not merely detect that two location signals disagree.

No automatic coordinate overwrite is enabled.
