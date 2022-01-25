from django import forms

from .models import Parse


class LinkForm(forms.ModelForm):
    class Meta:
        model = Parse
        fields = ['link']
