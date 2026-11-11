"""PORT added in M5 (handoff register EDR-10 NotificationPort).  Amir implements it on the real Engine's notification service; the contract suite in apg/det/contracts_m5.py defines
what an implementation must guarantee, including failure behaviour.  The in-memory reference (reference_m5.py) is a test double, not a design.

NotificationPort rules (Blueprint: Section 06 section 9.1 alert-noise control, section 10 failed runs observable)
  * the tenant is taken only from a verified AuthenticatedContext; a note that names another tenant is refused
  * a note carries a DEDUP KEY chosen by APG; the same key in the same tenant is delivered AT MOST ONCE: a repeat is answered 'duplicate' with the first receipt, nothing is sent again
  * a delivery failure is VISIBLE: the receipt says 'failed', the note is listed by `outstanding`, it is never reported as delivered, and a later attempt with the same key is not
    treated as a duplicate (only a delivered note suppresses a repeat)
  * receipts and notes returned to a caller are independent copies
This port only moves a message.  Whether a message should be sent at all (suppression window, re-notification rules) is decided by APG (det/noise.py), not by the port."""
from ..ports import PortError

NOTE_FIELDS = ('dedup_key', 'recipient_role', 'subject', 'body', 'finding_id', 'reason')
MAX_TEXT = 2000


class NotificationInvalid(PortError):
    """The note is not well formed (missing field, wrong type, too long, float, control characters)."""


class NotificationPort:
    def send(self, ctx, note):
        """note = {dedup_key, recipient_role, subject, body, finding_id, reason} (all non-empty strings).
        -> receipt dict {receipt_id, dedup_key, status ('delivered' | 'duplicate' | 'failed'), attempts, error}.  Never raises for a transport failure: it answers 'failed'."""
        raise NotImplementedError

    def status(self, ctx, receipt_id):
        """-> receipt dict, or None when the receipt is unknown or belongs to another tenant."""
        raise NotImplementedError

    def outstanding(self, ctx):
        """-> tuple of receipts whose latest attempt failed and that have not been delivered since, ordered by receipt_id."""
        raise NotImplementedError

    # contract-test seams (test environments only)
    def _contract_set_transport_failure(self, failing):
        raise NotImplementedError

    def _contract_delivered(self, tenant_id):
        """-> list of the notes actually delivered for this tenant, in order."""
        raise NotImplementedError
