from django.db import models
import django.utils.timezone as timezone


class TimestampedModel(models.Model):
    # A timestamp representing when this object was created.
    created_at = models.DateTimeField(auto_now_add=True)

    # A timestamp representing when this object was last updated.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

        # By default, any model that inherits from `TimestampedModel` should
        # be ordered in reverse-chronological order. We can override this on a
        # per-model basis as needed, but reverse-chronological is a good
        # default ordering for most models.
        ordering = ['-created_at', '-updated_at']

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        # If this is a new object, set created_at
        if not self.created_at or self.created_at == "null":
            self.created_at = timezone.now()
        super().save(*args, **kwargs)
