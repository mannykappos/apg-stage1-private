"""APG-M8 / APG-M8.1: APG as a module client of AUIF (rev14 from APG-M8.1; the frozen rev13 before) (synthetic data only).  BUILDER-MADE, FOR REVIEW; nothing here is accepted, approved or for use outside tests.

  dependency   verify the AUIF rev14 ZIP by hash and import AUIF from a fresh, verified extraction (AUIF is never modified or copied as source)
  layout       which Builder Zero file reaches APG through which synthetic integration
  definitions  the construction definitions (MODULE namespace, status PROPOSED) and the AUIF canonical model built from them
  pack         the synthetic translation packs (configuration only) and the file-import connectors
  module       the APG module: receives entities, observations, events, states and errors; never acts outward
  intake       deliveries -> APG records with lineage, under the unchanged M3 rules; a batch is applied whole or not at all
  gate         the assessment gate: "cannot assess" with reasons instead of any old, default or partial value
  client       an AUIF runtime for APG (no real system, credential, Governor, Engine port or outbound action)
  assess       the assessment entry point: the gate first, then the financial core and detection
  lineage      lineage checks: every record, figure input and signal's evidence traces to its source
  loaders      the Builder Zero loaders for the AUIF path, with the same signatures as the M3 loaders (used to prove path equivalence)"""
M8_VERSION = 'apg-m8-0.1'
