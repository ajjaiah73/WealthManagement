"""Named compliance demo scenarios mapped to seeded client IDs. Not consumed
by the runtime pipeline itself — used by tests (and, later, the frontend) to
make the intended behavior of each mock client explicit and discoverable."""

SCENARIO_COMPLIANT = "compliant"
SCENARIO_WARNING = "warning"
SCENARIO_SELF_CORRECTION = "self_correction_then_compliant"
SCENARIO_REQUIRES_HUMAN_REVIEW = "requires_human_review"
SCENARIO_INCOMPLETE_FACT_FIND = "incomplete_fact_find"

CLIENT_SCENARIOS: dict[str, str] = {
    "C-0001": SCENARIO_COMPLIANT,
    "C-0002": SCENARIO_SELF_CORRECTION,
    "C-0003": SCENARIO_COMPLIANT,
    "C-0004": SCENARIO_REQUIRES_HUMAN_REVIEW,
    "C-0005": SCENARIO_INCOMPLETE_FACT_FIND,
    "C-0006": SCENARIO_WARNING,
    "C-0007": SCENARIO_COMPLIANT,
    "C-0008": SCENARIO_COMPLIANT,
    "C-0009": SCENARIO_COMPLIANT,
    "C-0010": SCENARIO_REQUIRES_HUMAN_REVIEW,
}
