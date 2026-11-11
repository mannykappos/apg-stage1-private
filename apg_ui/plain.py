"""Plain-language wording for the codes APG returns, for the prototype screens.  The code itself is always shown next to the words (and in the evidence panel), so a reader
can check the wording against what APG recorded.  A code with no entry here is shown as recorded, with no invented explanation.  The wording is the builder's; nothing here
changes what a code means."""

STATES = {'authoritative': 'Authoritative', 'provisional': 'Provisional', 'cannot_assess': 'Cannot assess'}

PREFIXES = (
    ('COMPONENT_PROVISIONAL:', 'one of the figures this is built from is provisional'),
    ('COMPONENT_CANNOT_ASSESS:', 'one of the figures this is built from cannot be assessed'),
    ('A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED', 'a part this figure is defined to include cannot be assessed, so the figure is not shown'),
    ('POLICY_NOT_APPROVED:', 'the policy it was calculated under is not approved'),
    ('ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED', 'costs recorded after the forecast date are not added to the forecast'),
    ('PERCENT_COMPLETE_IS_COST_TO_COST_ON_THE_FORECAST_FINAL_COST', 'percentage complete is cost incurred over forecast final cost'),
    ('EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED', 'the retention release date has passed and the money is not released, so its forward cost cannot be estimated'),
    ('RELEASE_REVIEW_DUE', 'the retention release date has passed: review the release'),
    ('CONTRACT_SUMMARY_DISAGREES_WITH_REGISTER', 'the contract summary and the variation register disagree'),
    ('SOURCE_EMPTY', 'the source sent no records for a record type that is expected to have them'),
    ('BUDGET_EXCEEDED_BY:', 'actual cost already exceeds the budget for this cost code'),
    ('SUPPLIER_AMBIGUOUS:', 'the invoice could belong to more than one supplier'),
    ('SECONDARY_DISAGREES:', 'a second system disagrees with the accounting record'),
    ('CRITICAL_VALUE_MISSING:', 'a value needed for the figures is missing'),
    ('DUPLICATE_CANDIDATE', 'this may be a duplicate of another record'),
    ('DUPLICATE_OF:', 'a duplicate delivery of an earlier record'),
    ('FINDING_NOT_REVIEWED', 'nobody has reviewed the finding yet'),
    ('EVIDENCE_MISSING', 'information treated as critical is missing'),
    ('AMOUNT_QUALIFIED', 'the amount rests on an assumption'),
    ('AMOUNT_UNQUANTIFIED', 'there is no defensible amount'),
    ('GATE:not_comparable', 'the offer does not meet the specification'),
    ('GATE:partially_comparable', 'the offer can only partly be compared'),
    ('FRESHNESS:qualified', 'some of the evidence is older than the policy prefers'),
    ('LANDED_COST_INCOMPLETE', 'the landed cost is missing parts, so the total is a lower bound'),
    ('INTERNATIONAL_CHECKS_UNRESOLVED', 'import checks are not resolved'),
    ('SUBSTITUTION_NEEDS_APPROVAL', 'a substitution needs a person to approve it'),
    ('PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL', 'percentage complete rests on a forecast that is provisional'),
    ('DATA_QUALITY_FINDING', 'this finding is about the data itself, so the next step is to fix the data'),
    ('INVOICED_EXCEEDS_COMMITMENT:', 'more has been invoiced than the order commits'),
    ('EVIDENCE_WEAK', 'the evidence is weak'),
    ('CTC_UNKNOWN:', 'the cost to complete for this cost code is not known'),
    ('FORECAST_DERIVED_FROM_BUDGET_NO_DECLARED_VERSION', 'the forecast is derived from the budget because no forecast version is declared'),
    ('ACTION_IN_HAND', 'an action is already approved or under way'),
    ('CONFLICT_SAME_KEY', 'two deliveries with the same key disagree'),
    ('PAYMENT_TARGET_NOT_VISIBLE:', 'the invoice this payment is for is not visible'),
)


def reason(code):
    """-> {'code', 'plain'}: the code as recorded, and the builder's wording or None."""
    text = str(code)
    for pre, words in PREFIXES:
        if text.startswith(pre):
            return {'code': text, 'plain': words}
    return {'code': text, 'plain': None}


KINDS = {'saving_opportunity': 'Possible lower cost (an opportunity, not a saving)', 'fx_stale_or_diverging': 'Exchange rate stale or diverging'}


def kind(subtype):
    """The name a screen gives a finding's subtype.  APG's own subtype is kept in the finding's evidence."""
    return KINDS.get(subtype) or humanise(subtype)


def humanise(token):
    return str(token).replace('_', ' ').strip().capitalize() if token else ''
