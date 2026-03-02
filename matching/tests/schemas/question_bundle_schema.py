from matching.tests.schemas.question_schema import QUESTION_SCHEMA


QUESTION_BUNDLE_SCHEMA = {
    "type": "object",
    "definitions": {
        "question": QUESTION_SCHEMA,
    },
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "supporter": {"type": "integer"},
        "category": {"type": ["integer", "null"]},
        "category_level": {"type": ["integer", "null"]},
        "questions": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/question"
            }
        }
    },
    "required": [
        "id",
        "name",
        "supporter",
        "category",
        "category_level",
        "questions"
    ]
}

PAGINATED_LIST_OF_QUESTION_BUNDLES_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "type": "object",
    "definitions": {
        "question": QUESTION_SCHEMA,
        "question_bundle": QUESTION_BUNDLE_SCHEMA,
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
                "$ref": "#/definitions/question_bundle"
            },
        }
    },
    "required": [
        "count",
        "previous",
        "next",
        "results"
    ]
}
