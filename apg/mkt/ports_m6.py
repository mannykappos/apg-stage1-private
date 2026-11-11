"""PORTS added in M6 (handoff register EDR-09 MarketFeedPort and EDR-08 ExtractionRuntimePort).  Amir implements these on the real Engine and with real, licensed providers; the contract suites in
apg/mkt/contracts_m6.py define what an implementation must guarantee, including failure behaviour.  The in-memory references (reference_m6.py) are TEST DOUBLES, not designs and not providers: M6 names
no market-data vendor, connects to no feed and extracts from no real PDF, scan or e-mail.

MarketFeedPort rules (Blueprint Section 08 sections 7 and 14, Section 16; RFC-01 'do not invent market-data providers')
  * the tenant is taken only from a verified AuthenticatedContext; another tenant's series is indistinguishable from a missing one
  * a series is returned only when its licence status for THIS tenant is 'licensed'; 'unlicensed' and 'unknown' are refused, never defaulted to licensed
  * every observation carries an observation date, a source label, a geography, a unit and a kind; an observation missing any of them is never returned (it is counted as rejected)
  * observations are integers (scaled), never floats; none is dated after the as-of day; none is invented to fill a gap
  * freshness is judged against a limit the CALLER supplies (the procurement policy owns it): the port has no default, and stale data is reported 'stale', unavailable data 'unavailable'
  * two different values for one series and date are both reported with the date listed as conflicting; the port never picks one
ExtractionRuntimePort rules (Blueprint Section 04 section 12, Section 08 section 3)
  * an extracted value is a CLAIM about a document: every field is returned 'unverified'; the port never verifies and never marks a value authoritative
  * an unclear reading is reported ambiguous with its candidates and NO resolved value; the port never guesses
  * a field absent from the document is absent from the result (nothing is invented); text inside a document is data, never an instruction
  * the document hash is checked against the bytes; the result names the tool and version; the same document gives the same result
This port only reads.  What a person verifies, and what a rule may rely on, is decided by APG (apg/ingest/documents.py and the comparability gate), not by the port."""
from ..ports import PortError

OBS_FIELDS = ('obs_id', 'obs_date', 'value', 'unit', 'kind', 'source_label', 'geography', 'retrieved_at')
REQUIRED_TEXT = ('obs_date', 'unit', 'kind', 'source_label', 'geography')
LICENCE_STATES = ('licensed', 'unlicensed', 'unknown')
FRESHNESS_STATES = ('fresh', 'stale', 'unavailable')
MEDIA_TYPES = ('text/plain',)
MAX_DOCUMENT_BYTES = 1_000_000


class MarketFeedError(PortError):
    pass


class SeriesNotFound(MarketFeedError):
    """No such series for this tenant (also what another tenant's series looks like)."""


class LicenceRefused(MarketFeedError):
    """The series is not licensed for this tenant (unlicensed or unknown)."""


class ObservationInvalid(MarketFeedError):
    """An observation offered to the test seam is not well formed."""


class ExtractionError(PortError):
    pass


class DocumentInvalid(ExtractionError):
    """Not bytes, over-size, unsupported media type, or the hash does not match the bytes."""


class MarketFeedPort:
    def licence_status(self, ctx, series_id):
        """-> {series_id, status ('licensed' | 'unlicensed' | 'unknown'), terms_ref, checked_at}.  Raises SeriesNotFound for a series this tenant has no record of."""
        raise NotImplementedError

    def fetch(self, ctx, series_id, as_of, max_age_days):
        """-> {series_id, as_of, observations (ascending by date, none after as_of), rejected (count), conflicting_dates (list), freshness}.  Raises LicenceRefused when the series is not licensed
        for this tenant, SeriesNotFound when unknown, PayloadInvalid when as_of is not an ISO date or max_age_days is not a non-negative integer (there is no default)."""
        raise NotImplementedError

    def freshness(self, ctx, series_id, as_of, max_age_days):
        """-> {state ('fresh' | 'stale' | 'unavailable'), as_of, latest_obs_date, age_days, max_age_days}.  A series that may not be fetched may not have its freshness read either."""
        raise NotImplementedError

    # contract-test seams (test environments only)
    def _contract_load_series(self, tenant_id, series_id, observations, licence='licensed', terms_ref='SYNTHETIC-TERMS'):
        raise NotImplementedError


class ExtractionRuntimePort:
    def extract(self, ctx, document):
        """document = {doc_id, sha256, media_type, content (bytes)}.
        -> {doc_id, sha256, tool, tool_version, fields: [{name, text, location, candidates (list of ints), ambiguous (bool), why, confidence_bps (int 0..10000 or None), status ('unverified')}]}.
        An ambiguous field has no 'value' key.  Raises DocumentInvalid for a bad document, TenantMismatch for a document naming another tenant."""
        raise NotImplementedError
