from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.timezone import now


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('1', 'Admin'),
        ('2', 'Staff'),
    )
    user_type = models.CharField(max_length=1, choices=USER_TYPE_CHOICES, default='2')
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, default="User")

    def __str__(self):
        return self.email

# Admin Profile Model
class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

# Staff Profile Model
class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    department = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    

class AudioFile(models.Model):
    ANIMAL_CHOICES = [
        ('amur_leopard', 'Amur Leopard'),
        ('amur_tiger', 'Amur Tiger'),
    ]

    file = models.FileField(upload_to='audio_files/')
    animal_type = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    upload_date = models.DateTimeField(default=now)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.animal_type} - {self.file.name}"

class ZooTable(models.Model): 
    zoo_id = models.IntegerField(auto_created=True)
    zoo_name = models.CharField(max_length=20)
    location = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.CharField(max_length=20)

    def _str_(self): 
        return self.zoo_name

class AnimalTable(models.Model):
    animal_id = models.IntegerField(auto_created=True)
    species_name = models.CharField(max_length=20)
    zoo_id = models.IntegerField(auto_created=True)

    def _str_(self):
        return self.species_name

class OriginalAudioFile(models.Model):
    ANIMAL_CHOICES = [
        ('amur_leopard', 'Amur Leopard'),
        ('amur_tiger', 'Amur Tiger'),
    ]

    file_id = models.IntegerField(auto_created=True)
    audio_file_name = models.CharField(max_length=20)
    recording_date = models.DateTimeField()
    animal_type = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    animal = models.IntegerField(auto_created=True)
    zoo = models.IntegerField(auto_created=True)
    file_size_mb = models.FloatField(auto_created=True)
    upload_date = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.animal_type} - {self.audio_file_name}"

class ReducedAudioFile(models.Model):
    ANIMAL_CHOICES = [
        ('amur_leopard', 'Amur Leopard'),
        ('amur_tiger', 'Amur Tiger'),
    ]

    file_id = models.IntegerField(auto_created=True)
    audio_file_name = models.CharField(max_length=20)
    recording_date = models.DateTimeField()
    animal_type = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    animal = models.IntegerField(auto_created=True)
    zoo = models.IntegerField(auto_created=True)
    file_size_mb = models.FloatField(auto_created=True)
    upload_date = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.animal_type} - {self.audio_file_name}"

class DetectedNoiseAudioFile(models.Model):
    detected_noise_file_id = models.IntegerField(auto_created=True)
    original_file_id = models.IntegerField(OriginalAudioFile.file_id)
    detected_noise_file_path = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    saw_count = models.IntegerField(blank=False)
    saw_call_count = models.IntegerField(blank=False)
    noise_verfied = models.BooleanField(saw_count > 0 or saw_call_count > 0)
    file_size_mb = models.FloatField(auto_created=True)
    upload_date = models.DateTimeField(default=now)

    def _str_(self):
        return self.detected_noise_file_path



# class is table
# each row under class is a column in the table 
    # ex: user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    #     full_name = models.CharField(max_length=100)
    #     department = models.CharField(max_length=100, null=True, blank=True)
    #     created_at = models.DateTimeField(auto_now_add=True)

    