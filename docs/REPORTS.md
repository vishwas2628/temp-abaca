# Reports

This is Abaca’s most recent module and is currently being developed yet. It consists of a dashboard with a wide range of graphs, charts and data tables.

This is only available for Supporters with an active Pro subscription.

## List Reports

This section of the dashboard displays stats about the Companies included in a given Company List. The stats consist of demographic data about Team Members, which are based in answers to specific Questions (gender, ethnicity and sexual orientation) provided by these Companies during Affiliate submissions.

It is supported by a single API endpoint: `/demographic-composition/`, which takes as input two query parameters:

- `list_uid` – the `uid` of a Company List owned by the authenticated user
- `question` – the `id` or `slug` (both can be used) of a Question (one of the three demographic questions mentioned above)

The frontend UI allows the user to select different values in order to retrieve different results.

The logic for this endpoint is in `viral.views.FetchListDemographicCompositionView`, and basically consists of fetching *Responses* to the selected *Question*, by each *Company* in the *Company List*, and calculate several stats.

The a sample response from this endpoint might look something like this:

```json
{
  "question": "How would you describe your gender identity",
  "companies": [
    {
      "name": "Scott-Woods",
      "id": 35,
      "team_members_count": 0,
      "team_members_with_responses_count": 0,
      "responses": [
        {
          "value": "Woman",
          "count": 3,
          "percentage": 0.5
        }
      ]
    },
    {...}
  ],
  "responses": [
    {
      "value": "Prefer not to say",
      "count": 17,
      "percentage": 0.20481927710843373
    },
    {...}
  ],
  "companies_with_responses": 15
}
```

## Process Reports

This section has several similarities with the List Reports, but the set of Companies differs. Instead of selecting a *Company List*, in this case, the user selects a *Process.*

<aside>
💡 A Process, in Abaca, is an entity that belongs to a single user and contains one or more Process Steps. Each Step is associated with a specific Company List. This is represented by the `company_lists.models.Process` and `company_lists.models.ProcessStep` models.

</aside>

The API provides two Process-related endpoints – `/user/processes/` to list all Processes of the authenticated user and `/user/processes/{id}` to retrieve the details of a given Process, including its Steps and the respective Company List IDs.

Then, for the actual stats that feed the dashboard, there is the `/user/processes/{id}/demographic-stats/` endpoint, which works very similarly to the List Reports one described in the previous section – it accepts the `process` and `question` query parameters. The returned data is a bit more complex given the structure of Processes. Here’s a sample:

```json
[
  {
    "step": "Pipeline",
    "companies": [
      {
        "id": 651,
        "name": "Demographic Mock 2",
        "team_members_count": 6,
        "team_members_with_responses_count": 6,
        "responses": [
          {
            "value": "Unsure",
            "count": 1,
            "percentage": 0.16666666666666666
          },
          {...}
        ]
      },
      {...}
    ],
    "responses": [
      {
        "value": "Prefer not to say",
        "count": 40,
        "percentage": 0.2564102564102564
      },
      {...}
    ],
    "companies_with_responses": 25,
    "is_locked": false
  },
  {...}
]

```

## Milestone Progress

This hasn’t been implemented yet.