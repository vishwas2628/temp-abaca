from .location_schema import location

vendor_supporter = {
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
            "type": "string"
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
            "type": "null"
        },
        "supporter": {
            "type": "object",
            "properties": {
                "investing_level_range": {
                    "type": "array",
                    "items": {
                        "type": [
                            "integer",
                            "null"
                        ]
                    }
                },
                "sectors_of_interest": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "locations_of_interest": {
                    "type": "array",
                    "items": {
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
                }
            },
            "required": [
                "investing_level_range",
                "locations_of_interest",
                "sectors_of_interest"
            ]
        }
    },
    "required": [
        "Abaca_ID",
        "company_name",
        "created_at",
        "description",
        "email",
        "last_session",
        "location",
        "logo",
        "registration_date",
        "supporter",
        "uid",
        "website"
    ]
}

LIST_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "definitions": {
        'location': location
    },
    "type": "array",
    "items": {
        **vendor_supporter
    }
}
