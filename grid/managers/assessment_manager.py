import bugsnag

from django.db import models
from django.apps import apps
from django.utils.functional import cached_property
from time import time

from grid.utils import calculate_viral_level, generate_hash


class AssessmentManager(models.Manager):

    @cached_property
    def viral_level_serializer(self):
        # To avoid circular dependency issue:
        from grid.serializers import ViralLevelSerializer
        return ViralLevelSerializer

    @property
    def milestone_model(self):
        return apps.get_model('milestone_planner.Milestone')

    def _create_assessment(self, latest_assessment, milestone, to_upgrade=True):
        # 1 - Generate new assessment data with milestone with new level:
        new_data = []
        for selection in latest_assessment.data:
            # For now, only single level upgrade/downgrade is being supported:
            milestone_level = milestone.category_level.level.value
            new_level = milestone_level if to_upgrade else milestone_level - 1 if milestone_level > 1 else None
            if selection.get('category') == milestone.category_level.category.pk:
                new_data.append({
                    **selection,
                    'level': new_level
                })
            else:
                new_data.append(selection)

        # 2 - Calculate new viral level from the new assessment data:
        new_data_serializer = self.viral_level_serializer(data=new_data, many=True)
        new_data_serializer.is_valid()
        final_level = calculate_viral_level(levels=new_data_serializer.validated_data)

        # 3 - Create new Assessment:
        self.create(
            level=final_level, data=new_data, user=latest_assessment.user, evaluated=latest_assessment.evaluated,
            hash_token=generate_hash(time()), state=self.model.FINISHED_STATE, from_milestone_planner=True)

    def sync_with_milestone(self, milestone, created=False):
        """
        Create new assessment if a milestone has been completed/uncompleted.
        """
        is_milestone_completed = milestone.state == self.milestone_model.COMPLETED_STATE
        has_milestone_been_deleted = created is False and self.milestone_model.objects.filter(
            pk=milestone.pk).count() == 0
        milestone_history = milestone.history.first() if not created else None
        milestone_previous_state = milestone_history.prev_record.state if bool(
            milestone_history) and bool(milestone_history.prev_record) else None
        latest_assessment = self.filter(user=milestone.user_profile.user.pk,
                                        evaluated=milestone.user_profile.company.pk).order_by('-created_at').first()

        if not latest_assessment:
            return bugsnag.notify(Exception("Cannot sync milestone with unexisting assessment."),
                                  meta_data={"context": {"milestone": milestone}})

        has_deleted_completed_milestone = has_milestone_been_deleted and is_milestone_completed
        has_created_completed_milestone = created and is_milestone_completed
        has_updated_existing_milestone = bool(milestone_previous_state) and milestone.state != milestone_previous_state
        has_completed_existing_milestone = has_updated_existing_milestone and \
            milestone.state == self.milestone_model.COMPLETED_STATE
        has_uncompleted_existing_milestone = has_updated_existing_milestone and \
            milestone.state != self.milestone_model.COMPLETED_STATE

        if has_created_completed_milestone or has_completed_existing_milestone:
            self._create_assessment(latest_assessment, milestone, to_upgrade=True)

        if has_deleted_completed_milestone or has_uncompleted_existing_milestone:
            self._create_assessment(latest_assessment, milestone, to_upgrade=False)
