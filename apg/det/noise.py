"""Alert-noise control.  Blueprint: Section 06 section 9.1 (mandatory), PG-AI-AC-09.

DEDUPLICATION IDENTITY   one finding per (rule, scope, subject): signal.identity_of.  The same condition seen again updates that finding; it never creates a second one.
SUPPRESSION WINDOW       after a notification for a finding has been sent, further notifications for it are held back for `suppression_days` (policy), except the escalations below.
                         With no window configured, nothing is re-sent for ordinary changes at all (the quietest reading; the window is a policy decision, not a default).
RE-NOTIFICATION RULES    a notification is sent for exactly these events, each with its own dedup key so the port can never deliver one twice:
                           new               the first time a condition is detected                                         always
                           reopened          a resolved or dismissed finding came back with material new evidence           always (controlled reopening)
                           severity_increase the severity band rose (approved bands only)                                    if the policy lists it; ignores the window
                           status_transition a person moved the finding to a new status                                      if the policy lists it; inside the window it is held
                           material_evidence the evidence set changed (a new or revised source record)                       if the policy lists it; inside the window it is held
                         An unchanged repeat detection ('seen') never notifies.  A held notification is recorded as suppressed with the reason; it is not lost silently.
This module is a pure function of its arguments: no clock, no store, no port."""
from .. import canon
from ..fin.fmath import days_between
from . import policy as DP

ALWAYS = ('new', 'reopened')
BYPASS_WINDOW = ('new', 'reopened', 'severity_increase')


def dedup_key(finding_id, event, token):
    return f'{finding_id}|{event}|{token}'


def decide(finding_id, event, token, noise, last_sent_date, today):
    """-> {'send': bool, 'reason': event, 'dedup_key': str, 'why': str}.  `noise` is the policy's noise block or None; dates are ISO text."""
    key = dedup_key(finding_id, event, token)
    if event in ALWAYS:
        return {'send': True, 'reason': event, 'dedup_key': key, 'why': ''}
    listed = (noise or {}).get('renotify_on')
    if noise is None:
        return {'send': False, 'reason': event, 'dedup_key': key, 'why': 'NOISE_POLICY_NOT_CONFIGURED: only new and reopened findings notify'}
    if not listed or event not in listed:
        return {'send': False, 'reason': event, 'dedup_key': key, 'why': 'EVENT_NOT_LISTED_FOR_RENOTIFICATION'}
    if event in BYPASS_WINDOW:
        return {'send': True, 'reason': event, 'dedup_key': key, 'why': ''}
    win = noise.get('suppression_days')
    if last_sent_date is None:
        return {'send': True, 'reason': event, 'dedup_key': key, 'why': ''}
    if win is None:
        return {'send': False, 'reason': event, 'dedup_key': key, 'why': 'NO_SUPPRESSION_WINDOW_CONFIGURED: ordinary changes are not re-sent'}
    if days_between(last_sent_date, today) < win:
        return {'send': False, 'reason': event, 'dedup_key': key, 'why': 'INSIDE_SUPPRESSION_WINDOW: last sent %s, window %d days' % (last_sent_date, win)}
    return {'send': True, 'reason': event, 'dedup_key': key, 'why': ''}


def severity_increased(dp, old_label, new_label):
    return DP.severity_rank(dp, new_label) > DP.severity_rank(dp, old_label) and DP.severity_rank(dp, new_label) > 0


def evidence_changed(old_signal, new_signal):
    a = {(e['ref'], e['revision']) for e in old_signal['evidence']}
    b = {(e['ref'], e['revision']) for e in new_signal['evidence']}
    return a != b


def message(finding, event):
    s = finding['signal']
    q = s['quantification']
    amt = f"{q['gross_cents'] // 100:,}.{q['gross_cents'] % 100:02d} ({q['label']})" if q['status'] == 'quantified' else 'not quantified: ' + q['reason']
    subject = f"{finding['finding_id']} {event}: {s['taxonomy']['subtype']} ({finding['scope_key']})"
    body = (f"{s['explanation']['observed']}\nExpected: {s['explanation']['expected']}\nAmount: {amt}\nSeverity {s['priority']['severity']}; evidence strength {s['confidence']['evidence_strength']}; "
            f"status {finding['status']}.\nA signal is not a conclusion: a person reviews it.")
    return subject, body


def digest_token(signal):
    return canon.digest({'d': signal['state_digest']})[:12]
