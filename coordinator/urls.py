from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/signup/', views.volunteer_signup, name='volunteer_signup'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
     path('login/', views.user_login, name='login'),  
    path('logout/', views.user_logout, name='logout'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('faq/', views.faq, name='faq'),
]