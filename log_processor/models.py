from django.db import models

# Create your models here.
from django.db import models

class DataTransfer(models.Model):
    vendorId = models.CharField(max_length=100)
    messageId = models.CharField(max_length=100)
    data = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendorId} - {self.messageId}"