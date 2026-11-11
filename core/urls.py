from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("demo/interest/<slug:key>/", views.feature_interest, name="feature_interest"),
    path("demo/role/<slug:role>/", views.switch_role, name="switch_role"),
    path("welcome/", views.after_login, name="after_login"),
]
