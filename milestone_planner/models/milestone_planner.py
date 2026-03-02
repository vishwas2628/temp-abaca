from django.db import models
from shared.models import TimestampedModel, UniqueUID


class MilestonePlanner(TimestampedModel, UniqueUID):
    """
    Entity responsible for managing external access to a company's milestones.

    NOTE:
    For the time being, each company can only have a single milestone planner which
    doesn't justify for now the effort of tracking all milestones on a m2m relation
    therefore we'll be accessing all milestones through the company foreign key.
    """
    company = models.ForeignKey('viral.Company', related_name="milestone_planners", on_delete=models.CASCADE)
    # Consider uncommenting this when a company might have multiple milestone planners with different milestones:
    # milestones = models.ManyToManyField('Milestone', blank=True)

    invited_users = models.ManyToManyField('viral.UserProfile', blank=True, through='UserInvitation')
    invited_guests = models.ManyToManyField('viral.UserGuest', blank=True)

    passcode = models.CharField(max_length=20, null=True, blank=True)
    # Helps us track passcode changes
    previous_passcode = models.CharField(max_length=20, null=True, blank=True)
    __original_passcode = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_passcode = self.passcode

    def __str__(self):
        return f"Milestone Planner > {self.company.name}"

    def save(self, *args, **kwargs):
        # Automatically update previous passcode:
        if self.passcode != self.__original_passcode:
            self.previous_passcode = self.__original_passcode

        super().save(*args, **kwargs)
        self.__original_passcode = self.passcode
