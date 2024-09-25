from django import forms
from .models import ShippingLocation

class ShippingForm(forms.Form):
    name = forms.CharField(max_length=100)
    location = forms.ModelChoiceField(
        queryset=ShippingLocation.objects.all(),
        empty_label="Select a shipping location",
        required=False
    )
    custom_address = forms.BooleanField(required=False, initial=False,
                                        widget=forms.CheckboxInput(attrs={'class': 'custom-address-checkbox'}))
    address = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get("location")
        custom_address = cleaned_data.get("custom_address")
        address = cleaned_data.get("address")

        if not location and not custom_address:
            raise forms.ValidationError("Please select a shipping location or provide a custom address.")
        
        if custom_address and not address:
            raise forms.ValidationError("Please provide a custom address.")

        return cleaned_data
    
    location = forms.ModelChoiceField(
        queryset=ShippingLocation.objects.all(),
        empty_label="Select a shipping location",
        required=False,
        widget=forms.Select(attrs={'class': 'shipping-location-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].widget.choices = [
            (location.id, f"{location.name} (Ksh. {location.shipping_cost})")
            for location in ShippingLocation.objects.all()
        ]
        for location in ShippingLocation.objects.all():
            self.fields['location'].widget.attrs[f'data-shipping-cost-{location.id}'] = location.shipping_cost