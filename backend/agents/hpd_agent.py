from typing import TypedDict, Literal

from backend.agents.zillow_agent import ZillowAgentState


class ViolationRecord(TypedDict):
    violationid: str
    class_: str
    novdescription: str
    inspectiondate: str
    violationstatus: str
    rentimpairing: bool


class EnforcementRecord(TypedDict):
    source: Literal["AEP", "Charges", "Litigation", "Order"]
    date: str
    description: str
    is_active: bool                    # Meaningful for AEP/Litigation/Order. Always False for Charges (no in-progress concept)
    is_landlord_fault: bool | None     # Only meaningful for Charges (based on OMOStatusReason). None for other sources
    amount: float | None               # Only Charges has a value. None for other sources


class HPDAgentState(ZillowAgentState):
    hpd_violations: list[ViolationRecord]              # Raw violation records from Violation Files
    hpd_enforcement_records: list[EnforcementRecord]    # Combined AEP/Charges/Litigation/Order records
    violation_score: float                              # Aggregated severity score from violations
    enforcement_score: float                            # Aggregated severity score from enforcement records
    violations_fetch_success: bool                      # Whether the violation API call succeeded
    enforcement_fetch_success: bool                     # Whether the enforcement API calls succeeded
    hpd_severity_label: Literal["good", "caution", "danger"]   # Final severity label based on total_score

class HPDVerdictExplanation(TypedDict):
    severity_explanation: str
    negotiation_comment: str