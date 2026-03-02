from django.db import models

from shared.models import TimestampedModel
from allauth.utils import get_user_model


class UserMetadata(TimestampedModel):
    """
    Model to store metadata for the a user.
    """

    key = models.CharField(max_length=150)
    value = models.TextField()
    user_profile = models.ForeignKey(
        "UserProfile",
        on_delete=models.CASCADE,
        related_name="metadata",
        related_query_name="metadata",)

    def __str__(self):
        return "(%s) %s" % (self.user_profile.user.email, self.key)

    class Meta:
        # Make possible to only have one type of metadata
        # for each user.
        unique_together = ("key", "user_profile")
