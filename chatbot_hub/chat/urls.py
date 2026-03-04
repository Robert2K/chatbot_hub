from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]

