import random
import mimetypes
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.db.models import Q
from django.http import FileResponse, Http404
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from functools import wraps
from coordinator.forms import (
    AnnouncementForm,
    LeaderRegisterForm,
    LoginForm,
    JournalCommentForm,
    ProfileEditForm,
    ProjectForm,
    RegisterForm,
)




from coordinator.models import (
    Announcement,
    Community,
    JournalComment,
    Participation,
    UmugandaProject,
    UmugandaJournal,
    UserProfile,
    Volunteer,
    Testimonial,
)


def home(request):
    today = timezone.localdate()
    active_announcements = (
        Announcement.objects.filter(is_published=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=today))
        .select_related('created_by')
        .order_by('-created_at', '-id')
    )
    announcements = list(active_announcements[:2])
    testimonials = list(
        Testimonial.objects.filter(
            is_published=True,
            consent_confirmed=True,
        ).order_by('-created_at', '-id')[:20]
    )
    published_journals = UmugandaJournal.objects.filter(is_published=True)
    journal_count = published_journals.count()
    journal_photo_stories = {
        journal.homepage_photo: journal
        for journal in published_journals.exclude(homepage_photo__isnull=True)
    }
    journals = published_journals.order_by('-activity_date', '-id')[:4]
    journal_story_cards = published_journals.filter(
        homepage_photo__isnull=True,
    ).prefetch_related('photos')[:4]
    is_volunteer = request.user.is_authenticated and (
        UserProfile.objects.filter(user=request.user, role='volunteer').exists()
        or Volunteer.objects.filter(user=request.user).exists()
    )
    random.shuffle(testimonials)
    return render(request, 'coordinator/home.html', {
        'announcements': announcements,
        'announcement_count': active_announcements.count(),
        'testimonials': testimonials[:3],
        'journals': journals,
        'journal_count': journal_count,
        'journal_story_cards': journal_story_cards,
        'journal_photo_stories': journal_photo_stories,
        'is_volunteer': is_volunteer,
    })


def announcement_list(request):
    today = timezone.localdate()
    announcements = Announcement.objects.filter(
        is_published=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=today),
    ).select_related('created_by').order_by('-created_at', '-id')
    page_obj = Paginator(announcements, 10).get_page(request.GET.get('page'))
    return render(request, 'coordinator/announcement_list.html', {
        'page_obj': page_obj,
        'announcements': page_obj.object_list,
    })


def journal_detail(request, slug):
    journal = get_object_or_404(
        UmugandaJournal.objects.prefetch_related('photos'),
        slug=slug,
        is_published=True,
    )
    if request.method == 'POST':
        comment_form = JournalCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.journal = journal
            comment.save()
            messages.success(request, 'Your comment was submitted for review.')
            return redirect(f'{reverse("journal_detail", args=[journal.slug])}#comments')
    else:
        comment_form = JournalCommentForm()

    return render(request, 'coordinator/journal_detail.html', {
        'journal': journal,
        'comments': journal.comments.filter(is_approved=True),
        'comment_form': comment_form,
        'related_journals': UmugandaJournal.objects.filter(
            is_published=True,
        ).exclude(pk=journal.pk)[:3],
    })


def journal_list(request):
    journals = UmugandaJournal.objects.filter(
        is_published=True,
    ).order_by('-activity_date', '-id')
    page_obj = Paginator(journals, 12).get_page(request.GET.get('page'))
    return render(request, 'coordinator/journal_list.html', {
        'page_obj': page_obj,
        'journals': page_obj.object_list,
    })


class ConfiguredPasswordResetView(auth_views.PasswordResetView):
    def form_valid(self, form):
        if not settings.DEBUG and not settings.EMAIL_HOST:
            return render(
                self.request,
                self.template_name,
                {
                    'form': form,
                    'email_not_configured': True,
                },
                status=503,
            )
        return super().form_valid(form)


