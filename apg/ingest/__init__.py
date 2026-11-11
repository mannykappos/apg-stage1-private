"""APG ingestion pipeline (M3).  DRAFT, NON-PRODUCTION.  Blueprint: Section 04 (data ingestion, normalisation and reconciliation).

Modules
  mapping      mapping templates applied to a file: strict parsing, row-level problems, nothing defaulted, raw values kept
  entities     supplier resolution that never forces an uncertain match
  pipeline     receive -> validate -> normalise -> store with provenance; duplicate deliveries, revisions and conflicts; one atomic write per file
  reconcile    relationships between records (PO, credits, payments, secondary sources, duplicates, supplier) as a pure function of what is stored
  views        authoritative and provisional views built only from stored records
  freshness    source freshness, completeness and decision eligibility; thresholds are configuration, never invented
  documents    AI/OCR-extracted values stay unverified until a person verifies them
  jobs         bounded retries and a dead-letter list; replay never repeats an effect
Everything sits on the M2 controls (tenant-scoped store, source authority, quarantine, values that know when they are unknown)."""
INGEST_VERSION = 'apg-ingest-1'
