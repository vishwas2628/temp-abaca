criteria_desired = {
    "type": "object",
    "properties": {
        "value": {
            "type": "number"
        },
        "min": {
            "type": "number"
        },
        "max": {
            "type": "number"
        },
        "text": {
            "type": "string"
        },
        "date": {
            "type": "string"
        }
    },
    "oneOf": [
        {
            "required": [
                "value"
            ]
        },
        {
            "required": [
                "min",
                "max"
            ]
        },
        {
            "required": [
                "text"
            ]
        },
        {
            "required": [
                "date"
            ]
        }
    ]
}
