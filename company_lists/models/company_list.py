from django.db import models
from shared.models import TimestampedModel, UniqueUID


class CompanyList(TimestampedModel, UniqueUID):
    COMPANY_LIST_TYPE_STATIC = 0
    COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS = 1
    COMPANY_LIST_TYPE_CHOICES = (
        (COMPANY_LIST_TYPE_STATIC, 'Static'),
        (COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS, 'Affiliate Submissions'),
    )

    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    owner = models.ForeignKey('viral.UserProfile', related_name="my_company_list", null=True, on_delete=models.CASCADE)
    passcode = models.CharField(max_length=20, null=True, blank=True)
    # Helps us track passcode changes
    previous_passcode = models.CharField(max_length=20, null=True, blank=True)
    __original_passcode = None

    invited_users = models.ManyToManyField('viral.UserProfile', blank=True)
    invited_guests = models.ManyToManyField('viral.UserGuest', blank=True)

    companies = models.ManyToManyField('viral.Company', blank=True)

    pinned = models.BooleanField(default=False)

    company_list_type = models.SmallIntegerField(choices=COMPANY_LIST_TYPE_CHOICES, default=COMPANY_LIST_TYPE_STATIC)
    affiliate = models.ForeignKey('viral.Affiliate', blank=True, null=True, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_passcode = self.passcode

    def save(self, *args, **kwargs):
        # Automatically update previous passcode:
        if self.passcode != self.__original_passcode:
            self.previous_passcode = self.__original_passcode

        if self.affiliate and self.company_list_type == self.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS:
            self.title = self.affiliate.name
            self.description = f'Companies appear in this list if they submitted {self.affiliate.name}.'

        super().save(*args, **kwargs)
        self.__original_passcode = self.passcode

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='enforce_owner_or_affiliate',
                check=(
                    models.Q(company_list_type=0, owner__isnull=False) |
                    models.Q(company_list_type=1, affiliate__isnull=False)
                )
            )
        ]
