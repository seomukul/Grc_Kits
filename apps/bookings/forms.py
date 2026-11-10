from django import forms

from apps.core.spam import SpamProtectedForm
from apps.services.models import Service

from .models import Booking


class BookingForm(SpamProtectedForm, forms.ModelForm):
    start = forms.DateTimeField(widget=forms.HiddenInput)
    tz = forms.CharField(widget=forms.HiddenInput, max_length=64)

    class Meta:
        model = Booking
        fields = ["name", "email", "company", "phone", "service", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"service": "Topic", "phone": "Phone / WhatsApp"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["service"].required = False
        self.fields["service"].empty_label = "General / not sure yet"
