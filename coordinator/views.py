from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.db.models import Q
from functools import wraps
from coordinator.forms import (
    LeaderRegisterForm,
    LoginForm,
    ProfileEditForm,
    ProjectForm,
    RegisterForm,
)




from coordinator.models import (
    Community,
    Participation,
    UmugandaProject,
    UserProfile,
    Volunteer,
)

def home(request):
    return render(request, 'coordinator/home.html')



def project_list(request):
    """Show all upcoming projects with search and filter functionality"""
    # Get search parameters
    search_query = request.GET.get('search', '')
    province_filter = request.GET.get('province', '')
    district_filter = request.GET.get('district', '')
    sector_filter = request.GET.get('sector', '')
    cell_filter = request.GET.get('cell', '')
    village_filter = request.GET.get('village', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Base queryset
    projects = UmugandaProject.objects.filter(status='planned').select_related(
        'community'
    ).order_by('date')

    # Apply search filter
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(community__village__icontains=search_query) |
            Q(community__cell__icontains=search_query) |
            Q(community__sector__icontains=search_query) |
            Q(community__district__icontains=search_query)
        )

    # Apply province filter
    if province_filter:
        projects = projects.filter(community__province=province_filter)
    if district_filter:
        projects = projects.filter(community__district=district_filter)
    if sector_filter:
        projects = projects.filter(community__sector=sector_filter)
    if cell_filter:
        projects = projects.filter(community__cell=cell_filter)
    if village_filter:
        projects = projects.filter(community__village=village_filter)

    # Apply date filters
    if date_from:
        projects = projects.filter(date__gte=date_from)
    if date_to:
        projects = projects.filter(date__lte=date_to)

    # Build each location dropdown from communities matching the selections above it.
    communities = Community.objects.all()
    districts = communities
    if province_filter:
        districts = districts.filter(province=province_filter)

    sectors = districts
    if district_filter:
        sectors = sectors.filter(district=district_filter)

    cells = sectors
    if sector_filter:
        cells = cells.filter(sector=sector_filter)

    villages = cells
    if cell_filter:
        villages = villages.filter(cell=cell_filter)

    # Group by province for better organization
    projects_by_province = {}
    for project in projects:
        province = project.community.get_province_display()
        if province not in projects_by_province:
            projects_by_province[province] = []
        projects_by_province[province].append(project)

    context = {
        'projects_by_province': projects_by_province,
        'total_projects': projects.count(),
        'search_query': search_query,
        'province_filter': province_filter,
        'district_filter': district_filter,
        'sector_filter': sector_filter,
        'cell_filter': cell_filter,
        'village_filter': village_filter,
        'date_from': date_from,
        'date_to': date_to,
        'available_provinces': Community.PROVINCE_CHOICES,
        'available_districts': districts.values_list('district', flat=True).distinct().order_by('district'),
        'available_sectors': sectors.values_list('sector', flat=True).distinct().order_by('sector'),
        'available_cells': cells.values_list('cell', flat=True).distinct().order_by('cell'),
        'available_villages': villages.values_list('village', flat=True).distinct().order_by('village'),
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
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'volunteer'},
    )
    if profile.role != 'volunteer':
        messages.error(request, "Community leaders cannot sign up as volunteers.")
        return redirect('leader_dashboard')
    
    # Check if user is already a volunteer
    volunteer, created = Volunteer.objects.get_or_create(
        user=request.user,
        defaults={'phone': profile.phone}
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


def _profile_for(user):
    volunteer_phone = Volunteer.objects.filter(user=user).values_list(
        'phone', flat=True
    ).first()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': 'leader' if Community.objects.filter(leader=user).exists() else 'volunteer',
            'phone': volunteer_phone or '',
        },
    )
    return profile


def role_required(role):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if _profile_for(request.user).role != role:
                messages.error(request, "You don't have access to that dashboard.")
                return redirect('dashboard')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def leader_register(request):
    if request.method == 'POST':
        form = LeaderRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your leader account is ready. Post a project announcement from your dashboard.")
            return redirect('leader_dashboard')
    else:
        form = LeaderRegisterForm()
    return render(request, 'coordinator/leader_register.html', {'form': form})


def _handle_login(request, *, leader):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            is_leader = _profile_for(user).role == 'leader'
            if is_leader != leader:
                form.add_error(None, "Please use the sign-in page for your account type.")
            else:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('leader_dashboard' if leader else 'dashboard')
    else:
        form = LoginForm(request)
    template = 'coordinator/leader_login.html' if leader else 'coordinator/login.html'
    return render(request, template, {'form': form})


def user_login(request):
    return _handle_login(request, leader=False)


def leader_login(request):
    return _handle_login(request, leader=True)


@login_required
def dashboard(request):
    if _profile_for(request.user).role == 'leader':
        return redirect('leader_dashboard')
    return redirect('volunteer_dashboard')


@role_required('volunteer')
def volunteer_dashboard(request):
    profile = _profile_for(request.user)
    volunteer, _ = Volunteer.objects.get_or_create(
        user=request.user,
        defaults={'phone': profile.phone},
    )
    participations = Participation.objects.filter(
        volunteer=volunteer
    ).select_related('project', 'project__community').order_by('-signed_up_at')
    return render(request, 'coordinator/dashboard.html', {
        'profile': profile,
        'volunteer': volunteer,
        'user': request.user,
        'participations': participations,
        'total_projects': participations.count(),
        'total_hours': sum(p.hours_contributed for p in participations),
        'projects_attended': participations.filter(attended=True).count(),
    })


@role_required('leader')
def leader_dashboard(request):
    profile = _profile_for(request.user)
    communities = Community.objects.filter(leader=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, communities=communities)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f"Project announcement '{project.title}' has been posted.")
            return redirect('leader_dashboard')
    else:
        form = ProjectForm(communities=communities)
    projects = UmugandaProject.objects.filter(
        created_by=request.user
    ).select_related('community').order_by('-created_at')
    return render(request, 'coordinator/leader_dashboard.html', {
        'profile': profile,
        'communities': communities,
        'project_form': form,
        'projects': projects,
    })


@login_required
def profile_edit(request):
    profile = _profile_for(request.user)
    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST,
            request.FILES,
            user=request.user,
            profile=profile,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('dashboard')
    else:
        form = ProfileEditForm(user=request.user, profile=profile)
    return render(request, 'coordinator/profile_edit.html', {
        'form': form,
        'profile': profile,
    })