from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.db.models import Q
from coordinator.forms import RegisterForm, LoginForm 




from coordinator.models import Participation, UmugandaProject, Volunteer

def home(request):
    return render(request, 'coordinator/home.html')



def project_list(request):
    """Show all upcoming projects with search and filter functionality"""
    # Get search parameters
    search_query = request.GET.get('search', '')
    province_filter = request.GET.get('province', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Base queryset
    projects = UmugandaProject.objects.filter(status='planned').order_by('date')

    # Apply search filter
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(community__village__icontains=search_query) |
            Q(community__cell__icontains=search_query) |
            Q(community__sector__icontains=search_query) |
            Q(community__district__icontains=search_query)
        )

    # Apply province filter
    if province_filter:
        projects = projects.filter(community__province=province_filter)

    # Apply date filters
    if date_from:
        projects = projects.filter(date__gte=date_from)
    if date_to:
        projects = projects.filter(date__lte=date_to)

    # Group by province for better organization
    projects_by_province = {}
    for project in projects:
        province = project.community.get_province_display()
        if province not in projects_by_province:
            projects_by_province[province] = []
        projects_by_province[province].append(project)

    # Get all available provinces for filter dropdown
    from coordinator.models import Community
    available_provinces = Community.PROVINCE_CHOICES

    context = {
        'projects_by_province': projects_by_province,
        'total_projects': projects.count(),
        'search_query': search_query,
        'province_filter': province_filter,
        'date_from': date_from,
        'date_to': date_to,
        'available_provinces': available_provinces,
    }
    return render(request, 'coordinator/project_list.html', context)

def project_detail(request, project_id):
    """Show details of a specific project"""
    project = get_object_or_404(UmugandaProject, id=project_id)
    # Get participants for this project
    participants = Participation.objects.filter(project=project).select_related('volunteer__user')
    
    # Check if user is already signed up
    is_signed_up = False
    if request.user.is_authenticated:
        is_signed_up = Volunteer.objects.filter(
            user=request.user, 
            community=project.community
        ).exists()
    
    context = {
        'project': project,
        'is_signed_up': is_signed_up,
        'volunteers_needed': project.needed_volunteers,
        'current_participants': project.participant_count(),
        'participants': participants,
    }
    return render(request, 'coordinator/project_detail.html', context)

@login_required
def volunteer_signup(request, project_id):
    """Sign up a user as a volunteer for a project"""
    project = get_object_or_404(UmugandaProject, id=project_id)
    
    # Check if user is already a volunteer
    volunteer, created = Volunteer.objects.get_or_create(
        user=request.user,
        defaults={'phone': request.user.email}
    )
   #Check if already signed up
    if Participation.objects.filter(volunteer=volunteer, project=project).exists():
        messages.info(request, "You are already signed up for this project!")
    else:
        # Create participation record
        Participation.objects.create(volunteer=volunteer, project=project)
    
    # Update community if not set
    if not volunteer.community:
        volunteer.community = project.community
        volunteer.save()
    
    messages.success(request, f"You have successfully signed up for {project.title}!")
    return redirect('project_detail', project_id=project_id)
def register(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Auto-login after registration
            login(request, user)
            
            messages.success(request, f"Registration successful! Welcome to Umuganda Coordinator, {user.username}.")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'coordinator/register.html', {'form': form})

def user_login(request):
    """Custom login view (optional, uses Django's built-in for now)"""
    return render(request, 'coordinator/login.html')
@login_required
def dashboard(request):
    """User dashboard showing profile and project participation"""
    # Get or create volunteer profile
    volunteer, created = Volunteer.objects.get_or_create(
        user=request.user,
        defaults={'phone': ''}
    )
    
    # Get projects user has signed up for
    # We'll need to create a Participation model for this, but for now show all projects
    # Get projects user has signed up for through Participation
    participations = Participation.objects.filter(
        volunteer=volunteer
    ).select_related('project', 'project__community').order_by('-signed_up_at')
    
    context = {
        'volunteer': volunteer,
        'user': request.user,
        'participations': participations,
        'total_projects': participations.count(),
        'total_hours': sum(p.hours_contributed for p in participations),
        'projects_attended': participations.filter(attended=True).count(),
    }
    return render(request, 'coordinator/dashboard.html', context)
def user_login(request):
    """Handle user login"""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect based on user type
                if user.is_staff:
                    return redirect('admin:index')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    
    return render(request, 'coordinator/login.html', {'form': form})

def user_logout(request):
    """Handle user logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

def privacy_policy(request):
    """Display privacy policy page"""
    return render(request, 'coordinator/privacy_policy.html')

def terms_of_service(request):
    """Display terms of service page"""
    return render(request, 'coordinator/terms_of_service.html')

def faq(request):
    """Display frequently asked questions page"""
    return render(request, 'coordinator/faq.html')