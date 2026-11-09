from django import forms


class CheckoutForm(forms.Form):
    email = forms.EmailField(help_text="We'll send your download links and receipt here.")
    name = forms.CharField(max_length=150, required=False, label="Full name")
    accept_license = forms.BooleanField(
        label="I agree to the License Terms and Refund Policy",
        error_messages={"required": "Please accept the License Terms to continue."},
    )
