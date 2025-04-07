from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from apps.myauth.models import CustomUser, Role
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from django.views.decorators.cache import cache_control, never_cache
from django.contrib import messages
from apps.myauth.models import CustomUser
from apps.myuser.models import BRSExcel
import json
from django.utils.timezone import now
from django.db.models import Count



@login_required
@never_cache
def manage_users(request):
    users = CustomUser.objects.select_related('id_role').all()  # Ambil data user beserta role-nya
    roles = Role.objects.all()  # Ambil daftar semua role
    return render(request, "admin/manage-users.html", {"users": users, "roles": roles})  # Kirim data roles ke template

@login_required
@never_cache
def change_user_role(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_role_id = request.POST.get("role_id")

        user = get_object_or_404(CustomUser, id=user_id)
        new_role = get_object_or_404(Role, id_role=new_role_id)

        user.id_role = new_role
        user.save()

        return JsonResponse({"success": True, "new_role": new_role.nama_role})

    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard_admin(request):
    # Grafik BRS Perbulan
    total_users = CustomUser.objects.count()  
    user_brs_count = BRSExcel.objects.filter(id=request.user).count()
    total_brs_uploaded = BRSExcel.objects.count()

    current_year = now().year
    current_month = now().month
    month_name = now().strftime('%B')  

    def get_week_of_month(date):
        first_day = date.replace(day=1)
        adjusted_dom = date.day + first_day.weekday()
        return (adjusted_dom - 1) // 7 + 1

    brs_per_week = (
        BRSExcel.objects
        .filter(tgl_up__year=current_year, tgl_up__month=current_month)
        .values_list('tgl_up', flat=True)
    )

    week_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for date in brs_per_week:
        week_num = get_week_of_month(date)
        if 1 <= week_num <= 4:
            week_counts[week_num] += 1

    chart_categories = ["Week 1", "Week 2", "Week 3", "Week 4"]
    chart_data = [week_counts[1], week_counts[2], week_counts[3], week_counts[4]]

    # Grafik BRS User
    user_uploads = (
        BRSExcel.objects.values('id__username')
        .annotate(total_uploads=Count('id'))
        .order_by('-total_uploads')  
    )
    
    usernames = [user['id__username'] for user in user_uploads]
    upload_counts = [user['total_uploads'] for user in user_uploads]

    context = {
        'total_users': total_users,
        'user_brs_count': user_brs_count,
        'total_brs_uploaded': total_brs_uploaded,
        'usernames': json.dumps(usernames),
        'upload_counts': json.dumps(upload_counts),
        'month_name': month_name,
        'chart_categories': json.dumps(chart_categories),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'admin/dashboard-admin.html', context)

@login_required
@never_cache
def log_activity(request):
    users = CustomUser.objects.filter(brsexcel__isnull=False).distinct()

    log_data = {}
    
    for user in users:
        user_logs = BRSExcel.objects.filter(id=user.id).order_by('-tgl_up')
        log_data[user.username] = user_logs  # Simpan dalam dict
    return render(request, 'admin/log-activity.html', {'log_data': log_data})

User = get_user_model()

@login_required
@never_cache
def profile_admin(request):
    return render(request, 'common/profile-admin.html')

@login_required
@never_cache
def profile_view(request):
    user = request.user  

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()  # Ambil full name dari form
        username = request.POST.get("username", "").strip()

        if not full_name:
            messages.error(request, "Full name cannot be empty.")
            return redirect("profile-admin")

        if not username:
            messages.error(request, "Username cannot be empty.")
            return redirect("profile-admin")

        if User.objects.filter(username=username).exclude(id=user.id).exists():
            messages.error(request, "Username is already taken.")
            return redirect("profile-admin")

        # Simpan full name langsung ke first_name
        user.first_name = full_name  
        user.username = username
        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile-admin")  

    return render(request, "common/profile-admin.html", {"user": user})

@login_required
@never_cache
def update_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        full_name = request.POST.get("fullName", "").strip()
        username = request.POST.get("username", "").strip()

        if full_name:
            user.first_name = full_name
        if username:
            user.username = username

        user.save()
        return redirect(request.path)  # Redirect ke halaman yang sama setelah update

    return render(request, "common/profile-admin.html", {"user": user})

@login_required
@never_cache
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('password')
        new_password = request.POST.get('newpassword')
        renew_password = request.POST.get('renewpassword')

        user = request.user

        # Cek apakah current password benar
        if user.check_password(current_password) and new_password == renew_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # Agar tetap login
        return redirect('profile-admin')  # Kembali ke halaman profil

    return redirect('profile-admin')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def custom_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Cek parameter next agar hanya redirect ke halaman yang diizinkan
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return redirect('dashboard-admin')  # Redirect default setelah login

        else:
            return render(request, 'login.html', {'error': 'Username atau password salah'})

    return render(request, 'login.html')

def custom_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard-admin')  # Redirect ke halaman dashboard
        else:
            messages.error(request, "Username atau password salah!")
            return redirect('login')  # Redirect kembali ke halaman login
    
    return render(request, 'login.html')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def logout_view(request):
    logout(request)
    request.session.flush()  # Hapus seluruh data sesi
    return redirect('login')

