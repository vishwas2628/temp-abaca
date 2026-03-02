affiliate = {
    "type": "object",
    "properties": {
        "id": {
            "type": "integer"
        },
        "created_at": {
            "type": "string"
        },
        "updated_at": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "shortcode": {
            "type": "string"
        },
        "slug": {
            "type": "string"
        },
        "email": {
            "type": "string"
        },
        "additional_emails": {
            "type": ["array", "null"],
            "default": "null",
            "items": {
                "type": "string"
            }
        },
        "website": {
            "type": "string"
        },
        "logo": {
            "type": "string"
        },
        "spreadsheet": {
            "type": "string"
        },
        "flow_type": {
            "type": "integer"
        },
        "company": {
            "type": ["integer", "null"]
        },
        "supporters": {
            "type": "array",
            "default": [],
            "items": {
                "type": "integer"
            }
        },
        "networks": {
            "type": "array",
            "default": [],
            "items": {
                "type": "integer"
            }
        },
        "webhooks": {
            "type": "array",
            "default": [],
            "items": {
                "type": "integer"
            }
        }
    }
}
