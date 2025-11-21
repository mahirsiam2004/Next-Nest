# forms.py
from django import forms
from .models import HouseAd

class HouseAdForm(forms.ModelForm):
    class Meta:
        model = HouseAd
        fields = [
            'location', 'city', 'state', 'area', 'floors', 'cost',
            'hall', 'kitchen', 'balcony', 'bedrooms', 'ac', 'description', 'image'
        ]
