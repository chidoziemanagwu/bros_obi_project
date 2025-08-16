# forms.py
from django import forms
from .models import Product
from django.contrib.auth.models import User

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'price', 'quantity', 'active']  # adjust to your model fields
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-2 border rounded'}),
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'sku': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'price': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'active': forms.CheckboxInput(attrs={'class': 'ml-2'}),
        }

class ManagerUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email is already in use.")
        return email


class StaffUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded'}), required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
        }



class SaleCreateForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded'})
    )