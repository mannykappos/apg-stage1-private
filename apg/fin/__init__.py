"""APG M4 financial core (DRAFT, builder-made, non-production, standalone).  Blueprint: Section 05 (profitability calculation engine), Section 12 (retention, security,
carrying cost), Section 03 section 5 and 6 (canonical views and semantics).

Every figure is a plain dict (see figure.py) that says: the value, a state (authoritative | provisional | cannot_assess), the records that contributed, the credits,
duplicates and revisions that were applied, the records left out and why, the inputs that are unknown or disputed, and the policy and formula version used.
Calculations are PURE functions of a pinned snapshot of stored records and a stored policy, so they can be re-run from the stored record (calc_records.py).
Methods whose definition the locked text leaves open (CR-02 items A2 to A13) are CONFIGURATION in policy.py with no default; an unconfigured method gives
'cannot_assess' naming the open decision.  Nothing here settles an open decision or sets a threshold."""
FIN_VERSION = 'apg-fin-1'
