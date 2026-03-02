# Team Members

In Abaca, users can add the details of their Team Members to their profile. We have the following `viral.models.TeamMember` model for this purpose:

- `id` – a UUID4, auto-generated identifier
- `company` – the related Company
- `first_name`
- `last_name`
- `email`
- `position`
- `is_active` – a boolean flag that hides the team member if set to `False`

There are two ways of managing Team Members – either during submission of an Affiliate that has `show_team_section == True`, or through a dedicated page accessible through the Profile (”Edit Team Members” button in the profile’s main block).

## Team Member Questions

With the introduction of Team Members, the Affiliate’s Questions feature was expanded to include questions specifically targeted at team members (e.g. demographic questions). This is determined by the `is_team_member_question` model property. During an Affiliate’s submission, these questions appear only in the Team Members step, and can/should be answered once per each team member. These kind of questions are not mandatory.