def serve_journal_media(request, file_path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    journal_root = (media_root / 'journals').resolve()
    image_path = (journal_root / file_path).resolve()
    try:
        image_path.relative_to(journal_root)
    except ValueError as error:
        raise Http404 from error

    if not image_path.is_file():
        raise Http404

    stored_path = image_path.relative_to(media_root).as_posix()
    is_published = UmugandaJournal.objects.filter(is_published=True).filter(
        Q(cover_image=stored_path) | Q(photos__image=stored_path),
    ).exists()
    if not is_published and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404

    response = FileResponse(
        image_path.open('rb'),
        content_type=mimetypes.guess_type(image_path.name)[0] or 'application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _volunteer_project_scope(profile):
    if not profile.province:
        return Q(pk__in=[])

    scope = Q(community__province=profile.province)
    for field in ('district', 'sector', 'cell', 'village'):
        value = getattr(profile, field)
        if not value:
            return Q(pk__in=[])
        scope &= Q(**{f'community__{field}__in': ['', value]})
    return scope



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
    projects = UmugandaProject.objects.filter(
        status='planned',
        date__gte=timezone.localdate(),
    ).select_related('community').order_by('date', 'id')
    if request.user.is_authenticated:
        profile = _profile_for(request.user)
        if profile.role == 'volunteer':
            projects = projects.filter(_volunteer_project_scope(profile))

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

    paginator = Paginator(projects, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Group the current page by province for better organization.
    projects_by_province = {}
    for project in page_obj.object_list:
        province = project.community.get_province_display()
        if province not in projects_by_province:
            projects_by_province[province] = []
        projects_by_province[province].append(project)

    context = {
        'projects_by_province': projects_by_province,
        'total_projects': paginator.count,
        'page_obj': page_obj,
        'pagination_query': request.GET.copy(),
        'search_query': search_query,
        'province_filter': province_filter,
        'district_filter': district_filter,
        'sector_filter': sector_filter,
        'cell_filter': cell_filter,
        'village_filter': village_filter,
        'date_from': date_from,
        'date_to': date_to,
        'available_provinces': Community.PROVINCE_CHOICES,
        'available_districts': districts.exclude(district='').values_list('district', flat=True).distinct().order_by('district'),
        'available_sectors': sectors.exclude(sector='').values_list('sector', flat=True).distinct().order_by('sector'),
        'available_cells': cells.exclude(cell='').values_list('cell', flat=True).distinct().order_by('cell'),
        'available_villages': villages.exclude(village='').values_list('village', flat=True).distinct().order_by('village'),
    }
    context['pagination_query'].pop('page', None)
    context['pagination_query'] = context['pagination_query'].urlencode()
    return render(request, 'coordinator/project_list.html', context)

def project_detail(request, project_id):
    """Show details of a specific project"""
    projects = UmugandaProject.objects.filter(
        status='planned',
        date__gte=timezone.localdate(),
    )
    if request.user.is_authenticated:
        profile = _profile_for(request.user)
        if profile.role == 'volunteer':
            projects = projects.filter(_volunteer_project_scope(profile))
    project = get_object_or_404(
        projects,
        id=project_id,
    )
    # Get participants for this project
    participants = Participation.objects.filter(project=project).select_related('volunteer__user')
    
    # Check if user is already signed up
    is_signed_up = project.is_user_signed_up(request.user)
    
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
    profile = _profile_for(request.user)
    if profile.role != 'volunteer':
        messages.error(request, "Community leaders cannot sign up as volunteers.")
        return redirect('leader_dashboard')

    project = get_object_or_404(
        UmugandaProject.objects.filter(
            status='planned',
            date__gte=timezone.localdate(),
        ).filter(_volunteer_project_scope(profile)),
        id=project_id,
    )
    
    # Check if user is already a volunteer
    volunteer, created = Volunteer.objects.get_or_create(
        user=request.user,
        defaults={'phone': profile.phone}
    )
    # Check if already signed up
    if Participation.objects.filter(volunteer=volunteer, project=project).exists():
        messages.info(request, "You are already signed up for this project!")
    else:
        # Create participation record
        Participation.objects.create(volunteer=volunteer, project=project)
        messages.success(request, f"You have successfully signed up for {project.title}!")
    
    # Update community if not set
    if not volunteer.community:
        volunteer.community = project.community
        volunteer.save()
    
    return redirect('project_detail', project_id=project_id)
def register(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            request.session['show_volunteer_signup_success'] = True
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'coordinator/register.html', {'form': form})

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
    assigned_community = Community.objects.filter(leader=user).first()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': 'leader' if assigned_community else 'volunteer',
            'leader_type': 'village' if assigned_community else '',
            'community': assigned_community,
            'province': assigned_community.province if assigned_community else '',
            'district': assigned_community.district if assigned_community else '',
            'sector': assigned_community.sector if assigned_community else '',
            'cell': assigned_community.cell if assigned_community else '',
            'village': assigned_community.village if assigned_community else '',
            'is_approved': False,
            'phone': volunteer_phone or '',
        },
    )
    if profile.role == 'leader' and not profile.community_id and assigned_community:
        profile.community = assigned_community
        profile.leader_type = profile.leader_type or 'village'
        profile.save(update_fields=['community', 'leader_type'])
    return profile


def role_required(role):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            profile = _profile_for(request.user)
            if profile.role != role:
                messages.error(request, "You don't have access to that dashboard.")
                return redirect('dashboard')
            if role == 'leader' and not profile.is_approved:
                messages.info(
                    request,
                    "Your leader application is awaiting administrator approval.",
                )
                return redirect('home')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def leader_register(request):
    if request.method == 'POST':
        form = LeaderRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your leader application was submitted. You can sign in after an administrator verifies and approves it.",
            )
            return redirect('leader_login')
    else:
        form = LeaderRegisterForm()
    return render(request, 'coordinator/leader_register.html', {'form': form})


