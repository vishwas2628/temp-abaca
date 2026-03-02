from django.db import models

from simple_history.utils import bulk_create_with_history


class ResponseManager(models.Manager):
    def bulk_create_with_answers(self, data, user_profile, with_history=False):
        """
        A helper method to bulk create responses with answers as
        Django's built-in bulk create does not support m2m fields.
        """
        # 1 - First let's store the answers on a separate variable
        responses_with_answers = []
        for response in data:
            # Assign user profile:
            response['user_profile'] = user_profile

            # Store answers for later
            if 'answers' in response:
                responses_with_answers.append({
                    'question': response['question'].pk,
                    'answers': response.pop('answers')
                })

        # 2 - Create responses (without m2m fields)
        responses_to_create = [self.model(**response) for response in data]
        created_responses = bulk_create_with_history(
            responses_to_create, self.model, batch_size=500) if with_history else self.bulk_create(responses_to_create)

        # 3 - Prepare all answers from the responses to add them all in bulk
        through_models = []
        ThroughModel = self.model.answers.through
        for created_response in created_responses:
            response_answers = next((response['answers'] for response in responses_with_answers
                                     if response['question'] == created_response.question.pk),
                                    [])
            for answer in response_answers:
                through_models.append(ThroughModel(response=created_response, answer=answer))

        # 4 - Bulk create all selections of answers select on each response
        ThroughModel.objects.bulk_create(through_models)

        return created_responses
