from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CustomUser, Role
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
import re


def user_register(request):
    if request.method == "POST":
        name = request.POST['name']
        username = request.POST['username']
        password = request.POST['password']
        confpassword = request.POST['confirmPassword']

        # Validasi password: minimal 8 karakter, kombinasi huruf dan angka
        password_regex = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$')

        if password != confpassword:
            response_data = {'status': 'error', 'message': 'Password and confirm password do not match.'}
        elif not password_regex.match(password):
            response_data = {'status': 'error', 'message': 'Password must be at least 8 characters long and include both letters and numbers.'}
        elif CustomUser.objects.filter(username=username).exists():
            response_data = {'status': 'error', 'message': 'Username is already taken.'}
        else:
            # Buat user baru
            user = CustomUser.objects.create_user(username=username, password=password)
            user.first_name = name
            role, created = Role.objects.get_or_create(nama_role='User')
            user.id_role = role
            user.save()
            response_data = {'status': 'success', 'message': 'Account successfully created. Redirecting to login.', 'redirect_url': '/login/'}
        
        # Cek apakah request dari AJAX/JavaScript
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(response_data)
        else:
            # fallback ke flow biasa
            if response_data['status'] == 'success':
                messages.success(request, response_data['message'])
                return redirect('login')
            else:
                messages.error(request, response_data['message'])
                return redirect('register')

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
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Incorrect username or password!'})
            else:
                messages.error(request, "Incorrect username or password!")
                return redirect('login')

    return render(request, "auth/login.html")

@never_cache
def user_logout(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response.delete_cookie('sessionid')  # Pastikan cookie sesi dihapus
    return response

