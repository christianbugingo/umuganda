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
                is_approved=True,
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
    leader_type = forms.ChoiceField(
        choices=UserProfile.LEADER_TYPE_CHOICES,
        label="Leader type",
    )
    province = forms.ChoiceField(
        choices=[("", "Select a province"), *Community.PROVINCE_CHOICES],
    )
    district = forms.CharField(max_length=100, required=False)
    sector = forms.CharField(max_length=100, required=False)
    cell = forms.CharField(max_length=100, required=False)
    village = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone',
            'leader_type', 'province', 'district', 'sector', 'cell',
            'village', 'password1', 'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_suggestions = {}
        for field_name in ('district', 'sector', 'cell', 'village'):
            self.fields[field_name].widget.attrs['list'] = (
                f'{field_name}-location-options'
            )
            self.location_suggestions[field_name] = (
                Community.objects.exclude(**{f'{field_name}': ''})
                .values_list(field_name, flat=True)
                .distinct()
                .order_by(field_name)
            )
        levels = {
            'province': 1,
            'district': 2,
            'sector': 3,
            'cell': 4,
            'village': 5,
        }
        leader_type = (
            self.data.get('leader_type')
            if self.is_bound
            else self.initial.get('leader_type')
        )
        required_through = {
            'province': 1,
            'district': 2,
            'sector': 3,
            'cell': 4,
            'village': 5,
        }.get(leader_type, 0)
        for field_name, level in levels.items():
            self.fields[field_name].required = level <= required_through
            self.fields[field_name].widget.attrs['data-area-level'] = str(level)

    def clean(self):
        cleaned_data = super().clean()
        location_fields = ('province', 'district', 'sector', 'cell', 'village')
        required_through = {
            'province': 1,
            'district': 2,
            'sector': 3,
            'cell': 4,
            'village': 5,
        }.get(cleaned_data.get('leader_type'), 0)
        prefix = []
        for level, field_name in enumerate(location_fields, start=1):
            if level > required_through:
                break
            value = cleaned_data.get(field_name)
            if not value:
                break
            if isinstance(value, str):
                value = value.strip()
                cleaned_data[field_name] = value
            prefix.append(value)
        for field_name in location_fields[len(prefix):]:
            cleaned_data[field_name] = ''
        if (
            cleaned_data.get('leader_type') == 'village'
            and len(prefix) == len(location_fields)
            and Community.objects.filter(
                province=cleaned_data['province'],
                district=cleaned_data['district'],
                sector=cleaned_data['sector'],
                cell=cleaned_data['cell'],
                village=cleaned_data['village'],
                leader__isnull=False,
            ).exists()
        ):
            self.add_error(
                'village',
                "This village already has a registered leader. Contact an administrator if you need help.",
            )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            leader_type = self.cleaned_data['leader_type']
            location = {
                field: self.cleaned_data[field]
                for field in ('province', 'district', 'sector', 'cell', 'village')
            }
            community, _ = Community.objects.get_or_create(**location)
            UserProfile.objects.create(
                user=user,
                role='leader',
                leader_type=leader_type,
                community=community,
                **location,
                phone=self.cleaned_data['phone'],
                is_approved=False,
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