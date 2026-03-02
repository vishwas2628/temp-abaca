import os
import requests
import bugsnag

from viral.models import AffiliateWebhook


class AffiliateWebhookMixin:
    """
    A mixin that provides the method "send_submission_to_affiliate_webhooks"
    that when gets called, will submit to an Affiliate's webhooks a submission.
    """

    def send_submission_to_affiliate_webhooks(self, submission):
        # Helper method to submit all webhooks from an Affiliate
        for webhook in submission.affiliate.webhooks.all():
            self.submit_webhook(webhook, submission)

    def submit_webhook(self, webhook, submission):
        # 1 - Grab payload
        payload = self._get_payload(webhook.schema, submission)

        # 2 - Submit request
        self._send_request(webhook.url, payload)

    def _formatted_profile_link(self, company):
        return 'https://' + os.getenv('APP_BASE_URL', 'my.abaca.app') + '/profile/v/' + company.access_hash

    def _formatted_company_location(self, company):
        return company.locations.values(
            'formatted_address', 'latitude', 'longitude', 'city', 'region', 'region_abbreviation', 'country',
            'continent').first()

    def _formatted_supporter_investing_range(self, supporter):
        investing_range = [supporter.investing_level_range.lower, supporter.investing_level_range.upper]

        if supporter.investing_level_range.upper:
            # To include upper in range:
            investing_range[1] += 1
            return list(range(*investing_range))

        return list(filter(lambda value: bool(value), investing_range))

    def _formatted_supporter_types(self, supporter):
        return [supporter_type.name for supporter_type in supporter.types.all()]

    def _formatted_supporter_locations(self, supporter):
        # TEMP: To avoid circular dependency issue until serializers.py gets refactored into multiple files.
        from matching.serializers import SupporterLocationsOfInterestSerializer

        serialized_locations = SupporterLocationsOfInterestSerializer(supporter)
        return serialized_locations.data

    def _formatted_supporter_sectors(self, supporter):
        # TEMP: To avoid circular dependency issue until serializers.py gets refactored into multiple files.
        from matching.serializers import SupporterSectorsOfInterestSerializer

        serialized_sectors = SupporterSectorsOfInterestSerializer(supporter)
        return serialized_sectors.data

    def _formatted_supporter_questions(self, submission):
        # TEMP: To avoid circular dependency issue until serializers.py gets refactored into multiple files.
        from matching.serializers import SupporterCriteriaAffiliateSerializer

        serialized_questions = SupporterCriteriaAffiliateSerializer(submission.criteria, many=True)
        return serialized_questions.data

    def _formatted_supporter_interests(self, submission):
        # TEMP: To avoid circular dependency issue until serializers.py gets refactored into multiple files.
        from matching.serializers import SupporterCriteriaAffiliateSerializer

        serialized_interests = SupporterCriteriaAffiliateSerializer(submission.additional_criteria, many=True)
        return serialized_interests.data

    def _get_payload(self, schema, submission):
        payload = {}

        if schema == AffiliateWebhook.ENTREPRENEUR_PROGRAM:
            # TODO: Add entrepreneur schema (currently at: submit_affiliate_webhook)
            pass
        elif schema == AffiliateWebhook.SUPPORTER_PROGRAM:
            # TODO: Refactor into custom serializer
            payload = {
                "affiliate": submission.affiliate.id,
                "affiliate_name": submission.affiliate.name,
                "supporter": {
                    "id": submission.supporter.id,
                    "name": submission.supporter.name,
                    "investing_level_range": self._formatted_supporter_investing_range(submission.supporter),
                    "types": self._formatted_supporter_types(submission.supporter),
                    "locations_of_interest": self._formatted_supporter_locations(submission.supporter),
                    "sectors_of_interest": self._formatted_supporter_sectors(submission.supporter),
                },
                "questions": self._formatted_supporter_questions(submission),
                "interests": self._formatted_supporter_interests(submission),
                "submission": submission.uid,
                "submission_id": submission.id,
                "submission_link": f'{os.getenv("API_DOMAIN", "api.abaca.app")}/admin/viral/affiliateprogramsupportersubmission/{submission.id}',
                "submitted_at": submission.updated_at.strftime('%H:%M %m-%d-%Y')
            }

            if submission.supporter.user_profile:
                payload['supporter']['email'] = submission.supporter.user_profile.user.email
                payload['company'] = {
                    'id': submission.supporter.user_profile.company.id,
                    'uid': submission.supporter.user_profile.company.uid,
                    'website': submission.supporter.user_profile.company.website,
                    'about': submission.supporter.user_profile.company.about,
                    'location': self._formatted_company_location(submission.supporter.user_profile.company),
                    'profile_url': self._formatted_profile_link(submission.supporter.user_profile.company)
                }

        return payload

    def _send_request(self, url, payload):
        try:
            response = requests.post(url, json=payload)

            if not response.ok:
                bugsnag.notify(Exception("Yikes! Unexpected response while submitting webook."),
                               meta_data={"context": {"url": url, "payload": payload, "response": response}})

            return response
        except Exception as error:
            bugsnag.notify(Exception("Yikes! Error while submitting webook."),
                           meta_data={"context": {"url": url, "payload": payload, "error": error}})
