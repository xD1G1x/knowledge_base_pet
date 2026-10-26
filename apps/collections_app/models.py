from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Collection(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_collection_name_per_owner",
            ),
        ]
    def __str__(self) -> str:
        return self.name
