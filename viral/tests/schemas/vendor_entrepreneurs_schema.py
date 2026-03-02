from grid.tests.schemas.viral_assessment_schema import viral_assessment

from .location_schema import location

vendor_entrepreneur = {
    "type": "object",
    "properties": {
        "Abaca_ID": {
            "type": "integer"
        },
        "uid": {
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
            "type": [
                "null",
                "string"
            ]
        },
        "description": {
            "type": [
                "null",
                "string"
            ]
        },
        "logo": {
            "type": [
                "null",
                "string"
            ]
        },
        "location": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "object",
                    "allOf": [
                        {"$ref": "#/definitions/location"},

                        {
                            "properties": {
                                "id": {
                                    "type": "integer"
                                },
                                "created_at": {
                                    "type": "string"
                                },
                                "updated_at": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "created_at",
                                "id",
                                "updated_at"
                            ]
                        }
                    ]
                }
            ]
        },
        "created_at": {
            "type": "string"
        },
        "registration_date": {
            "type": "string"
        },
        "last_session": {
            "type": [
                "null",
                "string"
            ]
        },
        "sectors": {
            "type": ["array", "null"],
            "items": {
                "type": "string"
            }
        },
        "assessments": {
            "anyOf": [
                {"$ref": "#/definitions/viral_assessment"},
                {"type": "object", "maxProperties": 0}
            ]
        }
    },
    "required": [
        "Abaca_ID",
        "assessments",
        "company_name",
        "created_at",
        "description",
        "email",
        "last_session",
        "location",
        "logo",
        "registration_date",
        "sectors",
        "uid",
        "website"
    ]
}

LIST_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "definitions": {
        'location': location,
        'viral_assessment': viral_assessment
    },
    "type": "array",
    "items": {
        **vendor_entrepreneur
    }
}
