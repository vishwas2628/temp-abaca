import os
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_405_METHOD_NOT_ALLOWED
from rest_framework.views import APIView

from capital_explorer.models import CriteriaWeight, FundingSource, Submission
from capital_explorer.permissions import CanViewSubmission
from capital_explorer.serializers import FundingSourceSerializer, OwnerSubmissionSerializer, ViewerSubmissionSerializer
from matching.models.question_bundle import QuestionBundle
from shared.mailjet.mailjet import sendEmailWithoutTemplate
from shared.models.unique_uid import random_uid
from viral.models import UserGuest


class CapitalExplorerView(APIView):
    def get(self, request):
        from matching.serializers import QuestionSerializer

        questions = {}
        for question_bundle in QuestionBundle.objects.filter(capital_explorer=True):
            for question in question_bundle.questions.all():
                if question.id not in questions:
                    questions[question.id] = question

        weights = CriteriaWeight.objects.order_by('id').values_list(
            'value_matched', 'value_unmatched', 'value_unanswered'
        )

        data = {
            'questions': QuestionSerializer(list(questions.values()), many=True).data,
            'funding_sources': FundingSourceSerializer(FundingSource.objects.all(), many=True).data,
            'weights': {
                'matched': [weight[0] for weight in weights],
                'unmatched': [weight[1] for weight in weights],
                'unanswered': [weight[2] for weight in weights],
            },
        }

        return Response(data)


class ListSubmissionView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnerSubmissionSerializer

    def get_queryset(self):
        return Submission.objects.filter(company__company_profile__user=self.request.user)

    def get(self, request):
        submissions = self.get_queryset()
        if submissions.count() == 0:
            submissions = [Submission.objects.create(company=request.user.userprofile.company, responses=[])]
        return Response(self.get_serializer(submissions, many=True).data)


class RetrieveSubmissionView(RetrieveAPIView):
    lookup_field = 'uid'
    serializer_class = ViewerSubmissionSerializer
    permission_classes = [CanViewSubmission]
    queryset = Submission.objects.select_related('company').all()

    def retrieve(self, request, *args, **kwargs):
        submission = self.get_object()

        # If the user is not logged in
        if not request.user.is_authenticated:
            # and a guest email was provided
            if user_guest := UserGuest.objects.filter(email__iexact=request.GET.get('email')).first():
                # add it to the list of invited guests
                submission.invited_guests.add(user_guest)

        return Response(self.get_serializer(submission).data)


class PatchSubmissionView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnerSubmissionSerializer

    def get_queryset(self):
        return Submission.objects.select_related('company').filter(company__company_profile__user=self.request.user)

    def _send_updated_invitation_emails(self, submission):
        users = submission.invited_users.all()

        if users.count() == 0:
            return

        link = f'https://{os.getenv("APP_BASE_URL", "my.abaca.app")}/capital-explorer/{submission.uid}'

        subject = f"Update: {submission.company.name} made changes to access info for Capital Explorer Results"

        message = "<p>Hi,</p>\n"
        message += f"<p>You were previously invited to explore {submission.company.name}'s Capital Explorer Results. The owner has updated the link and/or the passcode, here's the updated information:</p>\n"
        message += f"<p>Link: {link}"

        if submission.passcode:
            message += f"<br>\nPasscode: {submission.passcode}"

        message += "</p>\n"
        message += "<p>You can now use this link"

        if submission.passcode:
            message += " and passcode "

        message += "to view the Capital Explorer Results. If you encounter any issues or have questions, please feel free to reach out to us.</p>\n"
        message += "<p>Best regards,<br><i>The Abaca Team</i></p>"

        email_data = {
            'subject': subject,
            'message': message,
        }

        for user_profile in users:
            sendEmailWithoutTemplate(user_profile.user.email, email_data)

    def _reset_link(self, submission):
        # Generate a new UID
        submission.uid = random_uid()

        # Remove guests (but preserve invited users, as they'll receive an
        # email with the new link, and can be individually removed if needed)
        submission.invited_guests.clear()
        submission.save()

    def _reset_passcode(self, submission):
        submission.passcode = random_uid()
        submission.save()

    def put(self, request, *args, **kwargs):
        return Response(status=HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        submission = self.get_object()

        if reset_link := request.query_params.get('reset') == 'link':
            self._reset_link(submission)
        if reset_passcode := request.query_params.get('reset') == 'passcode':
            self._reset_passcode(submission)

        response = self.partial_update(request, *args, **kwargs)

        if reset_link or reset_passcode:
            self._send_updated_invitation_emails(submission)

        return response
