from django.db import models


# Create your models here.
class BaseModel(models.Model):
    """
    Base models to save the common properties such as:
        created_at, updated_at, updated_by, is_deleted, deleted_at.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    updated_by = models.IntegerField(blank=True, null=True, verbose_name='Updated by')
    is_deleted = models.BooleanField('Is Deleted', default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        verbose_name = 'BaseModel'
        verbose_name_plural = 'BaseModels'
        index_together = ["created_at", "updated_at"]


class ExpoPaymentUrl(BaseModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    full_url = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'Export Payment Url'
        verbose_name_plural = 'Export Payment Urls'

