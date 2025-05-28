from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.myuser.models import BRSExcel
from apps.myuser.views import extract_file_id
from django.utils.timezone import now
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.files.uploadedfile import SimpleUploadedFile
import os

User  = get_user_model()

class UserViewsTestCase(TestCase):
    def setUp(self):
        # Membuat user test
        self.client = Client()
        self.user = User.objects.create_user(username='testing05', password='testing05')
        self.client.login(username='testing05', password='testing05')

                # Membuat dua data BRSExcel minimal sesuai model untuk test
        # Menggunakan field 'id' sebagai foreign key user sesuai view (filter id=request.user)
        # Field tgl_terbit wajib diisi
        # Jika perlu sesuaikan nama atribut foreign key user
        self.brs1 = BRSExcel.objects.create(id=self.user, tgl_terbit="2025-04-02")
        self.brs2 = BRSExcel.objects.create(id=self.user, tgl_terbit="2024-04-02")

    def test_01_custom_login_valid(self):
        response = self.client.post(reverse('custom_login_user'), {
            'username': 'testing05',
            'password': 'testing05'
        })
        self.assertRedirects(response, reverse('dashboard-user'))
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, 'testing05')

    def test_02_custom_login_invalid(self):
        self.client.logout()  # Menghapus sesi yang sebelumnya
        response = self.client.post(reverse('custom_login_user'), {
            'username': 'testing05',
            'password': 'testing123'
        }, follow=True)
        self.assertRedirects(response, reverse('login'))
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)
        messages = list(response.context.get('messages'))
        self.assertTrue(any("Incorrect username or password" in str(m) for m in messages))

    def test_03_dashboard_user(self):
        self.client.login(username='testing05', password='testing05')
        BRSExcel.objects.create(id=self.user, tgl_up=now(), tgl_terbit=now())
        BRSExcel.objects.create(id=self.user, tgl_up=now(), tgl_terbit=now())
        response = self.client.get(reverse('dashboard-user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/dashboard-user.html')
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
        url_with_id = "https://drive.google.com/?id=1A2B3C4D5E6F7"
        file_id_with_id = extract_file_id(url_with_id)
        self.assertEqual(file_id_with_id, "1A2B3C4D5E6F7")
    
    def test_06_rekapitulasi(self):
        self.client.login(username='testing05', password='tetsing05')
        response = self.client.get(reverse('rekapitulasi'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/rekapitulasi.html')

    def test_11_rekapitulasi_keseluruhan(self):
        response = self.client.get(reverse('rekapitulasi-keseluruhan'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/rekapitulasi-keseluruhan.html')
        self.assertIn('brs_data', response.context)
        self.assertIn('years', response.context)
        self.assertEqual(len(response.context['brs_data']), 2)
        
    def test_12_rekapitulasi_pribadi_edit(self):
        post_data = {
            'edit_id': self.brs1.id_brsexcel if hasattr(self.brs1, 'id_brsexcel') else self.brs1.id,
            'fieldname1': 'value1', 
            'fieldname2': 'value2', 
        }
        response = self.client.post(reverse('rekapitulasi-pribadi'), post_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

    def test_13_rekapitulasi_pribadi_delete(self):
        response = self.client.post(
            reverse('delete-brs', args=[self.brs2.id_brsexcel if hasattr(self.brs2, 'id_brsexcel') else self.brs2.id]),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        redirect_urls = [redirect[0] for redirect in response.redirect_chain]
        self.assertIn(reverse('rekapitulasi-pribadi'), redirect_urls)
        with self.assertRaises(BRSExcel.DoesNotExist):
            self.brs2.refresh_from_db()

    def test_07_profile_user(self):
        self.client.login(username='testing05', password='tetsing05')
        response = self.client.get(reverse('profile-user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/profile-user.html')

    def test_08_update_profile_usr(self):
        self.client.login(username='testing05', password='testing05')

        # POST update profile
        response_post = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing05'
        })
        self.assertEqual(response_post.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'testing05')
        self.assertEqual(self.user.username, 'testing05')

        # Missing coverage: GET should render profile with user in context
        response_get = self.client.get(reverse('update_profile_usr', args=[self.user.id]))
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'common/profile-user.html')
        self.assertIn('user', response_get.context)

        # Test POST dengan XMLHttpRequest
        response_post_ajax = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST dengan XMLHttpRequest dan username yang sudah digunakan
        User.objects.create_user(username='testing051', password='testing05')
        response_post_ajax_duplicate_username = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing051'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_duplicate_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_duplicate_username.content, {'status': 'error', 'message': 'Username is already taken.'})

        # Test POST dengan XMLHttpRequest dan username yang sama dengan yang sudah ada
        response_post_ajax_same_username = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_same_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_same_username.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST dengan XMLHttpRequest dan username yang kosong
        response_post_ajax_empty_username = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': ''
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_empty_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_empty_username.content, {'status': 'success', 'message': 'Profile updated successfully.'})

    def test_09_change_password_valid(self):
        self.client.login(username='testing05', password='testing05')
        response = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'testing051',
            'renewpassword': 'testing051'
        })
        self.assertRedirects(response, reverse('profile-user'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testing051'))

        # Test POST dengan XMLHttpRequest
        response_post_ajax = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'testing05',
            'renewpassword': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'valid': False})  # Ubah menjadi {'valid': False}

    def test_10_change_password_invalid(self):
        self.client.login(username='testing05', password='testing05')
        response = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'testing051',
            'renewpassword': 'testing052'
        })
        self.assertRedirects(response, reverse('profile-user'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testing05'))  # Password tidak berubah

    def test_upload_valid_pdf_file(self):
        """Test uploading a valid PDF file by the user."""
        
        # Prepare the valid PDF file for upload
        pdf_file_path = r'C:\Data\Kuliah\Projek_SAD\statsync\htmlcov\25_01.pdf'
        
        # Ensure the file exists before running the test
        self.assertTrue(os.path.exists(pdf_file_path), "The test PDF file does not exist.")
        
        with open(pdf_file_path, 'rb') as pdf:
            response = self.client.post(reverse('brstoexcel'), {
                'pdf_file': pdf,
                'tgl_terbit': '2025-05-01'  # Publication Date
            })
        
        # Check the response status
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains success message
        self.assertContains(response, "The file has been successfully extracted!")
        
        # Log the response content for debugging
        print(response.content)  # You can also use logging

        # Check for the actual title extracted from the PDF
        # Replace this with the actual expected title based on your PDF content
        extracted_title = "Expected Title from PDF"  # Update this to the actual expected title
        
        # Check if the BRSExcel entry was created
        if not BRSExcel.objects.filter(judul_brs=extracted_title).exists():
            # Log all BRSExcel entries for debugging
            all_entries = BRSExcel.objects.all()
            for entry in all_entries:
                print(f"Entry: {entry.judul_brs}, ID: {entry.id}, User: {entry.id_user}, Date: {entry.tgl_terbit}")

        self.assertTrue(BRSExcel.objects.filter(judul_brs=extracted_title).exists(), 
                        f"BRSExcel entry with title '{extracted_title}' does not exist.")

        # Optionally, check the details of the created BRSExcel entry
        brs_entry = BRSExcel.objects.get(judul_brs=extracted_title)
        self.assertEqual(brs_entry.tgl_terbit, '2025-05-01')
        self.assertEqual(brs_entry.id, self.user)  # Assuming 'id' is the foreign key to the user

        # Check if the uploaded file exists in the expected location
        file_path = os.path.join("static/uploads", brs_entry.id_file)  # Adjust based on your model
        self.assertTrue(os.path.exists(file_path))

        # Clean up: Remove the uploaded file if necessary
        if os.path.exists(file_path):
            os.remove(file_path)









   

