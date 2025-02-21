from django.urls import path
from . import views, adminViews, staffViews

urlpatterns = [
    # Authentication URLs
    path('', views.loginPage, name="login"),
    path('doLogin/', views.doLogin, name="doLogin"),
    path('logout_user/', views.logout_user, name="logout_user"),
    path('register/', views.registerPage, name="register"),
    path('doRegister/', views.doRegister, name="doRegister"),
    
    # Admin URLs
    path('admin_home/', adminViews.admin_home, name="admin_home"),
    path('upload_audio/', adminViews.upload_audio, name="upload_audio"),
    path('manage_staff/', adminViews.manage_staff, name="manage_staff"),
    path('view_spectrograms/<int:file_id>/', adminViews.view_spectrograms, name="admin_view_spectrograms"),
    
    # Staff URLs
    path('staff_home/', staffViews.staff_home, name="staff_home"),
    path('staff/view_spectrograms/<int:file_id>/', staffViews.view_spectrograms, name="staff_view_spectrograms"),
]
