from django.contrib import admin
from django.urls import path, include
from . import views, adminViews

urlpatterns = [
    path('', views.loginPage, name="login"),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('doLogin/', views.doLogin, name="doLogin"),
    path('get_user_details/', views.get_user_details, name="get_user_details"),
    path('logout_user/', views.logout_user, name="logout_user"),
    path('admin_dashboard/', adminViews.admin_dashboard, name="admin_dasshboard"),
    path('add_big_cat/', adminViews.add_big_cat, name="add_big_cat"),
    path('add_vocalization/', adminViews.add_vocalization, name="add_vocalization"),
    path('edit_big_cat/', adminViews.edit_big_cat, name="edit_big_cat"),
    path('delete_big_cat/', adminViews.delete_big_cat, name="delete_big_cat"),
    path('delete_vocalization/', adminViews.delete_vocalization, name="delete_vocalization"),
    path('login_required/<staff_id>/', adminViews.login_required, name="login_required"),
]