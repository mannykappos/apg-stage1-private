"""Entity resolution.  Blueprint: Section 04 section 11 ("confidence alone must not authorise a material financial merge"; "must not force a match simply to clear
an exception queue"), acceptance PG-DI-AC-12.

Resolution ladder for a supplier reference, strongest first:
  1. the text IS a known supplier identifier                         -> resolved (stable_id)
  2. an APPROVED alias (a person approved the cross-reference)       -> resolved (approved_alias)
  3. the full name (legal words kept) equals exactly one supplier's full name -> resolved (exact_name); two such suppliers -> ambiguous
  4. anything else that resembles one or more suppliers              -> NOT resolved: 'needs_confirmation' (one resembling candidate) or 'ambiguous' (several)
  5. resembles none                                                  -> 'unresolved'
Resemblance (step 4) is only ever used to SHOW a reviewer the candidates.  It never selects one.  A person's decision is a separate, recorded step."""
import re, unicodedata
from dataclasses import dataclass

LEGAL_WORDS = {'pty', 'ltd', 'limited', 'inc', 'llc', 'co', 'company', 'proprietary', 'the'}
RESOLVED, AMBIGUOUS, NEEDS_CONFIRMATION, UNRESOLVED = 'resolved', 'ambiguous', 'needs_confirmation', 'unresolved'


def full_norm(text):
    """Lower-case words with brackets and punctuation removed, legal words KEPT.  Exact-name matching uses this, so 'SYN Metro Steel' is not 'SYN Metro Steel Pty Ltd'."""
    s = unicodedata.normalize('NFKC', str(text)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s)
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def name_tokens(text):
    """Lower-case word set with brackets, punctuation and legal-form words removed.  '(synthetic)' style tags in brackets are dropped."""
    s = unicodedata.normalize('NFKC', str(text)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return frozenset(w for w in s.split() if w not in LEGAL_WORDS)


@dataclass(frozen=True)
class SupplierMatch:
    status: str                  # resolved | ambiguous | needs_confirmation | unresolved
    supplier_id: object          # str when resolved, else None
    method: str
    candidates: tuple            # supplier ids a reviewer should look at (never an automatic choice)


class SupplierDirectory:
    """suppliers: iterable of (supplier_id, name).  aliases: iterable of (alias_text, supplier_id) that a person has APPROVED."""
    def __init__(self, suppliers, aliases=()):
        self._names, self._full = {}, {}
        for sid, name in suppliers:
            if not isinstance(sid, str) or not sid.strip():
                continue
            self._names[sid] = name_tokens(name)
            self._full.setdefault(full_norm(name), []).append(sid)
        self._alias = {}
        for text, sid in aliases:
            if sid in self._names:
                self._alias.setdefault(full_norm(text), set()).add(sid)

    def ids(self):
        return tuple(sorted(self._names))

    def resolve(self, text):
        if not isinstance(text, str) or not text.strip():
            return SupplierMatch(UNRESOLVED, None, 'blank', ())
        t = text.strip()
        if t in self._names:
            return SupplierMatch(RESOLVED, t, 'stable_id', ())
        toks = name_tokens(t)
        if not toks:
            return SupplierMatch(UNRESOLVED, None, 'no_usable_words', ())
        hit = self._alias.get(full_norm(t))
        if hit:
            return SupplierMatch(RESOLVED, next(iter(hit)), 'approved_alias', ()) if len(hit) == 1 else SupplierMatch(AMBIGUOUS, None, 'alias_points_to_several', tuple(sorted(hit)))
        exact = sorted(self._full.get(full_norm(t), ()))
        if len(exact) == 1:
            return SupplierMatch(RESOLVED, exact[0], 'exact_name', ())
        if len(exact) > 1:
            return SupplierMatch(AMBIGUOUS, None, 'identical_names', tuple(exact))
        like = sorted(s for s, n in self._names.items() if n and (toks <= n or n <= toks))
        if len(like) == 1:
            return SupplierMatch(NEEDS_CONFIRMATION, None, 'resembles_one', tuple(like))
        if len(like) > 1:
            return SupplierMatch(AMBIGUOUS, None, 'resembles_several', tuple(like))
        return SupplierMatch(UNRESOLVED, None, 'no_resemblance', ())
