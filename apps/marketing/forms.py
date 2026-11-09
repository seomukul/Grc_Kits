from django import forms


class SubscribeForm(forms.Form):
    email = forms.EmailField()
    source = forms.CharField(max_length=50, required=False)
    # Honeypot: bots fill it, humans don't see it.
    website = forms.CharField(required=False)
