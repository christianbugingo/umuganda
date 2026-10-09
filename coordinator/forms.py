from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Community, UserProfile, Volunteer, UmugandaProject

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            Volunteer.objects.create(
                user=user,
                phone=self.cleaned_data['phone']
            )
            UserProfile.objects.create(
                user=user,
                role='volunteer',
                phone=self.cleaned_data['phone'],
            )
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))


class LeaderRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    community = forms.ModelChoiceField(
        queryset=Community.objects.none(),
        empty_label="Select your community",
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'community', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['community'].queryset = Community.objects.filter(
            leader__isnull=True
        ).order_by('province', 'district', 'sector', 'cell', 'village')
        self.fields['community'].label_from_instance = lambda community: community.full_address()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            community = self.cleaned_data['community']
            community.leader = user
            community.leader_phone = self.cleaned_data['phone']
            community.save(update_fields=['leader', 'leader_phone'])
            UserProfile.objects.create(
                user=user,
                role='leader',
                phone=self.cleaned_data['phone'],
            )
        return user


class ProjectForm(forms.ModelForm):
    class Meta:
        model = UmugandaProject
        fields = [
            'title', 'description', 'location', 'date', 'start_time',
            'end_time', 'community', 'needed_volunteers',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        communities = kwargs.pop('communities')
        super().__init__(*args, **kwargs)
        self.fields['community'].queryset = communities
        self.fields['community'].label_from_instance = lambda community: community.full_address()


class ProfileEditForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, required=False)
    photo = forms.ImageField(required=False)

    def __init__(self, *args, user, profile, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.profile = profile
        if not self.is_bound:
            self.initial.update({
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': profile.phone,
            })

    def save(self):
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        self.user.save(update_fields=['first_name', 'last_name', 'email'])

        self.profile.phone = self.cleaned_data['phone']
        if self.cleaned_data.get('photo'):
            self.profile.photo = self.cleaned_data['photo']
        self.profile.save()
        Volunteer.objects.filter(user=self.user).update(phone=self.profile.phone)
        Community.objects.filter(leader=self.user).update(leader_phone=self.profile.phone)
        return self.profile