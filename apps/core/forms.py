from django import forms


class MagicLinkForm(forms.Form):
    email = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))
