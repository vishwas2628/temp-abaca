viral_assessment = {
    "type": "object",
    "properties": {
        "Venture Investment Level": {
            "type": "object",
            "patternProperties": {
                ".+": {
                    "type": "integer"
                },
            },
            "required": [
                "Level"
            ]
        }
    },
    "required": [
        "Venture Investment Level"
    ]
}
