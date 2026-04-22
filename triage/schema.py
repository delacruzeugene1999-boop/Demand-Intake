"""JSON Schema for the structured triage output.

The model is constrained to emit a JSON object matching this schema. The 14
sections map 1:1 to the BPI Demand Screening and Triage Manual output spec.
"""

OVERLAY_NAMES = [
    "Architecture",
    "Cybersecurity",
    "Data/Privacy",
    "Reporting/Regulatory",
    "AI/Model Risk",
    "Vendor/Procurement",
    "PMO/Governance",
]

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "demand_intake_status": {
            "type": "string",
            "enum": [
                "complete_for_triage",
                "incomplete_for_triage",
                "clarification_required",
            ],
            "description": "Outcome of Step 2 minimum completeness check.",
        },
        "completeness_assessment": {
            "type": "object",
            "properties": {
                "mandatory_fields_present": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "missing_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "assumptions_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "can_continue_safely": {"type": "boolean"},
            },
            "required": [
                "mandatory_fields_present",
                "missing_fields",
                "assumptions_used",
                "can_continue_safely",
            ],
            "additionalProperties": False,
        },
        "service_family_routing": {
            "type": "object",
            "properties": {
                "primary_family": {
                    "type": "string",
                    "enum": [
                        "DCG",
                        "ISG-Applications",
                        "ISG-Infrastructure",
                        "CEDA",
                        "Disputed",
                    ],
                },
                "specific_subfamily": {"type": "string"},
                "rationale": {"type": "string"},
                "secondary_families": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "routing_ambiguity": {"type": "boolean"},
            },
            "required": [
                "primary_family",
                "specific_subfamily",
                "rationale",
                "secondary_families",
                "routing_ambiguity",
            ],
            "additionalProperties": False,
        },
        "run_type": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["Run", "Grow", "Innovate"]},
                "rationale": {"type": "string"},
            },
            "required": ["type", "rationale"],
            "additionalProperties": False,
        },
        "subtype": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["BAU", "MR", "Project", "PoC", "Pilot"],
                },
                "rationale": {"type": "string"},
                "disqualifiers_or_escalators": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["type", "rationale", "disqualifiers_or_escalators"],
            "additionalProperties": False,
        },
        "program_affiliation": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "stand_alone",
                        "under_existing_program",
                        "recommend_program",
                        "not_applicable",
                    ],
                },
                "rationale": {"type": "string"},
            },
            "required": ["type", "rationale"],
            "additionalProperties": False,
        },
        "materiality": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["Tier 1", "Tier 2", "Tier 3"],
                },
                "rationale": {"type": "string"},
            },
            "required": ["tier", "rationale"],
            "additionalProperties": False,
        },
        "overlay_triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "overlay": {"type": "string", "enum": OVERLAY_NAMES},
                    "triggered": {"type": "boolean"},
                    "rationale": {"type": "string"},
                    "consultation_type": {
                        "type": "string",
                        "enum": ["mandatory", "by_exception", "not_needed"],
                    },
                },
                "required": [
                    "overlay",
                    "triggered",
                    "rationale",
                    "consultation_type",
                ],
                "additionalProperties": False,
            },
        },
        "effort_and_cost_bands": {
            "type": "object",
            "properties": {
                "effort_band": {
                    "type": "string",
                    "enum": ["E0", "E1", "E2", "E3", "E4", "E5"],
                },
                "cost_band": {
                    "type": "string",
                    "enum": ["C0", "C1", "C2", "C3", "C4", "C5"],
                },
                "estimate_basis": {"type": "string"},
                "confidence_level": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low"],
                },
                "quick_estimate_huddle_needed": {"type": "boolean"},
            },
            "required": [
                "effort_band",
                "cost_band",
                "estimate_basis",
                "confidence_level",
                "quick_estimate_huddle_needed",
            ],
            "additionalProperties": False,
        },
        "provisional_delivery_path": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "enum": ["Agile", "Waterfall", "Infra Build", "Innovation"],
                },
                "rationale": {"type": "string"},
            },
            "required": ["path", "rationale"],
            "additionalProperties": False,
        },
        "recommended_next_owner_forum": {
            "type": "object",
            "properties": {
                "owner_or_forum": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["owner_or_forum", "rationale"],
            "additionalProperties": False,
        },
        "g1_triage_recommendation": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "proceed_to_receiving_queue",
                        "proceed_to_shaping_lane",
                        "hold_for_clarification",
                        "escalate_routing_dispute",
                        "escalate_materiality_overlay_review",
                        "exception_memo_required",
                        "retroactive_fast_track_regularization",
                    ],
                },
                "rationale": {"type": "string"},
            },
            "required": ["action", "rationale"],
            "additionalProperties": False,
        },
        "triage_note_draft": {
            "type": "string",
            "description": "5-8 sentence audit-friendly triage note.",
        },
        "confidence_and_escalation": {
            "type": "object",
            "properties": {
                "overall_confidence": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low"],
                },
                "uncertainty_drivers": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "human_review_mandatory": {"type": "boolean"},
                "escalation_items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "overall_confidence",
                "uncertainty_drivers",
                "human_review_mandatory",
                "escalation_items",
            ],
            "additionalProperties": False,
        },
    },
    "required": [
        "demand_intake_status",
        "completeness_assessment",
        "service_family_routing",
        "run_type",
        "subtype",
        "program_affiliation",
        "materiality",
        "overlay_triggers",
        "effort_and_cost_bands",
        "provisional_delivery_path",
        "recommended_next_owner_forum",
        "g1_triage_recommendation",
        "triage_note_draft",
        "confidence_and_escalation",
    ],
    "additionalProperties": False,
}
