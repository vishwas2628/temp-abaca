response_value = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "maxLength": 1500},
        "value": {"type": "number"},
        "date": {"type": "string"},
        "min": {"type": "number"},
        "max": {"type": "number"},
    },
    "additionalProperties": True,
    # "oneOf": [{"required": ["text"]}, {"required": ["value"]}, {"required": ["date"]}, {"required": ["min", "max"]}],
}
