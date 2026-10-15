from django import forms


class ContactMessageForm(forms.Form):
    CATEGORY_CHOICES = [
        ('question', 'General question'),
        ('support', 'Technical support'),
        ('volunteer', 'Volunteer registration'),
        ('project', 'Community project'),
        ('feedback', 'Feedback or idea'),
    ]

    name = forms.CharField(max_length=120)
    email = forms.EmailField(max_length=254)
    subject = forms.CharField(max_length=160)
    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    message = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={'rows': 5}))
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_subject(self):
        return self.cleaned_data['subject'].strip()

    def clean_message(self):
        return self.cleaned_data['message'].strip()

    def clean_website(self):
        value = self.cleaned_data.get('website', '')
        if value:
            raise forms.ValidationError('Unable to accept this submission.')
        return value
