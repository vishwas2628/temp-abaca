# Affiliate Submissions

Submissions to Affiliates are represented by different models, depending on the type of user who makes them.

## Entrepreneur submissions

The model used to represent an Affiliate submission made by an Entrepreneur is `viral.models.AffiliateProgramEntry`. It has the following properties:

- `affiliate` – the related `Affiliate` model
- `user_profile` – the related `UserProfile` model
- `assessment` – the related `Assessment` model (more info below)
- `responses` – many to many relationship with the `Response` model
- `team_members` – team members data in JSON format

As  mentioned in [the Affiliates documentation](AFFILIATES.md), the first step of an Affiliate submission, for an Entrepreneur, is a self-assessment, which consists on the set of levels of the Company for each of the 8 VIRAL categories. Self assessments are also represented, on their own, by the `grid.models.Assessment` model. In fact, the current VIRAL level of a Company is precisely defined by the content of its latest `Assessment`. When an Entrepreneur submission is made, both `Assessment` and `AffiliateProgramEntry` instances are created and stored.

## Supporter submissions

When it comes to Supporters, the model that represents their submissions is `viral.modal.AffiliateProgramSupporterSubmission`, which has the following properties:

- `affiliate` – the related `Affiliate` model
- `supporter` – the related `Supporter` model
- `investing_level_range` – the VIL level range the Supporter is interested in
- `sectors_of_interest` – JSON list of sectors the Supporter is interested in
- `locations_of_interest` – JSON list of locations the Supporter is interested in
- `criteria` – many to many relationship with the `matching.models.Criteria` model; these are not explicitly defined by the user, but instead derived from the Affiliate’s questions
- `additional_criteria` – same as `criteria`, but these are manually selected by the user
- `team_members` – team members data in JSON format

## Submissions spreadsheets

Abaca leverages the Google Docs API to automatically generate a Google Sheets spreadsheet for each Affiliate and keep it updated with submission data. This only applies to Affiliates targeted at Entrepreneurs.

For this purpose, we use the [gspread](https://docs.gspread.org/) library. For API authentication, we use Google Service Accounts (these are discussed in both gspread’s and Google’s documentation pages). In the repository, within the `/rest-api/` directory, there are two JSON files with the credentials used (`client_secret_development.json` and `client_secret.json`). In `/rest-api/viral/utils.py` there is a `get_affiliate_spreadsheet()` helper method, in which either of these credentials is used depending on the environment being executed. In the same file are also defined the remaining functions used for this integration, to create and keep spreadsheets updated.

## Draft submissions

Recently (late 2023), draft submissions were introduced in Abaca. Upon starting a new submission, the frontend calls the `/affiliate-submission-drafts` API endpoint in order to create a new draft – `viral.models.AffiliateSubmissionDraft` – or retrieve an existing one, so it can be resumed. Drafts are progressively updated as the user advances through the form. Once submitted, the draft is deleted and an actual submission with the same data is recorded in the database.