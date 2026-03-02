QUESTION_SCHEMA = {
    "$id": "/schemas/question",
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "entrepreneur_question": {"type": "string"},
        "resource_question": {"type": "string"},
        "ttl": {"type": "string"},
        "profile_field": {"type": ["integer", "null"]},
        "short_name": {"type": ["string", "null"]},
        "question_type": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "meta": {
                    "type": "object",
                    "properties": {
                        "currency": {"type": "boolean"},
                    }
                }
            },
            "required": ["name", "type", "meta"]
        },
        "question_category": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string"},
            },
            "required": ["id", "name", "description"]
        },
    },
    "required": [
        "id",
        "entrepreneur_question",
        "resource_question",
        "ttl",
        "short_name",
        "question_type",
        "question_category",
    ]
}
