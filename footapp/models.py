from typing import Any
from django.db import models


class Database(models.Model):
    STATUS = [("N", "Normal"), ("H", "High"), ("F", "Flat"), ("U", "Unlabel")]

    SIDE = [("L", "Left"), ("R", "Right")]

    # LEVEL = [1,2,3]

    # hn = models.CharField(max_length=16)
    name = models.CharField(max_length=32, unique=True, null=True)
    link = models.CharField(max_length=256, unique=True, null=True)
    stat = models.CharField(max_length=1, choices=STATUS, default="U")
    side = models.CharField(max_length=1, choices=SIDE, null=True)
    owner = models.CharField(max_length=32)
    file_type = models.CharField(max_length=32)
    # level = models.IntegerField(choices=LEVEL)
    """For frontend checking"""
    deleted = models.BooleanField(default=False)

    remark = models.CharField(max_length=256, default="")

    created_date = models.DateTimeField(auto_now_add=True)
    modify_date = models.DateTimeField(auto_now_add=True)  # update when mod and del
    deleted_date = models.DateTimeField(
        null=True, default=None, blank=True
    )  # update when del

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.name:
            self.name = str(self.pk).zfill(3)
            super().save(update_fields=["name"])