def _handle_login(request, *, leader):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            profile = _profile_for(user)
            is_leader = profile.role == 'leader'
            if is_leader and not profile.is_approved:
                form.add_error(
                    None,
                    "Your leader application is awaiting administrator approval.",
                )
            elif is_leader != leader:
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
        'show_signup_success': request.session.pop(
            'show_volunteer_signup_success',
            False,
        ),
    })


@role_required('leader')
def leader_dashboard(request):
    profile = _profile_for(request.user)
    communities = profile.managed_communities()
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
    announcements = Announcement.objects.filter(
        created_by=request.user,
    ).order_by('-created_at')
    context = _leader_dashboard_context(profile, communities, projects, announcements)
    context.update({
        'profile': profile,
        'communities': communities,
        'managed_area': profile.managed_area_label(),
        'project_form': form,
        'projects': projects,
        'announcement_form': AnnouncementForm(
            initial={'area': profile.managed_area_label()}
        ),
        'today': timezone.localdate(),
    })
    return render(request, 'coordinator/leader_dashboard.html', context)


def _leader_dashboard_context(profile, communities, projects, announcements):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    week_end = today + timedelta(days=7)
    participations = Participation.objects.filter(project__in=projects)
    total_participations = participations.count()
    attended_participations = participations.filter(attended=True).count()
    pie_percent = round(attended_participations * 100 / total_participations) if total_participations else 0
    project_total = projects.count()
    chart_height = lambda value: max(3, round(value * 65 / project_total)) if project_total else 0
    return {
        'profile': profile,
        'managed_area': profile.managed_area_label(),
        'announcements': announcements,
        'projects': projects,
        'active_project_count': projects.filter(status__in=('planned', 'ongoing')).count(),
        'published_update_count': announcements.filter(is_published=True).count(),
        'projects_this_month': projects.filter(created_at__date__gte=month_start).count(),
        'upcoming_project_count': projects.filter(
            date__gte=today,
            date__lt=week_end,
            status__in=('planned', 'ongoing'),
        ).count(),
        'community_member_count': Volunteer.objects.filter(community__in=communities).count(),
        'members_this_month': Volunteer.objects.filter(
            community__in=communities,
            user__date_joined__date__gte=month_start,
        ).count(),
        'updates_this_month': announcements.filter(
            is_published=True,
            created_at__date__gte=month_start,
        ).count(),
        'upcoming_activities': projects.filter(
            date__gte=today,
            date__lt=week_end,
            status__in=('planned', 'ongoing'),
        ).order_by('date', 'start_time')[:6],
        'planned_projects': projects.filter(status='planned').count(),
        'ongoing_projects': projects.filter(status='ongoing').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'total_projects': project_total,
        'planned_bar_height': chart_height(projects.filter(status='planned').count()),
        'ongoing_bar_height': chart_height(projects.filter(status='ongoing').count()),
        'completed_bar_height': chart_height(projects.filter(status='completed').count()),
        'total_participations': total_participations,
        'attended_participations': attended_participations,
        'not_attended_participations': total_participations - attended_participations,
        'attendance_percent': pie_percent,
        'attendance_pie_style': (
            f'conic-gradient(#0b8067 0 {pie_percent}%, #e6edf0 {pie_percent}% 100%)'
        ),
        'today': today,
    }


