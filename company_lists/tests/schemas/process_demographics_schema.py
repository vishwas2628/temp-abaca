process_demographics_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "list": {"type": "string"},
            "companies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "number"},
                        "name": {"type": "string"},
                        "team_members_count": {"type": "number"},
                        "team_members_with_responses_count": {"type": "number"},
                        "responses": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"},
                                    "count": {"type": "number"},
                                    "percentage": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            "responses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "count": {"type": "number"},
                        "percentage": {"type": "number"},
                    },
                },
            },
            "companies_with_responses": {"type": "number"},
        },
    },
}
