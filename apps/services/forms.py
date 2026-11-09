from django import forms

from .models import ServiceInquiry


class InquiryForm(forms.ModelForm):
    class Meta:
        model = ServiceInquiry
        fields = ["name", "email", "company", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}
