from django.db import models

from shared.models import TimestampedModel
from allauth.utils import get_user_model


class UserVendor(TimestampedModel):
    """
    Model to store vendor user data.
    """

    user_id = models.CharField(max_length=200, blank=True)
    user_vendor = models.ForeignKey('Vendor',
                                    on_delete=models.DO_NOTHING,
                                    blank=True,
                                    null=True)
    user_profile = models.ForeignKey(
        "UserProfile", on_delete=models.CASCADE)

    def __str__(self):
        return "(%s) %s" % (self.user_profile.user.email, self.user_vendor.name)

    class Meta:
        # Make possible to only have one type of vendor for each user
        unique_together = ("user_vendor", "user_profile")
