from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CustomUser, Role
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache


def user_register(request):
    if request.method == "POST":
        name = request.POST['name']
        username = request.POST['username']
        password = request.POST['password']
        confpassword = request.POST['confirmPassword']

        if password == confpassword:
            # Pastikan username belum terdaftar
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Username is already taken!")
                return redirect('register')

            # Buat user baru
            user = CustomUser.objects.create_user(username=username, password=password)
            user.first_name = name

            # Tetapkan role default (User)
            role, created = Role.objects.get_or_create(nama_role='User')
            user.id_role = role  # Asumsi CustomUser memiliki foreign key ke Role
            user.save()

            messages.success(request, "Account successfully created! Please log in.")
            return redirect('login')

    return render(request, "auth/register.html")

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST["password"]
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)

            # Redirect berdasarkan role
            if user.id_role and user.id_role.nama_role == "Admin":
                return redirect('dashboard-admin')
            else:
                return redirect('dashboard-user')

        else:
            messages.error(request, "Incorrect username or password!")
            return redirect('login')

    return render(request, "auth/login.html")

@login_required
def dashboard_admin(request):
    return render(request, "admin/dashboard-admin.html", context)

@login_required
def dashboard_user(request):
    return render(request, "user/dashboard-user.html")

@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response.delete_cookie('sessionid')  # Pastikan cookie sesi dihapus
    return response