@role_required('leader')
def leader_residents(request):
    profile = _profile_for(request.user)
    communities = profile.managed_communities()
    residents = Volunteer.objects.filter(
        community__in=communities,
    ).select_related('user', 'community').order_by(
        'user__last_name', 'user__first_name', 'user__username',
    )
    search = request.GET.get('q', '').strip()
    if search:
        residents = residents.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
            | Q(phone__icontains=search)
            | Q(community__district__icontains=search)
            | Q(community__sector__icontains=search)
            | Q(community__cell__icontains=search)
            | Q(community__village__icontains=search)
        )
    page_obj = Paginator(residents, 25).get_page(request.GET.get('page'))
    return render(request, 'coordinator/leader_residents.html', {
        'profile': profile,
        'residents': page_obj.object_list,
        'page_obj': page_obj,
        'search': search,
        'managed_area': profile.managed_area_label(),
        'total_residents': residents.count(),
        'province_name': dict(Community.PROVINCE_CHOICES).get(profile.province, profile.province),
    })


@role_required('leader')
def leader_announcement_create(request):
    if request.method != 'POST':
        return redirect('leader_dashboard')
    form = AnnouncementForm(request.POST)
    if form.is_valid():
        announcement = form.save(commit=False)
        announcement.created_by = request.user
        announcement.save()
        messages.success(request, "Your community announcement has been published.")
        return redirect('leader_dashboard')

    profile = _profile_for(request.user)
    communities = profile.managed_communities()
    projects = UmugandaProject.objects.filter(
        created_by=request.user,
    ).select_related('community').order_by('-created_at')
    context = _leader_dashboard_context(profile, communities, projects, Announcement.objects.filter(
        created_by=request.user,
    ).order_by('-created_at'))
    context.update({
        'profile': profile,
        'communities': communities,
        'managed_area': profile.managed_area_label(),
        'project_form': ProjectForm(communities=communities),
        'announcement_form': form,
    })
    return render(request, 'coordinator/leader_dashboard.html', context)


@role_required('leader')
def leader_announcement_edit(request, announcement_id):
    announcement = get_object_or_404(
        Announcement,
        pk=announcement_id,
        created_by=request.user,
    )
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Your community announcement has been updated.")
            return redirect('leader_dashboard')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'coordinator/leader_announcement_form.html', {
        'form': form,
        'announcement': announcement,
    })


@role_required('leader')
def leader_announcement_delete(request, announcement_id):
    if request.method != 'POST':
        return redirect('leader_dashboard')
    announcement = get_object_or_404(
        Announcement,
        pk=announcement_id,
        created_by=request.user,
    )
    announcement.delete()
    messages.success(request, "Your community announcement has been deleted.")
    return redirect('leader_dashboard')


@role_required('leader')
def leader_project_edit(request, project_id):
    project = get_object_or_404(
        UmugandaProject.objects.select_related('community'),
        pk=project_id,
        created_by=request.user,
    )
    communities = _profile_for(request.user).managed_communities()
    if request.method == 'POST':
        form = ProjectForm(request.POST, communities=communities, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project announcement '{project.title}' has been updated.")
            return redirect('leader_dashboard')
    else:
        form = ProjectForm(communities=communities, instance=project)
    return render(request, 'coordinator/leader_project_edit.html', {
        'form': form,
        'project': project,
    })


@role_required('leader')
def leader_project_delete(request, project_id):
    project = get_object_or_404(
        UmugandaProject,
        pk=project_id,
        created_by=request.user,
    )
    if request.method == 'POST':
        title = project.title
        project.delete()
        messages.success(request, f"Project announcement '{title}' has been deleted.")
    return redirect('leader_dashboard')


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
