MILESTONE_SCHEMA = {
    "type": "object",
    "properties": {
        "uid": {"type": "string"},
        "user_profile": {"type": "string"},
        "category_level": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "achievements": {"type": "string"},
                "requirements": {"type": "string"},
                "next_milestones_title": {"type": "string"},
                "next_milestones_description": {"type": "string"},
                "achieved_milestones_title": {"type": "string"},
                "achieved_milestones_description": {"type": "string"},
                "level": {
                    "type": "integer",
                    "description": "Level value"
                },
                "category": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "requirements": {"type": "string"},
                        "color": {"type": "string"},
                        "abbreviation": {"type": "string"}
                    }
                }
            },
            "required": [
                "description",
                "achievements",
                "requirements",
                "next_milestones_title",
                "next_milestones_description",
                "achieved_milestones_title",
                "achieved_milestones_description",
                "level",
                "category"
            ]
        },
        "strategy": {"type": "string"},
        "outcomes": {"type": "string"},
        "resources": {"type": "string"},
        "finances_needed": {
            "type": ["number", "null"],
            "minimum": 0
        },
        "target_date": {
            "type": ["string", "null"],
            "format": "date-time"
        },
        "plan_published": {
            "type": "boolean",
            "default": False
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Answer value"
                        }
                    },
                    "question": {
                        "type": "integer",
                        "description": "Question Id"
                    }
                },
                "required": [
                    "value",
                    "answers",
                    "question"
                ]
            }
        },
        "date_of_completion": {
            "type": ["string", "null"],
            "format": "date-time"
        },
        "evidence_published": {
            "type": "boolean",
            "default": False
        },
        "critical": {
            "type": "boolean",
            "default": False
        },
        "state": {
            "enum": ["to-be-planned", "planned", "in-progress", "completed"]
        },
        "created_at": {
            "type": "string",
            "format": "date-time"
        },
        "updated_at": {
            "type": "string",
            "format": "date-time"
        }
    },
    "required": [
        "uid",
        "user_profile",
        "category_level",
        "strategy",
        "outcomes",
        "resources",
        "finances_needed",
        "target_date",
        "plan_published",
        "evidence",
        "date_of_completion",
        "evidence_published",
        "critical",
        "created_at",
        "updated_at"
    ]
}

MILESTONE_LIST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "array",
    "items": {
        **MILESTONE_SCHEMA
    }
}
