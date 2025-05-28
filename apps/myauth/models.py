from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.Model):
    id_role = models.AutoField(primary_key=True)
    nama_role = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nama_role

class CustomUser(AbstractUser):
    id_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.username

