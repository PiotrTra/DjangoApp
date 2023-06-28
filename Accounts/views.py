from datetime import date

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import render, redirect

from django.contrib.auth import authenticate, login
from CinemaSite.models import Client


def render_login(request, content=None):
    return render(request, "registration/login_signup.html", content)


def login_view(request):
    username = request.POST['login-l']
    password = request.POST['password-l']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return redirect('home')
    else:
        content = {
            "error_message": "Nieprawidłowe hasło lub login. Pamiętaj, że wielkość liter ma znaczenie!"
        }
        return render(request, "registration/login_signup.html", content)


def calculate_age(born=date.today()):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def signup_result(request):
    if is_ajax(request):
        login_var = request.POST.get("login", None)
        email_var = request.POST.get("email", None)
        birthday_var = request.POST.get("birthdate", None)

        if login_var is not None:
            if User.objects.filter(username=login_var).exists():
                return JsonResponse({"LOGIN": False}, status=200)
            else:
                return JsonResponse({"LOGIN": True}, status=200)

        if email_var is not None:
            if User.objects.filter(email=email_var).exists():
                return JsonResponse({"EMAIL": False}, status=200)
            else:
                return JsonResponse({"EMAIL": True}, status=200)

        if birthday_var is not None:
            if calculate_age(date.fromisoformat(birthday_var)) < 13:
                return JsonResponse({"BD": False}, status=200)
            else:
                return JsonResponse({"BD": True}, status=200)

    else:
        try:
            new_user = User.objects.create_user(username=request.POST['login-s'],
                                                email=request.POST['email-s'],
                                                password=request.POST['password-s'],
                                                first_name=request.POST['name-s'],
                                                last_name=request.POST['surname-s']
                                                )
            new_client = Client(
                user=new_user,
                name=request.POST["name-s"],
                surname=request.POST["surname-s"],
                date_of_birth=request.POST["birthday-s"]
            )
            new_client.save()
            new_user.save()

            return render(request, 'registration/signup_result.html')
        except ValidationError:
            return HttpResponse("Nieznany błąd", ValidationError.messages)


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'