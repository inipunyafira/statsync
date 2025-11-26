from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from apps.myauth.models import CustomUser
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .forms import PDFUploadForm
# from apps.myuser.pdf_processing.extract import pdf_to_excel, upload_to_drive, extract_brs_title, extract_description_from_pdf
from apps.myuser.pdf_processing.extract import (
    get_file_size, 
    get_page_count,
    extract_abstract,
    pdf_to_excel, 
    upload_to_drive, 
    extract_brs_title, 
    # extract_description_from_pdf # <-- Import fungsi baru kita
)
# from django.conf import settings # Import settings
# from thefuzz import fuzz

from apps.myuser.pdf_processing.brs_sheets import get_sheets_gid
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.views.decorators.cache import never_cache, cache_control
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from urllib.parse import urlparse, parse_qs
from apps.myuser.models import BRSExcel, BRSsheet
from django.utils.timezone import now
import os
from .forms import BRSExcelForm
import uuid
import json
import re


def extract_file_id(url):
    """Ekstrak FILE_ID dari berbagai format URL Google Drive"""
    parsed_url = urlparse(url)

    if "drive.google.com" in parsed_url.netloc or "docs.google.com" in parsed_url.netloc:
        if "/d/" in parsed_url.path: 
            return parsed_url.path.split("/d/")[1].split("/")[0]
        elif "id=" in parsed_url.query: 
            return parse_qs(parsed_url.query).get("id", [None])[0]

# def pilih_judul_final(nama_tabel_lengkap, nama_tabel_ver2, ambang_batas=85):
#     """
#     Helper function untuk memilih judul terbaik berdasarkan skor kemiripan.
#     """
#     if not nama_tabel_ver2 or not nama_tabel_lengkap:
#         return nama_tabel_ver2 or nama_tabel_lengkap

#     # Menggunakan token_set_ratio lebih fleksibel terhadap perbedaan panjang dan urutan kata
#     skor = fuzz.token_set_ratio(nama_tabel_lengkap, nama_tabel_ver2)

#     if skor >= ambang_batas:
#         return nama_tabel_ver2  # Prioritaskan hasil YOLO jika sangat mirip
#     else:
#         return nama_tabel_lengkap # Gunakan hasil parsing teks jika tidak mirip

