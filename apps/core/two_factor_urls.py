from django.urls import path

from . import two_factor

urlpatterns = [
    path("setup/", two_factor.setup, name="otp_setup"),
    path("verify/", two_factor.verify, name="otp_verify"),
    path("backup-codes/", two_factor.new_backup_codes, name="otp_backup_codes"),
]
