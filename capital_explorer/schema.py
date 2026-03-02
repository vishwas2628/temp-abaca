submission_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "question": {
                "type": "number",
            },
            "answers": {"type": "array", "items": {"type": "number"}},
        },
        "required": ["question", "answers"],
    },
}
