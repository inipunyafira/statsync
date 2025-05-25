from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.myuser.models import BRSExcel
from apps.myuser.views import extract_file_id
from django.utils.timezone import now
from django.core.files.uploadedfile import SimpleUploadedFile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.files.uploadedfile import SimpleUploadedFile
import io


User  = get_user_model()

def create_valid_pdf():
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "This is a valid PDF file.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return SimpleUploadedFile("brs.pdf", buffer.read(), content_type="application/pdf")

class UserViewsTestCase(TestCase):
    def setUp(self):
        # Membuat user test
        self.user = User.objects.create_user(username='testing05', password='testing05')

    def test_01_custom_login_valid(self):
        """TC_WB_USR_012: Menguji fungsi custom_login_user() dengan data yang valid oleh user"""
        response = self.client.post(reverse('custom_login_user'), {  # Pastikan ini sesuai dengan URL yang benar
            'username': 'testing05',
            'password': 'testing05',
        })
        self.assertRedirects(response, reverse('dashboard-user'))  # Pastikan ini sesuai dengan URL yang benar
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, 'testing05')

    def test_02_custom_login_invalid(self):
        """TC_WB_USR_013: Menguji fungsi custom_login_user() dengan data yang tidak valid oleh user"""
        response = self.client.post(reverse('custom_login_user'), {  # Pastikan ini sesuai dengan URL yang benar
            'username': 'testing05',
            'password': 'wrongpassword',
        }, follow=True)
        self.assertRedirects(response, reverse('login'))  # Pastikan ini sesuai dengan URL yang benar
        messages = list(response.context.get('messages'))
        self.assertTrue(any("Incorrect username or password!" in str(m) for m in messages))
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

    def test_03_dashboard_user(self):
        self.client.login(username='testing05', password='testing05')
        
        # Membuat data BRSExcel untuk user ini agar ada data diproses di view
        BRSExcel.objects.create(id=self.user, tgl_up=now(), tgl_terbit=now())
        BRSExcel.objects.create(id=self.user, tgl_up=now(), tgl_terbit=now())
        response = self.client.get(reverse('dashboard-user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/dashboard-user.html')
        # Contoh assert untuk data yang diharapkan di context
        self.assertIn('user_brs_count', response.context)
        self.assertIn('total_brs_count', response.context)
        self.assertIn('month_name', response.context)
        self.assertIn('chart_categories', response.context)
        self.assertIn('chart_data', response.context)

    def test_04_extract_file_id_valid(self):
        """TC_WB_USR_001: Menguji fungsi extract_file_id() dengan URL Google Drive valid"""
        url = "https://drive.google.com/file/d/1A2B3C4D5E6F7/edit"
        file_id = extract_file_id(url)
        self.assertEqual(file_id, "1A2B3C4D5E6F7")

    def test_05_brstoexcel_valid_pdf(self):
        """TC_WB_USR_002: Menguji fungsi brstoexcel() dengan file PDF valid oleh user"""
        # Menggunakan path yang benar ke file PDF yang valid
        pdf_path = r'C:\Data\Kuliah\Projek_SAD\statsync\htmlcov\25_01.pdf'
        with open(pdf_path, 'rb') as pdf_file:
            uploaded_file = SimpleUploadedFile("25_01.pdf", pdf_file.read(), content_type="application/pdf")
            self.client.login(username='testing05', password='testing05')  # Pastikan pengguna terautentikasi
            response = self.client.post(reverse('brs-to-excel'), {
                'pdf_file': uploaded_file,
                'tgl_terbit': '2025-01-05',
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json().get('success', False))

    def test_06_brstoexcel_duplicate_file(self):
        """TC_WB_USR_003: Menguji fungsi brstoexcel() dengan file PDF yang sama oleh user"""
        pdf_path = r'C:\Data\Kuliah\Projek_SAD\statsync\htmlcov\25_01.pdf'
        with open(pdf_path, 'rb') as pdf_file:
            uploaded_file = SimpleUploadedFile("25_01.pdf", pdf_file.read(), content_type="application/pdf")
            self.client.login(username='testing05', password='testing05')  # Pastikan pengguna terautentikasi
            
            # Pertama kali mengunggah file
            response = self.client.post(reverse('brs-to-excel'), {
                'pdf_file': uploaded_file,
                'tgl_terbit': '2025-01-05',
            })
            print("First upload response:", response.json())  # Log response untuk debugging
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json().get('success', False))

            # Cek apakah file sudah ada di database
            extracted_title = response.json().get('id_file')  # Ambil judul dari response jika ada
            print("Extracted title:", extracted_title)  # Debugging line
            duplicate_check = BRSExcel.objects.filter(judul_brs=extracted_title)
            print("Duplicate check after first upload:", duplicate_check.exists())
            self.assertTrue(duplicate_check.exists())

            # Mengunggah file yang sama lagi
            response = self.client.post(reverse('brs-to-excel'), {
                'pdf_file': uploaded_file,
                'tgl_terbit': '2025-04-05',
            })

            # Periksa status kode untuk pengunggahan duplikat
            print("Second upload response:", response.json())  # Log response untuk debugging
            self.assertEqual(response.status_code, 400)  # Mengharapkan 400 untuk pengunggahan duplikat
            self.assertIn("BRS with this title has already been uploaded", response.json().get("error"))

    def test_07_rekapitulasi(self):
        """TC_WB_USR_007: Menguji fungsi rekapitulasi() untuk memastikan template yang benar dirender"""
        self.client.login(username='testing05', password='testing05')
        response = self.client.get(reverse('rekapitulasi'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/rekapitulasi.html')
        self.assertNotIn('brs_data', response.context) 

    def test_08_rekapitulasi_keseluruhan(self):
        """TC_WB_USR_008: Menguji fungsi rekapitulasi_keseluruhan() dengan data yang ada di database"""
        self.client.login(username='testing05', password='testing05')
        # Membuat data BRSExcel untuk pengujian
        BRSExcel.objects.create(judul_brs="Keseluruhan BRS 1", tgl_terbit=now(), id=self.user)
        BRSExcel.objects.create(judul_brs="Keseluruhan BRS 2", tgl_terbit=now(), id=self.user)
        response = self.client.get(reverse('rekapitulasi-keseluruhan'))  
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/rekapitulasi-keseluruhan.html')
        self.assertIn('brs_data', response.context)
        self.assertIn('years', response.context)
        self.assertEqual(len(response.context['brs_data']), 2)
        years = response.context['years']
        self.assertTrue(all(isinstance(year, int) for year in years))

    def test_09_rekapitulasi_pribadi_edit(self):
        """TC_WB_USR_009: Menguji fungsi rekapitulasi_pribadi() dengan aksi mengedit BRS"""
        self.client.login(username='testing05', password='testing05')
        # Membuat data BRSExcel untuk pengujian
        brs = BRSExcel.objects.create(judul_brs="Pertumbuhan Ekonomi 2025", tgl_terbit=now(), id=self.user)
        # Mengedit BRS
        response = self.client.post(reverse('rekapitulasi-pribadi'), {
            'edit_id': brs.id_brsexcel,
            'judul_brs': 'Pertumbuhan Ekonomi 2025 - Updated',
            'tgl_terbit': '2025-04-02'
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "success"})
        brs.refresh_from_db()
        self.assertEqual(brs.judul_brs, 'Pertumbuhan Ekonomi 2025 - Updated')

    def test_10_rekapitulasi_pribadi_delete(self):
        """TC_WB_USR_010: Menguji fungsi delete_brs() dengan aksi menghapus BRS"""
        self.client.login(username='testing05', password='testing05')
            # Membuat data BRSExcel untuk pengujian
        brs = BRSExcel.objects.create(judul_brs="Pertumbuhan Ekonomi 2025", tgl_terbit=now(), id=self.user)
        response = self.client.post(reverse('delete-brs', args=[brs.id_brsexcel]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('rekapitulasi-pribadi'))
        with self.assertRaises(BRSExcel.DoesNotExist):
            brs.refresh_from_db()

    def test_11_profile_user(self):
        """TC_WB_USR_011: Menguji fungsi profile_user() untuk menampilkan halaman profil user"""
        self.client.login(username='testing05', password='testing05')
        response = self.client.get(reverse('profile-user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/profile-user.html')

    def test_12_update_profile_usr(self):
        """TC_WB_USR_012: Menguji fungsi update_profile_usr() dengan data profile user"""
        self.client.login(username='testing05', password='testing05')
        response_post = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'Updated Name',
            'username': 'updated_username'
        })
        self.assertEqual(response_post.status_code, 302)  # Memastikan redirect setelah update

        # Memastikan data pengguna terupdate
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated Name')
        self.assertEqual(self.user.username, 'updated_username')

        # GET untuk memastikan halaman profil dirender dengan data yang benar
        response_get = self.client.get(reverse('update_profile_usr', args=[self.user.id]))
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'common/profile-user.html')
        self.assertIn('user', response_get.context)  # Memastikan user ada dalam konteks

    def test_13_change_password_usr_valid(self):
        """TC_WB_USR_013: Menguji fungsi change_password_usr() dengan data yang valid"""
        self.client.login(username='testing05', password='testing05')
        response = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'new_valid_password',
            'renewpassword': 'new_valid_password'
        })
        self.assertRedirects(response, reverse('profile-user'))  # Memastikan redirect ke profil

        # Memastikan password terupdate
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new_valid_password'))

    def test_14_change_password_usr_invalid(self):
        """TC_WB_USR_014: Menguji fungsi change_password_usr() dengan data yang tidak valid"""
        self.client.login(username='testing05', password='testing05')
        response = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'new_valid_password',
            'renewpassword': 'different_password'  # Password baru dan konfirmasi tidak sama
        })
        self.assertRedirects(response, reverse('profile-user'))  # Memastikan redirect ke profil

        # Memastikan password tetap sama
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testing05'))  # Password tidak berubah










   