@login_required
@never_cache
def brstoexcel(request):
    if request.method == "POST":
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['pdf_file']
            tgl_terbit = form.cleaned_data['tgl_terbit']

            file_name = f"{uuid.uuid4().hex}.pdf"
            file_path = os.path.join("static/uploads", file_name)
            with open(file_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            extracted_title = extract_brs_title(file_path) or uploaded_file.name

            file_size = get_file_size(file_path)
            page_count = get_page_count(file_path)
            abstract_text = extract_abstract(file_path)

            excel_path, sheet_links = pdf_to_excel(file_path)

            # # Ambil nama tabel dari sheet_links
            # table_names = [sheet["judul_sheet"] for sheet in sheet_links]  # Ambil nama tabel dari sheet links

            # # Ekstraksi deskripsi per tabel
            # descriptions = extract_description_from_pdf(file_path, table_names)

            if BRSExcel.objects.filter(judul_brs=extracted_title).exists():
                os.remove(file_path)
                return JsonResponse({"error": "BRS with this title has already been uploaded."}, status=400)

            # # --- BLOK EKSTRAKSI BARU ---
            # try:
            #     # 1. Jalankan ekstraksi layout (YOLO) untuk mendapatkan judul & deskripsi akurat
            #     # PENTING: Sesuaikan path ke file model .pt Anda di sini!
            #     model_path = r"C:\Data\Kuliah\Projek_SAD\statsync\apps\myuser\pdf_processing\doclayout_yolo_docstructbench_imgsz1024.pt"
            #     # Definisikan folder output untuk debug
            #     debug_dir = os.path.join(settings.BASE_DIR, 'static', 'debug_output')
            #     os.makedirs(debug_dir, exist_ok=True) # Pastikan folder ada
            #     layout_data = extract_pdf_layout_data(file_path, model_path, debug_output_dir=debug_dir)

            #     # 2. Jalankan ekstraksi tabel (pdfplumber) untuk membuat file Excel dan mendapatkan judul legacy
            #     excel_path, sheet_links_legacy = pdf_to_excel(file_path)
                
            # except Exception as e:
            #     os.remove(file_path) # Hapus file PDF jika terjadi error
            #     return JsonResponse({"error": f"Extraction failed: {str(e)}"}, status=500)
            # # --- AKHIR BLOK EKSTRAKSI BARU ---

            drive_url, drive_file_id = upload_to_drive(excel_path, return_id=True) 

            # Hapus file Excel lokal setelah diunggah
            os.remove(excel_path)

            BRSsheet.objects.filter(id_brsexcel__id=request.user).delete()

            brs = BRSExcel.objects.create(
                judul_brs=extracted_title,
                id_file=drive_file_id,
                url_file=drive_url,
                tgl_terbit=tgl_terbit,
                id=request.user,
                deskripsi_abstrak=abstract_text,
                ukuran_file=file_size,
                jumlah_halaman=page_count
            )

            sheets_gid_mapping = get_sheets_gid(drive_file_id)
            for i, sheet in enumerate(sheet_links):
                sheet_gid = sheets_gid_mapping.get(sheet["judul_sheet"], None)
                sheet_url = f"https://docs.google.com/spreadsheets/d/{drive_file_id}/edit?gid={sheet_gid}#gid={sheet_gid}" if sheet_gid else drive_url

                table_name = sheet["judul_sheet"]
                # Menyimpan deskripsi per tabel yang relevan dengan sheet yang sesuai
                # description_for_sheet = descriptions[i] if i < len(descriptions) else "Deskripsi tidak ditemukan"
                
                BRSsheet.objects.create(
                    id_brsexcel=brs,
                    judul_sheet=table_name,
                    nama_tabel_ver2=table_name,
                    # nama_tabel_lengkap=sheet["nama_tabel_lengkap"],
                    file_sheet=sheet_url,
                    # deskripsi=description_for_sheet  # Simpan deskripsi per tabel
                )

            # # Loop berdasarkan sheet_links_legacy untuk memastikan jumlah sheet dan URL benar
            # for i, legacy_sheet in enumerate(sheet_links_legacy):
            #     sheet_gid = sheets_gid_mapping.get(legacy_sheet["judul_sheet"], None)
            #     sheet_url = f"https://docs.google.com/spreadsheets/d/{drive_file_id}/edit#gid={sheet_gid}" if sheet_gid else drive_url

            #     # Ambil data dari hasil ekstraksi layout
            #     # Tambahkan pengecekan untuk menghindari error jika jumlah tabel tidak cocok
            #     if i < len(layout_data):
            #         nama_tabel_ver2 = layout_data[i]['title_v2']
            #         deskripsi_final = layout_data[i]['description']
            #     else:
            #         # Fallback jika metode YOLO gagal mendeteksi tabel sebanyak metode lama
            #         nama_tabel_ver2 = ""
            #         deskripsi_final = "Deskripsi tidak ditemukan (layout)"

            #     # --- TAMBAHKAN LOGIKA INI ---
            #     # # Jika ini adalah tabel lanjutan, paksa deskripsi menjadi kosong 
            #     if "(Lanjutan)" in legacy_sheet["judul_sheet"]: 
            #         deskripsi_final = "" 
            #     # --- AKHIR TAMBAHAN LOGIKA ---

            #     BRSsheet.objects.create(
            #         id_brsexcel=brs,
            #         judul_sheet=legacy_sheet["judul_sheet"],
            #         nama_tabel_lengkap=legacy_sheet["nama_tabel_lengkap"], # Dari metode parsing teks
            #         nama_tabel_ver2=nama_tabel_ver2,                       # Dari metode YOLO (ver2)
            #         file_sheet=sheet_url,
            #         deskripsi=deskripsi_final                                # Deskripsi gabungan dari YOLO
            #     )

            # ⏬ Simpan info ke session (sementara)
            request.session['show_preview'] = True
            request.session['last_id_file'] = drive_file_id

            # Hapus file PDF setelah semua proses selesai
            os.remove(file_path)

            return JsonResponse({
                "success": True,
                "message": "The file has been successfully extracted!",
                "id_file": drive_file_id
            })

    else:
        form = PDFUploadForm()

    # ⏬ Ambil data hanya jika session 'show_preview' aktif
    show_preview = request.session.pop('show_preview', False)
    last_id_file = request.session.pop('last_id_file', None)

    if show_preview:
        brs_data = {'last': {'id_file': last_id_file}} if last_id_file else None
        sheet_data = BRSsheet.objects.filter(id_brsexcel__id=request.user)

    # # ... sisa kode Anda untuk GET request tidak perlu diubah ...
    # if show_preview:
    #     brs_data = {'last': {'id_file': last_id_file}} if last_id_file else None
    #     # Ambil data BRS terakhir yang diupload oleh user ini untuk ditampilkan
    #     last_brs_instance = BRSExcel.objects.filter(id_file=last_id_file, id=request.user).first()
    #     sheet_data = BRSsheet.objects.filter(id_brsexcel=last_brs_instance) if last_brs_instance else []
    else:
        brs_data = None
        sheet_data = []

    return render(request, 'user/brs-to-excel.html', {
        'form': form,
        'brs_data': brs_data,
        'sheet_data': sheet_data
    })

@login_required
@never_cache
def rekapitulasi(request):
    return render(request, 'user/rekapitulasi.html')

@login_required
@never_cache
def rekapitulasi_keseluruhan(request):
    brs_data = BRSExcel.objects.all().order_by('-tgl_terbit')  
    
    years = BRSExcel.objects.dates('tgl_terbit', 'year', order='DESC')
    years_list = [year.year for year in years]  

    return render(request, 'user/rekapitulasi-keseluruhan.html', {
        "brs_data": brs_data,
        "years": years_list  
    })

@login_required
@never_cache
def rekapitulasi_pribadi(request):
    brs_data = BRSExcel.objects.filter(id=request.user)

    years = BRSExcel.objects.filter(id=request.user).dates('tgl_terbit', 'year', order='DESC')
    years_list = [year.year for year in years] 

    if request.method == "POST" and "edit_id" in request.POST:
        brs = get_object_or_404(BRSExcel, id_brsexcel=request.POST["edit_id"])
        form = BRSExcelForm(request.POST, instance=brs)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success"})  
        return JsonResponse({"status": "error", "errors": form.errors})

    return render(request, "user/rekapitulasi-pribadi.html", {
        "brs_data": brs_data,
        "years": years_list
    })

@login_required
@never_cache
def profile_user(request):
    return render(request, 'common/profile-user.html')

@login_required
@never_cache
def update_profile_usr(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        full_name = request.POST.get("fullName", "").strip()
        username = request.POST.get("username", "").strip()

        # Cek duplikat username
        if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Username is already taken.'})

        if full_name:
            user.first_name = full_name
        if username:
            user.username = username

        user.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Profile updated successfully.'})

        return redirect(request.path)

    return render(request, "common/profile-user.html", {"user": user})

@login_required
@never_cache
def change_password_usr(request):
    if request.method == 'POST':
        current_password = request.POST.get('password')
        new_password = request.POST.get('newpassword')
        renew_password = request.POST.get('renewpassword')
        user = request.user

        # Cek jika permintaan datang dari JavaScript (AJAX) hanya untuk validasi password lama
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if user.check_password(current_password):
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({'valid': False})

        # Kalau bukan AJAX, jalankan logika ganti password seperti biasa
        if user.check_password(current_password) and new_password == renew_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
        
        return redirect('profile-user')


User = get_user_model()

@login_required
@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard_user(request):
    print("\nDEBUG: Fungsi dashboard_user() dipanggil\n")
    user_brs_count = BRSExcel.objects.filter(id=request.user).count()
    total_brs_count = BRSExcel.objects.count()
    print("DEBUG: user & total:", user_brs_count, total_brs_count)

    current_year = now().year
    current_month = now().month
    month_name = now().strftime('%B')  

    print("DEBUG: Bulan & Tahun Saat Ini:", month_name, current_year)

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

    # DEBUG: Print data ke console Django
    print("Chart Categories:", chart_categories)
    print("Chart Data:", chart_data)

    # === DEBUG: Print ke Terminal ===
    print("\n=== DEBUG DATA ===")
    print("User BRS Count:", user_brs_count)
    print("Total BRS Count:", total_brs_count)
    print("Month Name:", month_name)
    print("Chart Categories:", chart_categories)
    print("Chart Data:", chart_data)
    print("===================\n")

    context = {
        'user_brs_count': user_brs_count,
        'total_brs_count': total_brs_count,
        'month_name': month_name,
        'chart_categories': json.dumps(chart_categories),
        'chart_data': json.dumps(chart_data),
    }
    print("DEBUG: Context yang dikirim ke template:", context)
    return render(request, 'user/dashboard-user.html', context)

@never_cache
def metadata_preview(request):
    daftar_brs = BRSExcel.objects.all().order_by('-tgl_terbit')
    selected_id = request.GET.get('id')

    brs = None

    if selected_id:
        brs = get_object_or_404(BRSExcel, id_brsexcel=selected_id)

    return render(request, 'user/metadata-preview.html', {
        'daftar_brs': daftar_brs,
        'brs': brs,
    })


# @never_cache
# def metadata_preview(request):
#     daftar_brs = BRSExcel.objects.all().order_by('-tgl_terbit')
#     selected_id = request.GET.get('id')

#     brs = None
#     sheets = None

#     if selected_id:
#         brs = get_object_or_404(BRSExcel, id_brsexcel=selected_id)
#         sheets_query = BRSsheet.objects.filter(id_brsexcel=brs)
        
#         # --- TAMBAHKAN LOGIKA PERBANDINGAN DI SINI ---
#         sheets = []
#         for sheet in sheets_query:
#             # Jalankan perbandingan untuk setiap sheet
#             sheet.nama_tabel_final = pilih_judul_final(
#                 sheet.nama_tabel_lengkap, 
#                 sheet.nama_tabel_ver2
#             )
#             sheets.append(sheet)
#         # --- AKHIR LOGIKA PERBANDINGAN ---

#     return render(request, 'user/metadata-preview.html', {
#         'daftar_brs': daftar_brs,
#         'brs': brs,
#         'sheets': sheets
#     })

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def custom_login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard-user')  # Redirect ke dashboard user
        else:
            messages.error(request, "Incorrect username or password!")
            return redirect('login')  # Redirect kembali ke halaman login

@login_required
@never_cache
def delete_brs(request, id_brsexcel):
    brs = get_object_or_404(BRSExcel, id_brsexcel=id_brsexcel, id=request.user)
    BRSsheet.objects.filter(id_brsexcel=brs).delete()
    brs.delete()
    return redirect('rekapitulasi-pribadi')
