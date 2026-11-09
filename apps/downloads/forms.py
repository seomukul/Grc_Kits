from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import ProductFileVersion


class R2UploadWidget(forms.Widget):
    """File picker that uploads straight from the browser to R2 with a presigned PUT URL.

    Only the resulting object key is posted to Django, so 500 MB files never pass through the app server.
    """

    template_name = "downloads/widgets/r2_upload.html"


class ProductFileVersionForm(forms.ModelForm):
    uploaded_key = forms.CharField(required=False, widget=R2UploadWidget, label="File")

    class Meta:
        model = ProductFileVersion
        fields = ["version", "file", "changelog"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.USE_R2:
            if "file" in self.fields:
                del self.fields["file"]
        else:
            self.fields.pop("uploaded_key", None)

    def clean(self):
        cleaned = super().clean()
        if not settings.USE_R2:
            return cleaned
        key = cleaned.get("uploaded_key")
        if not key and not self.instance.file:
            if self.has_changed():
                raise ValidationError("Upload a file first.")
            return cleaned
        if key:
            if not key.startswith("uploads/"):
                raise ValidationError("Invalid upload key.")
            storage = self.instance._meta.get_field("file").storage
            if not storage.exists(key):
                raise ValidationError("The upload didn't finish. Please upload the file again.")
            self.instance.file.name = key
            self.instance.size = storage.size(key)
        return cleaned
