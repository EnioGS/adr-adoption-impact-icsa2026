# ADR Status Mapping

This document summarizes how raw ADR status labels found in ADR files are mapped to the normalized status categories used in the study. 

Each normalized status category is associated with multiple surface forms that may appear in ADR texts. During extraction, these forms are normalized to the corresponding category listed in the first column.

## Normalized status categories and mapped labels

### `proposed`
- Mapped labels:
  - `proposed`
  - `draft`
  - `suggested`
  - `pending`
  - `in progress`
  - `under review`
  - `awaiting approval`
  - `undecided`

### `accepted`
- Mapped labels:
  - `accepted`
  - `approved`
  - `finalized`
  - `confirmed`
  - `ratified`
  - `endorsed`

### `deprecated`
- Mapped labels:
  - `deprecated`
  - `obsolete`
  - `archived`
  - `abandoned`
  - `retired`
  - `phased out`

### `rejected`
- Mapped labels:
  - `rejected`
  - `declined`
  - `not approved`
  - `dismissed`
  - `disapproved`

### `superseded`
- Mapped labels:
  - `superseded`
  - `replaced`
  - `updated`
  - `overridden`
  - `substituted`

### `implemented`
- Mapped labels:
  - `implemented`
  - `executed`
  - `deployed`
  - `realized`
  - `put into practice`

### `under revision`
- Mapped labels:
  - `under revision`
  - `being updated`
  - `modifying`
  - `revising`
  - `amending`

### `withdrawn`
- Mapped labels:
  - `withdrawn`
  - `retracted`
  - `pulled back`
  - `rescinded`
  - `revoked`

## Extraction overview

During data extraction, ADR contents are first preprocessed using a lightweight NLP pipeline (tokenization, lowercasing, and removal of non-alphabetic characters and stopwords). The extractor then searches for status-related keywords within this normalized text and uses the mapping above to assign a normalized status category. When both a status keyword and a nearby context pattern such as `status` or `state` are present, the distance between them is used to prioritize more reliable matches. Optionally, fuzzy matching can be enabled to recover approximate matches when exact keyword matches are not found, further increasing robustness to minor spelling variations or formatting differences in ADR files.
