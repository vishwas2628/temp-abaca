from django.db import models
from shared.models import TimestampedModel
from matching.models import Answer


class Question(TimestampedModel):
    entrepreneur_question = models.CharField(max_length=255)
    resource_question = models.CharField(max_length=255)
    ttl = models.DurationField()
    short_name = models.CharField(null=True, max_length=100)
    slug = models.SlugField(max_length=80, null=True, unique=True)
    instructions = models.TextField(null=True, blank=True)
    is_common = models.BooleanField(default=False, help_text='Set question as most common for additional criteria')
    is_team_member_question = models.BooleanField(default=False, help_text='Set question as targeted for Team Members')

    question_type = models.ForeignKey(
        'QuestionType',
        on_delete=models.CASCADE
    )
    question_category = models.ForeignKey(
        'QuestionCategory',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    profile_field = models.ForeignKey(
        'profiles.ProfileIDField', null=True, blank=True,
        help_text='Optionally target a profile field where the response to a question will override that field\'s value',
        on_delete=models.SET_NULL,)

    def __str__(self):
        return self.entrepreneur_question

    def get_answers(self):
        """
        Get list of answers associated with this question.
        """
        return Answer.objects.filter(question=self)
    
    def save(self, *args, **kwargs):
        super(Question, self).save(*args, **kwargs)
        # Make sure team member questions don't appear on regular question bundle
        question_bundles = self.questionbundle_set.all()
        for question_bundle in question_bundles:
            if question_bundle.has_team_member_questions and not self.is_team_member_question:
                question_bundle.questions.remove(self)
            elif not question_bundle.has_team_member_questions and self.is_team_member_question:
                question_bundle.questions.remove(self)


