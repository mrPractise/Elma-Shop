from django import forms

class ShippingForm(forms.Form):
    name = forms.CharField(max_length=100)
    address = forms.CharField(widget=forms.Textarea)