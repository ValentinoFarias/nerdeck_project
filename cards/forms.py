from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    validate_password,
    password_validators_help_text_html,
)
from django.core.exceptions import ValidationError
from .models import Card


class EmailSignupForm(forms.ModelForm):
    """Signup form that uses email instead of username and enforces strong passwords."""

    # Two explicit password fields so we can confirm they match.
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )

    class Meta:
        # Backed by Django's built‑in User model, but we only expose the email field.
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        """Attach Django's password help text so users see strength guidelines."""
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = password_validators_help_text_html()

    def clean_email(self):
        """Normalize email and ensure we don't already have an account for it."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            return email

        # Since we use email as the username, ensure it is unique.
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Please log in instead."
            )

        return email

    def clean(self):
        """Validate matching passwords and run Django's password validators."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            # Check that both password entries are identical.
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn’t match.")

            # Run Django's configured password validators (length, common passwords, numeric-only, etc.).
            try:
                # We don't have the user instance yet, but validators can run with user=None.
                validate_password(password1)
            except ValidationError as exc:
                # Attach all validation error messages to the first password field.
                self.add_error("password1", exc)

        return cleaned_data

    def save(self, commit=True):
        """Create the user using email as username and set the hashed password."""
        user = super().save(commit=False)
        # Use normalized email as the username internally so we never ask for a separate username.
        email = self.cleaned_data["email"].strip().lower()
        user.username = email
        user.email = email
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class CardForm(forms.ModelForm):
    """Simple form for creating or editing a flashcard."""

    class Meta:
        model = Card
        fields = ["front_text", "back_text"]
