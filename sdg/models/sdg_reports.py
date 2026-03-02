from django.db import models
from shared.models.timestamped_model import TimestampedModel


class SdgReport(TimestampedModel):
    company = models.ForeignKey(
        'viral.Company',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=False,
    )
    affiliate = models.ForeignKey(
        'viral.Affiliate',
        related_name="+",
        on_delete=models.DO_NOTHING,
        null=False,
        blank=False,
    )
    job_id = models.CharField(max_length=255)
    job_status = models.CharField(max_length=255)

    report_pdf_url = models.URLField(max_length=2048, null=True, blank=True)
    report_xlsx_url = models.URLField(max_length=2048, null=True, blank=True)
    report_date = models.DateField()
    report_type = models.CharField(max_length=255)
