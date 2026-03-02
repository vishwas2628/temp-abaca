from uuid import uuid4
from django.db import models
from company_lists.models import CompanyList
from shared.models.timestamped_model import TimestampedModel


class ProcessStep(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    process = models.ForeignKey('Process', related_name='steps', on_delete=models.CASCADE)
    title = models.CharField(max_length=25)
    description = models.TextField(blank=True)
    company_list = models.ForeignKey('CompanyList', on_delete=models.CASCADE, blank=True, help_text="Leave this field empty to automatically create a new list")
    order = models.PositiveIntegerField(default=0, db_index=True)

    def save(self, *args, **kwargs):
        # If no company list is provided, create a new one
        if not self.company_list_id:
            self.company_list = CompanyList.objects.create(
                owner=self.process.company.company_profile, title=f'{self.process.title} > {self.title}', description=self.description
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['process', 'company_list'], name='unique_process_step')
        ]