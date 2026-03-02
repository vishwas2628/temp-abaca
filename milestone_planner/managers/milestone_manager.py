import bugsnag

from django.apps import apps
from django.db import models
from django.db.models import F
from simple_history.utils import bulk_create_with_history, bulk_update_with_history

from grid.models import CategoryLevel
from shared.models.unique_uid import random_uid
from viral.models.user_profile import UserProfile


class MilestoneManager(models.Manager):
    use_in_migrations = True

    @property
    def milestone_model(self):
        # Import model on demand to work with migrations:
        return apps.get_model('milestone_planner.Milestone')

    def _set_category_levels_for_milestones(self):
        # This is just to avoid making duplicated trips to the database.
        self.category_levels_for_milestones = CategoryLevel.objects.filter(
            category__group=2).annotate(
            category_pk=F('category__pk'),
            level_value=F('level__value')).order_by('level_value')

    def _get_self_assessed_milestones(self, selected_category_pk, selected_level_value, current_level_value=0):
        """
        Retrieve the self-assessed milestones for each category level.
        """
        category_levels_assessed = [
            category_level for category_level in self.category_levels_for_milestones
            if category_level.level_value > current_level_value and
            category_level.level_value <= selected_level_value and
            category_level.category_pk == selected_category_pk]

        return [{
                'uid': random_uid(),
                'category_level_id': category_level.pk,
                } for category_level in category_levels_assessed]

    def _get_upgraded_milestones_from_assessment(self, milestones_to_upgrade, selected_level_value, assessment):
        milestones_to_upgrade = list(filter(
            lambda milestone: milestone.category_level.level.value <= selected_level_value, milestones_to_upgrade))

        for milestone in [*milestones_to_upgrade]:
            # 1 - Convert milestones into complete validated:
            milestone.evidence_published = True
            milestone.date_of_completion = assessment.created_at
            milestone.state = milestone.current_state

        return milestones_to_upgrade

    def _get_downgraded_milestones_from_assessment(self, milestones_to_downgrade, selected_level_value):
        # 1 - Only downgrade milestones that were completed and have a higher value than the selected level:
        milestones_to_downgrade = list(filter(
            lambda milestone: milestone.category_level.level.value > selected_level_value, milestones_to_downgrade))

        for milestone in [*milestones_to_downgrade]:
            # 2 - Unpublish milestones:
            milestone.evidence_published = False
            if not milestone.evidence.exists() and not milestone.has_any_plan_field:
                # 3 - Or, move to deletion those without evidence and a plan:
                milestones_to_downgrade.remove(milestone)
                continue
            else:
                # 4 - Revert those without evidence to their previous state (to-be-planned/planned):
                milestone.date_of_completion = None
            milestone.state = milestone.current_state

        return milestones_to_downgrade

    def _get_milestones_from_assessment(self, assessment, existing_milestones=[]):
        """
        Retrieve milestones to reflect the latest assessment while
        considering, depending if they already exist, their current state.
        """
        # Retrieve milestones to create, and/or update, delete
        milestones_to_create, milestones_to_update, milestones_to_delete = [], [], []

        # For query optimization, ensure that all category levels
        # were set/queried before accessing this instance method:
        assert hasattr(self, 'category_levels_for_milestones')

        # Ensure that there's a user profile link for the milestones
        if not hasattr(assessment, 'user_profile_pk'):
            try:
                user_profile = UserProfile.objects.get(user=assessment.user, company=assessment.evaluated)
                setattr(assessment, 'user_profile_pk', user_profile.pk)
            except UserProfile.DoesNotExist as error:
                bugsnag.notify(Exception("Cannot generate milestones for unexisting user profile."),
                               meta_data={"context": {"error": error}})
                return milestones_to_create, milestones_to_update, milestones_to_delete

        # Go trough each assessed category level to reflect a corresponding milestone:
        for selection in assessment.data:
            selected_level_value = selection.get('level') or 0
            selected_category_pk = selection.get('category')

            if not len(existing_milestones):
                # If there aren't milestones, then only we need is self-assessed milestones:
                new_self_assessed_milestones = self._get_self_assessed_milestones(
                    selected_category_pk, selected_level_value)
                milestones_to_create.extend([self.model(**{
                    **new_milestone,
                    'state': self.milestone_model.COMPLETED_STATE,
                    'evidence_published': True,
                    'date_of_completion': assessment.created_at,
                    'user_profile_id': assessment.user_profile_pk
                }) for new_milestone in new_self_assessed_milestones])
            else:
                category_milestones = list(filter(
                    lambda milestone: milestone.category_level.category.pk == selected_category_pk,
                    existing_milestones))
                completed_milestones = list(filter(
                    lambda milestone: milestone.evidence_published, category_milestones))
                has_milestone_with_higher_selected_category_level = any(
                    selected_level_value < milestone.category_level.level.value for milestone in completed_milestones)
                has_only_milestones_with_lower_category_level = all(
                    selected_level_value > milestone.category_level.level.value for milestone in completed_milestones)

                # Check if there's already a milestone with a higher selected level & category:
                if has_milestone_with_higher_selected_category_level:
                    # If exists, means that this will be a downgrade of milestones:
                    # 1 - Downgrade existing milestones:
                    updated_milestones = self._get_downgraded_milestones_from_assessment(
                        category_milestones, selected_level_value)
                    milestones_to_update.extend(updated_milestones)
                    # 2 - Remove self-assessed milestones:
                    milestones_to_update_pks = [milestone.pk for milestone in milestones_to_update]
                    milestones_to_delete.extend(list(
                        filter(
                            lambda milestone: milestone.category_level.level.value >
                            selected_level_value and not milestone.evidence.exists() and
                            not milestone.has_any_plan_field and
                            milestone.pk not in milestones_to_update_pks, category_milestones)))
                elif has_only_milestones_with_lower_category_level:
                    # Otherwise, it's an upgrade of milestones:
                    sorted_by_level = sorted(
                        category_milestones,
                        key=lambda milestone: milestone.category_level.level.value)
                    sorted_completed = list(filter(lambda milestone: milestone.evidence_published, sorted_by_level))
                    highest_completed_milestone_value = sorted_completed[-1].category_level.level.value if len(
                        completed_milestones) else 0
                    # 1 - Add self-assessed milestones for creation:
                    self_assessed_milestones = self._get_self_assessed_milestones(
                        selected_category_pk, selected_level_value,
                        highest_completed_milestone_value)
                    existing_milestones_category_levels_pks = list(
                        map(lambda milestone: milestone.category_level.pk, category_milestones))
                    # Exclude existing milestones from creation:
                    new_milestones_to_create = list(
                        filter(
                            lambda milestone: milestone['category_level_id'] not in
                            existing_milestones_category_levels_pks, self_assessed_milestones))
                    milestones_to_create.extend([self.model(**{
                        **new_milestone,
                        'evidence_published': True,
                        'state': self.model.COMPLETED_STATE,
                        'date_of_completion': assessment.created_at,
                        'user_profile_id': assessment.user_profile_pk
                    }) for new_milestone in new_milestones_to_create])
                    # 2 - Upgrade existing milestones:
                    updated_milestones = self._get_upgraded_milestones_from_assessment(
                        sorted_by_level, selected_level_value, assessment)
                    milestones_to_update.extend(updated_milestones)

        return milestones_to_create, milestones_to_update, milestones_to_delete

    def generate_from_assessments(self, assessments):
        """
        Create the initial (self-assessed) milestones
        from the existing self-assessments of all entrepreneurs.
        """
        milestones_from_assessment = []

        # Ensure this method only gets used to populate from scratch:
        assert self.count() == 0, "This is only supposed to be generated on an empty table!"

        # For query optimization, ensure all assessment instances already include a user_profile_pk:
        assert all((hasattr(assessment, 'user_profile_pk') for assessment in assessments))

        # 1 - Grab all category levels needed to link with each milestone.
        self._set_category_levels_for_milestones()

        # 2 - Build all milestones (self-assessed) to be created.
        for assessment in assessments:
            milestones_to_create, *_ = self._get_milestones_from_assessment(assessment)
            milestones_from_assessment.extend(milestones_to_create)

        # 3 - Bulk create all milestones with a safe batch size to prevent bottlenecks:
        return bulk_create_with_history(milestones_from_assessment, self.milestone_model, batch_size=5000)

    def sync_from_assessment(self, assessment):
        """
        Create, update and/or delete milestones from a newly
        added self-assessment of an entrepreneur.
        """
        existing_milestones = self.filter(user_profile__company__pk=assessment.evaluated).order_by(
            'category_level__level__value')

        # 1 - Grab all category levels needed to link with each milestone.
        self._set_category_levels_for_milestones()

        # 2 - Build all milestones to be created/updated.
        milestones_to_create, milestones_to_update, milestones_to_delete = self._get_milestones_from_assessment(
            assessment, existing_milestones)

        # 3 - Bulk update milestones:
        bulk_update_with_history(
            milestones_to_update,
            self.model,
            ['critical', 'state', 'date_of_completion', 'target_date', 'plan_published', 'evidence_published'])

        # 4 - Bulk delete milestones:
        self.filter(pk__in=[milestone.pk for milestone in milestones_to_delete]).delete()

        # 5 - Bulk create new milestones:
        return bulk_create_with_history(milestones_to_create, self.model, batch_size=5000)
