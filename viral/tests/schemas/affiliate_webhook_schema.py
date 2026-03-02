from viral.models import AffiliateWebhook

from .location_schema import location

# WIP: To be used for tests
AFFILIATE_WEBHOOK_SCHEMA = {
    # TODO: Add Entrepreneurs schema
    # AffiliateWebhook.ENTREPRENEUR_PROGRAM: {}

    AffiliateWebhook.SUPPORTER_PROGRAM: {
        "type": "object",
        "definitions": {
            'location': location
        },
        "properties": {
            "submission_id": {
                "type": "integer"
            },
            "submitted_at": {
                "type": "string"
            },
            "abaca_id": {
                "type": "integer"
            },
            "abaca_profile": {
                "type": "string"
            },
            "affiliate_id": {
                "type": "integer"
            },
            "company_name": {
                "type": "string"
            },
            "email": {
                "type": "string"
            },
            "website": {
                "type": "string"
            },
            "location": {
                "$ref": "#/definitions/location"
            },
            "sectors": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": [
            "abaca_id",
            "abaca_profile",
            "company_name",
            "email",
            "location",
            "sectors",
            "submission_id",
            "submitted_at",
            "website"
        ]
    }
}
