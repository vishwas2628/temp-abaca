location = {
    "type": "object",
    "properties": {
        "formatted_address": {
            "type": "string"
        },
        "latitude": {
            "type": "number"
        },
        "longitude": {
            "type": "number"
        },
        "city": {
            "type": [
                "null",
                "string"
            ]
        },
        "region": {
            "type": [
                "null",
                "string"
            ]
        },
        "region_abbreviation": {
            "type": [
                "null",
                "string"
            ]
        },
        "country": {
            "type": "string"
        },
        "continent": {
            "type": "string"
        }
    },
    "required": [
        "city",
        "continent",
        "country",
        "formatted_address",
        "latitude",
        "longitude",
        "region",
        "region_abbreviation"
    ]
}
