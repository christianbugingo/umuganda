from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Community(models.Model):
    # Rwandan Administrative Structure
    PROVINCE_CHOICES = [
        ('kigali', 'Kigali City'),
        ('south', 'Southern Province'),
        ('west', 'Western Province'),
        ('north', 'Northern Province'),
        ('east', 'Eastern Province'),
    ]
    
    province = models.CharField(max_length=50, choices=PROVINCE_CHOICES)
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True, help_text="Umudugudu")
    
    # Community leader (optional)
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    leader_phone = models.CharField(max_length=15, blank=True)
    
    # Additional info
    population = models.IntegerField(default=0, blank=True, null=True)
    households = models.IntegerField(default=0, blank=True, null=True)
    
    def __str__(self):
        return ", ".join(
            value for value in (
                self.village,
                self.cell,
                self.sector,
                self.district,
                self.get_province_display(),
            ) if value
        )
    
    def full_address(self):
        return str(self)
    
    class Meta:
        verbose_name_plural = "Communities"
        unique_together = ['province', 'district', 'sector', 'cell', 'village']


class UmugandaProject(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE, 
                                  help_text="Select a community or administrative area managed by the leader")
    needed_volunteers = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def participant_count(self):
        return self.participation_set.count()
    
    def is_user_signed_up(self, user):
        """Check if a user has signed up for this project"""
        if not user.is_authenticated:
            return False
        try:
            volunteer = Volunteer.objects.get(user=user)
            return Participation.objects.filter(
                volunteer=volunteer, 
                project=self
            ).exists()
        except Volunteer.DoesNotExist:
            return False


class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('community', 'Community update'),
        ('notice', 'Important notice'),
        ('opportunity', 'Volunteer opportunity'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=160)
    body = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='community',
    )
    area = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='community_announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(
        blank=True,
        null=True,
        help_text="Optional. The announcement stops appearing after this date.",
    )
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ('-created_at', '-id')
        indexes = [
            models.Index(fields=('is_published', '-created_at')),
            models.Index(fields=('expires_at',)),
        ]
        verbose_name = 'community announcement'
        verbose_name_plural = 'community announcements'

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    quote = models.TextField()
    attribution = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    consent_confirmed = models.BooleanField(
        default=False,
        help_text="Confirm the person agreed to have this testimonial published.",
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return self.attribution


class UmugandaJournal(models.Model):
    HOMEPAGE_PHOTO_CHOICES = [
        ('pathway', 'Pathway improvements'),
        ('building', 'Building together'),
        ('greening', 'Greener communities'),
        ('tree_planting', 'Tree planting'),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    activity_date = models.DateField()
    location = models.CharField(max_length=200)
    organizer = models.CharField(max_length=160, blank=True)
    summary = models.CharField(max_length=300)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='journals/covers/')
    homepage_photo = models.CharField(
        max_length=20,
        choices=HOMEPAGE_PHOTO_CHOICES,
        unique=True,
        null=True,
        blank=True,
        help_text='Optional. Connect this story to one of the four homepage activity photos.',
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-activity_date', '-id')
        indexes = [models.Index(fields=('is_published', '-activity_date'))]
        verbose_name = 'Umuganda journal'
        verbose_name_plural = 'Umuganda journals'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'umuganda-journal'
            candidate = base_slug
            suffix = 2
            while type(self).objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class JournalPhoto(models.Model):
    journal = models.ForeignKey(
        UmugandaJournal,
        on_delete=models.CASCADE,
        related_name='photos',
    )
    image = models.ImageField(upload_to='journals/photos/')
    caption = models.CharField(max_length=180, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('position', 'id')

    def __str__(self):
        return self.caption or f'Photo for {self.journal.title}'


class JournalComment(models.Model):
    journal = models.ForeignKey(
        UmugandaJournal,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    name = models.CharField(max_length=80)
    body = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at', 'id')
        verbose_name = 'journal comment'
        verbose_name_plural = 'journal comments'

    def __str__(self):
        return f'Comment by {self.name} on {self.journal.title}'


class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return self.user.username
    class Meta:
        verbose_name_plural = "Volunteers"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('volunteer', 'Volunteer'),
        ('leader', 'Community leader'),
    ]
    LEADER_TYPE_CHOICES = [
        ('village', 'Village leader'),
        ('cell', 'Cell leader'),
        ('sector', 'Sector leader'),
        ('district', 'District leader'),
        ('province', 'Province leader'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='volunteer')
    leader_type = models.CharField(
        max_length=20,
        choices=LEADER_TYPE_CHOICES,
        blank=True,
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leaders',
    )
    province = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(
        default=False,
        help_text="Enable leader access only after independently verifying this person's role.",
    )
    phone = models.CharField(max_length=15, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', blank=True)

    def managed_communities(self):
        if self.role != 'leader':
            return Community.objects.none()

        scope_fields = {
            'village': ('province', 'district', 'sector', 'cell', 'village'),
            'cell': ('province', 'district', 'sector', 'cell'),
            'sector': ('province', 'district', 'sector'),
            'district': ('province', 'district'),
            'province': ('province',),
        }.get(self.leader_type)
        if not scope_fields:
            return Community.objects.none()

        area = {
            'province': self.province,
            'district': self.district,
            'sector': self.sector,
            'cell': self.cell,
            'village': self.village,
        }
        if not area['province'] and self.community_id:
            area = {
                field: getattr(self.community, field)
                for field in ('province', 'district', 'sector', 'cell', 'village')
            }
        if any(not area[field] for field in scope_fields):
            return Community.objects.none()

        scope = {field: area[field] for field in scope_fields}
        return Community.objects.filter(**scope)

    def managed_area_label(self):
        area = {
            'province': self.province,
            'district': self.district,
            'sector': self.sector,
            'cell': self.cell,
            'village': self.village,
        }
        if not area['province'] and self.community_id:
            area = {
                field: getattr(self.community, field)
                for field in ('province', 'district', 'sector', 'cell', 'village')
            }
        province_names = dict(Community.PROVINCE_CHOICES)
        parts = [
            area['village'],
            area['cell'],
            area['sector'],
            area['district'],
            province_names.get(area['province'], area['province']),
        ]
        return ", ".join(value for value in parts if value)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Participation(models.Model):
    """Tracks which volunteers are participating in which projects"""
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)
    project = models.ForeignKey(UmugandaProject, on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    hours_contributed = models.IntegerField(default=0)
    signed_up_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['volunteer', 'project']  # Prevent duplicate signups
    
    def __str__(self):
        return f"{self.volunteer.user.username} - {self.project.title}"