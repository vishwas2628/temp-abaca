import bugsnag

from rest_framework import status
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext as _
from jsonschema.exceptions import ValidationError as JSONValidationError
from jsonschema.validators import validate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.models import Consent
from viral.models import Company
from viral.models import Affiliate
from viral.models import AffiliateSubmissionDraft
from viral.signals import finished_affiliate_flow
from company_lists.models import CompanyList
from sdg.models.sdg_response import Response as SDGResponse
from sdg.models.sdg_affiliate_program_entry import SDGAffiliateProgramEntry
from matching.tests.schemas.response_value_schema import response_value
from sdg.serializers.question_bundle_response_serializer import (
    QuestionBundleResponseSerializer,
)
from viral.utils import add_affiliate_program_entry_to_google_sheet


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sdg_submissions(request):
    try:
        draft = AffiliateSubmissionDraft.objects.get(  # pyright: ignore[reportAttributeAccessIssue]
            user=request.user,
            id=request.data.get('draft_id'),
        )

        affiliate = draft.affiliate
        user_profile = request.user.userprofile
        company = user_profile.company
        responses_data = draft.data.get('responses', [])
        response_is_valid = validate_response(responses_data, True)

        if not response_is_valid:
            return Response(
                {'errors': [_('Missing data.')]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        responses = save_response(
            response_data=responses_data,
            user_profile=user_profile,
        )
        populate_affiliate_company_lists(
            affiliate=affiliate,
            company=company,
        )

        if user_profile.company.type == Company.ENTREPRENEUR:
            program_entry = SDGAffiliateProgramEntry.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
                affiliate=affiliate,
                user_profile=user_profile,
            )

            program_entry.responses.set(responses)
            program_entry.save()
            Consent.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
                user=request.user,
                consent_type=Consent.SDG_REPORT_TYPE,
            )

            # add_affiliate_program_entry_to_google_sheet(program_entry)
            # finished_affiliate_flow.send(
            #     sender='SDGAffiliateSubmissions',
            #     user_profile=user_profile,
            #     affiliate=affiliate,
            #     entrepreneur_company=company,
            #     program_entry=program_entry,
            # )


        draft.delete()
        return Response(status=status.HTTP_201_CREATED)
    except (ValidationError, AffiliateSubmissionDraft.DoesNotExist):  # pyright: ignore[reportAttributeAccessIssue]
        return Response(status=status.HTTP_400_BAD_REQUEST)


def validate_response(data, required=True):
    for response in data:
        if 'value' in response:
            if all(
                [
                    not required,
                    not response['value'].get('value'),
                    not response['value'].get('text'),
                    not response['value'].get('min'),
                    not response['value'].get('max'),
                ]
            ):
                return True
            try:
                validate(response['value'], schema=response_value)
                if 'min' in response['value'] and 'max' in response['value']:
                    if response['value']['min'] > response['value']['max']:
                        return False
                elif 'text' in response['value'] and not response['value']['text']:
                    return False
                return True
            except JSONValidationError:
                return False
        else:
            return bool(response.get('answers', [])) or not required


def save_response(response_data, user_profile):
    responseWithSDG = list(filter(lambda response: response.get("isSDG", False), response_data))
    for response in responseWithSDG:
        response["value"] = {"optionIds": response["answers"]}
        if response.get("sdgdetails", False):
            response["value"]["options"] = response["sdgdetails"]["options"]
            response["sdgdetails"] = {}
        response["answers"] = []

    responseWithoutSDG = list(filter(lambda response: not response.get('isSDG', False), response_data))
    formatted_responses = responseWithSDG + responseWithoutSDG
    serializer = QuestionBundleResponseSerializer(
        data=formatted_responses,
        many=True,
    )
    serializer.is_valid()
    responses = []
    for data in serializer.validated_data:  # pyright: ignore[reportGeneralTypeIssues, reportOptionalIterable]
        if data.get("question") is not None:
            response = SDGResponse.objects.create(
                question_id=data.get("question").id,
                user_profile=user_profile,
                value=data.get('value'),
            )
            response.answers.set(data.get('answers', []))
            responses.append(response)

    return responses


def populate_affiliate_company_lists(affiliate: Affiliate, company: Company) -> None:
    # Include:
    # - lists explicitly linked to this affiliate via `Affiliate.company_lists`
    # - the auto-created "Affiliate Submissions" smart list (`CompanyList.affiliate`)
    linked_lists = affiliate.company_lists.all()  # pyright: ignore[reportAttributeAccessIssue]
    smart_list = CompanyList.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        company_list_type=CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS,
        affiliate=affiliate,
    )

    candidate_lists = CompanyList.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        Q(pk__in=linked_lists.values("pk")) | Q(pk__in=smart_list.values("pk"))
    ).distinct()

    # NOTE: Avoid `exclude(companies__pk=...)` on an M2M: it can drop lists that have
    # zero companies due to INNER JOIN semantics. Using a pk-subquery preserves empty lists.
    company_lists_to_populate = candidate_lists.exclude(
        pk__in=candidate_lists.filter(companies__pk=company.pk).values("pk")
    )

    # Only (easy) way to bulk create/update m2m fields:
    through_model = CompanyList.companies.through  # pyright: ignore[reportAttributeAccessIssue]
    through_model.objects.bulk_create(
        [
            through_model(companylist_id=pk, company_id=company.pk)
            for pk in company_lists_to_populate.values_list('pk', flat=True)
        ],
        ignore_conflicts=True,
    )
