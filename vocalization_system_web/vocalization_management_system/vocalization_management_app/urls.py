from django.urls import path
from . import views, adminViews, staffViews

urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.loginPage, name="login"),
    path('doLogin/', views.doLogin, name="doLogin"),
    path('logout/', views.logout_user, name="logout"),
    path('register/', views.registerPage, name="register"),  # Registration page
    path('doRegister/', views.doRegister, name="doRegister"),  # User registration processing

    # Admin URLs
    path('admin_home/', adminViews.admin_home, name="admin_home"),
    path('upload_audio/', adminViews.upload_audio, name="upload_audio"),
    path('manage_staff/', adminViews.manage_staff, name="manage_staff"),

    # Staff URLs
    path('staff_home/', staffViews.staff_home, name="staff_home"),
    path('view_audio_analysis/', staffViews.view_audio_analysis, name="view_audio_analysis"),
]
