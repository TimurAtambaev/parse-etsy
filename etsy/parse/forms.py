from django import forms

from .models import Parse


class LinkTokenForm(forms.ModelForm):
    class Meta:
        model = Parse
        fields = ['link']
