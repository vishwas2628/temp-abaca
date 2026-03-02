from .Company import COMPANY


class AFFILIATE:
    FLOW_PROGRAM = 1
    FLOW_SELF_ASSESSMENT = 0

    FLOW_LABEL = {
        FLOW_PROGRAM: 'Self-Assessment flow',
        FLOW_SELF_ASSESSMENT: 'Program (Question Bundles) flow',
    }

    FLOW_TARGETS = (
        (COMPANY.ENTREPRENEUR, 'Entrepreneur'),
        (COMPANY.SUPPORTER, 'Supporter'),
    )
