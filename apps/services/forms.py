from django import forms
from django.core.validators import FileExtensionValidator

from apps.core.spam import SpamProtectedForm

from .models import Service, ServiceInquiry

MAX_ATTACHMENT_MB = 10
ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "png", "jpg", "jpeg", "zip", "txt"]


class InquiryForm(SpamProtectedForm, forms.ModelForm):
    attachment = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(ALLOWED_EXTENSIONS)],
        help_text=f"Optional (RFP, scope, policy…). Max {MAX_ATTACHMENT_MB} MB.",
    )

    class Meta:
        model = ServiceInquiry
        fields = ["name", "email", "company", "service", "message", "attachment"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}
        labels = {"service": "Service you're interested in"}

    def __init__(self, *args, show_service=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["service"].required = False
        self.fields["service"].empty_label = "General question"
        if not show_service:
            del self.fields["service"]

    def clean_attachment(self):
        f = self.cleaned_data.get("attachment")
        if f and f.size > MAX_ATTACHMENT_MB * 1024 * 1024:
            raise forms.ValidationError(f"File is larger than {MAX_ATTACHMENT_MB} MB.")
        return f
