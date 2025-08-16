from django import forms
from .models import NotificationEmail

class NotificationEmailForm(forms.ModelForm):
    class Meta:
        model = NotificationEmail
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border rounded',
                'placeholder': 'name@example.com'
            })
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if NotificationEmail.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in the list.")
        return email