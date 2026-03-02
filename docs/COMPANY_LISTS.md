# Company Lists

Another core feature of Abaca is Company Lists. This allows users (this is bidirectional, available for both Entrepreneurs and Supporter) to group together and organize companies they’re interested in.

In its simplest form, a Company List consists, pretty much, of a title, a description and a set of companies, which the owner can manually manage (add/remove companies).

Company Lists can also be shared with other Abaca users, or even guests, as they all have a shareable link (which contains their `uid`). For privacy and security reasons, it is possible to restrict access with a passcode and also view a list of users who have accessed the List.

Recently, this feature was expanded with the introduction of Smart Lists, which are explained further ahead.

Here’s an overview of the `company_lists.models.CompanyList` model:

- `title` – the name of the List
- `description` – a short paragraph to describe the List
- `owner` – the related `UserProfile` of the List owner
- `passcode` – a passcode other users must enter in order to access the List
- `previous_passcode` – the previous passcode, in order to track password changes
- `invited_users` – Abaca users who have accessed the list (many-to-many relationship to the `UserProfile` model)
- `invited_guests` – guest users who have accessed the list (many-to-many relationship to the `UserGuest` model)
- `companies` – the actual companies that compose the list (many-to-many relationship to the `Company` model)
- `pinned` – boolean flag to make the List show up at the top
- `company_list_type` – choice field that specifies the type of list (additional info below):
    - `0: COMPANY_LIST_TYPE_STATIC`
    - `1: COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS`
- `affiliate` – the related `Affiliate`, only relevant when `company_list_type = 1`

## Smart Lists

A Smart List – `company_list_type != 0` – is a special type of list, in which the user does not manually manage the companies that compose it. Instead, the list is dynamic, with companies being automatically added based on specific rules.

While it is expected that additional types of Smart Lists are introduced in the future, there is only a single type for now – Affiliate Submissions Smart Lists (`company_list_type = 1`).

Unlike regular/static Lists, these are associated with an `Affiliate`, and are automatically created for it. The purpose of these lists is to help tracking users/companies who make submissions to a given Affiliate – whoever submits gets automatically added to the List. This logic is implemented Django signals, in `/rest-api/viral/signals.py`.

## Sharing

Company Lists can be shared with other Abaca users of the same type (Entrepreneurs can only access lists from other Entrepreneurs), and also guests who do not have an account, as long as they identify themselves with name and email address.

All lists have a shareable public URL that includes the `uid`. Additionally, users have the possibility to restrict access through this URL with a passcode.

The owner of a list can, at any given time, regenerate the shareable link (and, consequently, the lists’s `uid`) or change the passcode.

## Exporting

The API endpoint that returns the details of a Company List, `/company-lists/{uid}/companies`, accepts a `?format=csv` parameter that makes the data be returned in CSV format. Using this endpoint, the UI allows users to export a Company List to a CSV file, with the following values:

- `uid`
- `name`
- `email`
- `website`
- `profile_url`
- `about`
- `location.street_address`
- `location.city`
- `location.region`
- `location.region_abbreviation`
- `location.country`
- `location.continent`
- `sectors`
- `supporter_types`
- `sectors_of_interest`
- `sector_groups_of_interest`
- `locations_of_interest`
- `location_groups_of_interest`
- `match_score`
- `connection_state`
- `VIL Range`