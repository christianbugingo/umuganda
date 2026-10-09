from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/signup/', views.volunteer_signup, name='volunteer_signup'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/volunteer/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('dashboard/leader/', views.leader_dashboard, name='leader_dashboard'),
    path(
        'dashboard/leader/projects/<int:project_id>/edit/',
        views.leader_project_edit,
        name='leader_project_edit',
    ),
    path(
        'dashboard/leader/projects/<int:project_id>/delete/',
        views.leader_project_delete,
        name='leader_project_delete',
    ),
    path(
        'dashboard/leader/announcements/new/',
        views.leader_announcement_create,
        name='leader_announcement_create',
    ),
    path(
        'dashboard/leader/announcements/<int:announcement_id>/edit/',
        views.leader_announcement_edit,
        name='leader_announcement_edit',
    ),
    path(
        'dashboard/leader/announcements/<int:announcement_id>/delete/',
        views.leader_announcement_delete,
        name='leader_announcement_delete',
    ),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('login/', views.user_login, name='login'),
    path('leaders/register/', views.leader_register, name='leader_register'),
    path('leaders/login/', views.leader_login, name='leader_login'),
    path('logout/', views.user_logout, name='logout'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('faq/', views.faq, name='faq'),
]