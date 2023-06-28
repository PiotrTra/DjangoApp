from django.urls import path

# from .views import SignUpView
from . import views

app_name = "Accounts"

urlpatterns = [
    path("login/", views.render_login, name="login"),
    path("login/result", views.login_view, name="login_send"),
    path("signup", views.signup_result, name="signup_send"),
]
