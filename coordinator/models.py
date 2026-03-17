from django.db import models
from django.contrib.auth.models import User

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
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    village = models.CharField(max_length=100, help_text="Umudugudu")
    
    # Community leader (optional)
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    leader_phone = models.CharField(max_length=15, blank=True)
    
    # Additional info
    population = models.IntegerField(default=0, blank=True, null=True)
    households = models.IntegerField(default=0, blank=True, null=True)
    
    def __str__(self):
        return f"{self.village} - {self.cell}, {self.sector}"
    
    def full_address(self):
        return f"{self.village}, {self.cell}, {self.sector}, {self.district}, {self.get_province_display()}"
    
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
                                  help_text="Select the village (Umudugudu) where this project will take place")
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


class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return self.user.username
    class Meta:
        verbose_name_plural = "Volunteers"
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