from uuid import uuid4
from django.db import models
from shared.models.timestamped_model import TimestampedModel

class Process(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    company = models.ForeignKey('viral.Company', on_delete=models.CASCADE)
    company_lists = models.ManyToManyField('CompanyList', through='ProcessStep')    

    def __str__(self):
        return f'{self.title} ({self.company.name})'

    class Meta:
        verbose_name_plural = 'processes'