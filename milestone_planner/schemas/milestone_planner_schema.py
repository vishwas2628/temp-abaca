from milestone_planner.schemas.milestone_schema import MILESTONE_LIST_SCHEMA


MILESTONE_PLANNER_OWNER_SCHEMA = {
    "type": "object",
    "properties": {
        "uid": {"type": "string"},
        "passcode": {"type": ["string", "null"]},
        "invited_users": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "user_profile": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                    "photo": {"type": ["string", "null"]},
                },
                "required": ["user_profile", "email", "name", "photo"]
            }
        },
        "invited_guests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                },
                "required": ["email", "name"]
            }
        },
    },
    "required": ["uid", "passcode", "invited_users", "invited_guests"]
}

LIST_OWNED_MILESTONE_PLANNERS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "array",
    "items": {
        **MILESTONE_PLANNER_OWNER_SCHEMA
    }
}

MILESTONE_PLANNER_GUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "uid": {"type": "string"},
        "company": {"type": "integer"},
        "milestones": MILESTONE_LIST_SCHEMA
    },
    "required": ["uid", "company", "milestones"]
}
