from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, OriginalAudioFile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, required=True, label="User Role")

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'user_type']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        if commit:
            user.save()
        return user

class AudioUploadForm(forms.Form):
    # Use a regular FileField without the multiple attribute
    # The multiple file handling will be done in the view
    audio_files = forms.FileField(
        widget=forms.FileInput(attrs={'accept': '.wav'}),
        required=False,
        label="Select Audio Files",
        help_text="Select audio files to upload (.wav format only)"
    )
    folder_upload = forms.BooleanField(
        required=False,
        label="Upload Folder",
        help_text="Check this to upload an entire folder of audio files"
    )
    animal_type = forms.ChoiceField(
        choices=OriginalAudioFile.ANIMAL_CHOICES,
        required=True,
        label="Animal Type"
    )
    zoo = forms.ModelChoiceField(
        queryset=OriginalAudioFile._meta.get_field('zoo').remote_field.model.objects.all(),
        required=False,
        label="Zoo",
        empty_label="Select Zoo (Optional)"
    )