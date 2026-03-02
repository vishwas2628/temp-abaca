from django.core.management.base import BaseCommand
from django.db.models import Q

from matching.models import Response, QuestionType, Criteria


class Command(BaseCommand):
    """
    This command was built to normalize existing matching criteria desired values and matching responses values:
    https://pixelmatters.atlassian.net/projects/VIR/issues/VIR-547
    """
    help = 'Normalize matching values'

    def handle(self, *args, **options):
        self.normalize_matching_response_values()
        self.normalize_matching_criteria_desired_values()

        print("\r")
        print("Finished matching values normalization")
        print("\r")

    def _remove_invalid_select_responses(self):
        invalid_select_responses = Response.objects.filter(
            Q(question__question_type__type=QuestionType.MULTI_SELECT, answers=None) | Q(question__question_type__type=QuestionType.SINGLE_SELECT, answers=None))

        if invalid_select_responses.exists():
            print("\r")
            print('Deleting invalid select responses...')
            invalid_count = len(invalid_select_responses)
            invalid_select_responses.delete()
            print('Invalid Select Responses deleted: ', invalid_count)

    def _handle_invalid_range_responses_values(self):
        range_responses = Response.objects.filter(
            question__question_type__type=QuestionType.RANGE)

        for response in range_responses:
            if type(response.value) is list:
                print("\r")
                print('Deleted invalid array like value: ', response.value)
                response.delete()

            elif type(response.value) is dict:
                min_value = response.value.get('min', None)
                max_value = response.value.get('max', None)
                has_string_values = type(
                    min_value) is str or type(max_value) is str

                if has_string_values:
                    print("\r")
                    print('Converted string values: ',
                          min_value + ' - ' + max_value)
                    response.value['min'] = int(min_value)
                    response.value['max'] = int(max_value)

                    if response.value['min'] < 0 or response.value['max'] < 0:
                        print("\r")
                        print('Delete invalid range: ',
                              min_value + ' - ' + max_value)
                        response.delete()
                    else:
                        response.save()

    def _handle_invalid_integer_responses_values(self):
        integer_responses = Response.objects.filter(
            question__question_type__type=QuestionType.NUMERIC)

        for response in integer_responses:
            if type(response.value) is str:
                integer_value = int(response.value)
                if integer_value < 0:
                    print("\r")
                    print('Deleted invalid value: ', integer_value)
                    response.delete()
                else:
                    response.value = {'value': integer_value}
                    response.save()

    def normalize_matching_response_values(self):
        self._remove_invalid_select_responses()
        self._handle_invalid_range_responses_values()
        self._handle_invalid_integer_responses_values()

    def _remove_invalid_select_criteria(self):
        invalid_select_criteria = Criteria.objects.filter(
            Q(question__question_type__type=QuestionType.MULTI_SELECT, answers=None) | Q(question__question_type__type=QuestionType.SINGLE_SELECT, answers=None))

        if invalid_select_criteria.exists():
            print("\r")
            print('Deleting invalid select criteria...')
            invalid_count = len(invalid_select_criteria)
            invalid_select_criteria.delete()
            print('Invalid Select Criteria deleted: ', invalid_count)

    def normalize_matching_criteria_desired_values(self):
        self._remove_invalid_select_criteria()
