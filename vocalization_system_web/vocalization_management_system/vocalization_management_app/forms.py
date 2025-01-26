from django import forms
from .models import BigCat, Vocalization

class BigCatForm(forms.ModelForm):
    class Meta:
        model = BigCat
        fields = ['name', 'species', 'age', 'description']

class VocalizationForm(forms.ModelForm):
    class Meta:
        model = Vocalization
        fields = ['big_cat', 'sound_file', 'description', 'recorded_at']