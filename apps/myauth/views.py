# from django.shortcuts import render
# from django.contrib.auth import views as auth_views

# # Contoh view untuk login
# def login_view(request):
#     return auth_views.LoginView.as_view(template_name='myauth/login.html')(request)

# # Contoh view untuk logout
# def logout_view(request):
#     return auth_views.LogoutView.as_view()(request)

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
    return render(request, "admin/dashboard.html")

@login_required
def dashboard_user(request):
    return render(request, "user/dashboard.html")

@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response.delete_cookie('sessionid')  # Pastikan cookie sesi dihapus
    return response




# from django.shortcuts import render

# def dashboard_user(request):
#     return render(request, 'user/dashboard-user.html')

# def brstoexcel(request):
#     return render(request, 'user/brs-to-excel.html')

# def rekapitulasi(request):
#     return render(request, 'user/rekapitulasi.html')

# def rekapitulasi_keseluruhan(request):
#     return render(request, 'user/rekapitulasi-keseluruhan.html')

# def rekapitulasi_pribadi(request):
#     return render(request, 'user/rekapitulasi-pribadi.html')

# def profile_user(request):
#     return render(request, 'common/profile-user.html')
