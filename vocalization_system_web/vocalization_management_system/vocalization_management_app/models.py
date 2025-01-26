from django.db import models

# Create your models here.
from django.db import models

# Create your models here.

class BigCat(models.Model):
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    age = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return self.name

class Vocalization(models.Model):
    big_cat = models.ForeignKey(BigCat, on_delete=models.CASCADE)
    sound_file = models.FileField(upload_to='vocalizations/')
    description = models.TextField()
    recorded_at = models.DateTimeField()
    is_saw_call = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.big_cat.name} - {self.description}"