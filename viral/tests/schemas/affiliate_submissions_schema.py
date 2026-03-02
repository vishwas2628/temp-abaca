from grid.tests.schemas.viral_assessment_schema import viral_assessment

from .affiliate_schema import affiliate
from .location_schema import location

affiliate_submission = {
    "type": "object",
    "properties": {
        "submission_ID": {
            "type": "integer"
        },
        "submission_link": {
            "type": "string"
        },
        "submitted_at": {
            "type": "string"
        },
        "Abaca_ID": {
            "type": "integer"
        },
        "Abaca_profile": {
            "type": "string"
        },
        "company_name": {
            "type": "string"
        },
        "email": {
            "type": [
                "null",
                "string"
            ]
        },
        "website": {
            "type": "string"
        },
        "location": {
            "$ref": "#/definitions/location"
        },
        "sectors": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "assessments": {
            "$ref": "#/definitions/viral_assessment"
        },
        "questions": {
            "type": "object",
            "patternProperties": {
                ".+": {
                    "type": ["array", "object"],
                    "items": {
                        "type": "string"
                    },
                    "properties": {
                        "text": {
                            "type": "string"
                        }
                    }
                }
            }
        },
        "match_scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "supporter_ID": {
                        "type": "integer"
                    },
                    "supporter_name": {
                        "type": "string"
                    },
                    "match_score": {
                        "type": "integer"
                    },
                    "match_summary": {
                        "type": "string"
                    }
                },
                "required": [
                    "match_score",
                    "match_summary",
                    "supporter_ID",
                    "supporter_name"
                ]
            }
        }
    },
    "required": [
        "Abaca_ID",
        "Abaca_profile",
        "assessments",
        "company_name",
        "email",
        "location",
        "match_scores",
        "questions",
        "sectors",
        "submission_ID",
        "submission_link",
        "submitted_at",
        "website"
    ]
}

LIST_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "type": "object",
    "definitions": {
        'location': location,
        'affiliate': affiliate,
        'affiliate_submission': affiliate_submission,
        'viral_assessment': viral_assessment
    },
    "properties": {
        "count": {
            "type": "integer"
        },
        "previous": {
            "type": ["string", "null"]
        },
        "next": {
            "type": ["string", "null"]
        },
        "results": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/affiliate_submission"
            },
        },
        "affiliate": {
            "$ref": "#/definitions/affiliate"
        },
    },
    "required": [
        "count",
        "previous",
        "next",
        "results",
        "affiliate"
    ]
}

DETAIL_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "definitions": {
        'location': location,
        'affiliate': affiliate,
        'viral_assessment': viral_assessment
    },
    **affiliate_submission
}
