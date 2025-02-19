from django.urls import path
from . import views, adminViews, staffViews

urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.loginPage, name="login"),
    path('doLogin/', views.doLogin, name="doLogin"),
    path('logout/', views.logout_user, name="logout"),
    path('register/', views.registerPage, name="register"),  # Registration page
    path('doRegister/', views.doRegister, name="doRegister"),  # User registration processing

    # Common URLs
    path('spectrograms/', views.view_spectrograms, name='view_spectrograms'),
    path('spectrograms/<int:file_id>/', views.view_spectrograms, name='view_spectrograms'),

    # Admin URLs
    path('admin_home/', adminViews.admin_home, name="admin_home"),
    path('upload_audio/', adminViews.upload_audio, name="upload_audio"),
    path('manage_staff/', adminViews.manage_staff, name="manage_staff"),

    # Staff URLs
    path('staff_home/', staffViews.staff_home, name="staff_home"),
    path('view_audio_analysis/', staffViews.view_audio_analysis, name="view_audio_analysis"),

    path('change_password/', views.change_password, name="change_password"),
    path('clips/', views.view_extracted_clips, name='view_extracted_clips'),
    path('clips/<int:file_id>/', views.view_extracted_clips, name='view_extracted_clips'),
]
