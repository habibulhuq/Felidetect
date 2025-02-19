from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator


# Custom User Model with Role-Based Access Control
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email


# Staff Profile Model
class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email


# Zoo Information Table
class Zoo(models.Model):
    zoo_id = models.AutoField(primary_key=True)
    zoo_name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(unique=True)

    def __str__(self):
        return self.zoo_name


# Animal Table
class AnimalTable(models.Model):
    animal_id = models.AutoField(primary_key=True)
    species_name = models.CharField(max_length=50, unique=True)
    zoo = models.ForeignKey(Zoo, on_delete=models.CASCADE, related_name="animals")

    def __str__(self):
        return self.species_name


class OriginalAudioFile(models.Model):
    ANIMAL_CHOICES = [
        ('amur_leopard', 'Amur Leopard'),
        ('amur_tiger', 'Amur Tiger'),
    ]

    file_id = models.AutoField(primary_key=True)  # Explicitly setting primary key
    audio_file = models.FileField(upload_to='audio_files/', validators=[FileExtensionValidator(allowed_extensions=['wav'])])
    audio_file_name = models.CharField(max_length=100)
    recording_date = models.DateTimeField(blank=True, null=True)
    animal_type = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    animal = models.ForeignKey(AnimalTable, on_delete=models.CASCADE, related_name="original_audio", blank= True, null=True)
    zoo = models.ForeignKey(Zoo, on_delete=models.CASCADE, related_name="original_audio", blank=True, null=True)
    file_size_mb = models.FloatField(blank=True, null=True)
    upload_date = models.DateTimeField(default=now)
    uploaded_by = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, related_name="uploaded_audio", blank=True, null=True)

    def __str__(self):
        return f"{self.animal_type} - {self.audio_file_name}"


# Processed & Reduced Audio File Table
class ProcessedAudioFile(models.Model):
    file_id = models.AutoField(primary_key=True)
    audio_file_name = models.CharField(max_length=100)
    recording_date = models.DateTimeField()
    original_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name="processed_audio")
    file_size_mb = models.FloatField()
    processed_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, null=True, blank=True)
    upload_date = models.DateTimeField(default=now)

    def __str__(self):
        return f"Processed: {self.audio_file_name}"


# Detected Noise in Audio Files
class DetectedNoiseAudioFile(models.Model):
    detected_noise_file_id = models.AutoField(primary_key=True)
    original_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name="detected_noises")
    detected_noise_file_path = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    saw_count = models.IntegerField()
    saw_call_count = models.IntegerField()
    file_size_mb = models.FloatField()
    upload_date = models.DateTimeField(default=now)

    # Automatically determine if the noise should be verified
    def save(self, *args, **kwargs):
        self.noise_verified = self.saw_count > 0 or self.saw_call_count > 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Detected Noise: {self.detected_noise_file_path}"


# Spectrogram Table
class Spectrogram(models.Model):
    audio_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name='spectrograms')
    image_path = models.ImageField(upload_to='spectrograms/')
    generated_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Spectrogram for {self.audio_file.audio_file_name}"


# Waveform Table
class Waveform(models.Model):
    audio_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name='waveforms')
    image_path = models.ImageField(upload_to='waveforms/')
    generated_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waveform for {self.audio_file.audio_file_name}"


# Audio Processing Table (Processes Audio Files)
class AudioProcessor(models.Model):
    audio_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name='processing_results')
    processed_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, null=True, blank=True)
    saw_count = models.IntegerField(default=0)
    saw_call_count = models.IntegerField(default=0)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Processed {self.audio_file.audio_file_name}"


# Database Model (Metadata & Processing Status)
class Database(models.Model):
    audio_file = models.ForeignKey(OriginalAudioFile, on_delete=models.CASCADE, related_name='database_entry')
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Processed', 'Processed')], default='Pending')
    processed_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Database entry for {self.audio_file.audio_file_name}"
