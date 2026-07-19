from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics, name='analytics'),
    path('reports/', views.reports, name='reports'),
    path('download-report/', views.download_report, name='download_report'),
    path('activity/', views.activity, name='activity'),
    path('delete-dataset/<int:dataset_id>/', views.delete_dataset, name='delete_dataset'),
    path('load-dataset/<int:dataset_id>/', views.load_dataset, name='load_dataset'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
]