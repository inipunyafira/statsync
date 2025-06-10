from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.myuser.models import BRSExcel
from apps.myuser.views import extract_file_id
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.files.uploadedfile import SimpleUploadedFile
import os
import io

User  = get_user_model()

class UserViewsTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.client = Client()
        self.user = User.objects.create_user(username='testing05', password='testing05')
        self.client.login(username='testing05', password='testing05')

        # Create two BRSExcel entries for testing
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
        self.client.logout()  # Clear previous session
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
        """TC_WB_USR_001: Test extract_file_id() with valid Google Drive URL"""
        url = "https://drive.google.com/file/d/1A2B3C4D5E6F7/edit"
        file_id = extract_file_id(url)
        self.assertEqual(file_id, "1A2B3C4D5E6F7")
        url_with_id = "https://drive.google.com/?id=1A2B3C4D5E6F7"
        file_id_with_id = extract_file_id(url_with_id)
        self.assertEqual(file_id_with_id, "1A2B3C4D5E6F7")

    def test_06_rekapitulasi(self):
        self.client.login(username='testing05', password='testing05')
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
        self.client.login(username='testing05', password='testing05')
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

        # GET should render profile with user in context
        response_get = self.client.get(reverse('update_profile_usr', args=[self.user.id]))
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'common/profile-user.html')
        self.assertIn('user', response_get.context)

        # Test POST with XMLHttpRequest
        response_post_ajax = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST with duplicate username
        User.objects.create_user(username='testing051', password='testing05')
        response_post_ajax_duplicate_username = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing051'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_duplicate_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_duplicate_username.content, {'status': 'error', 'message': 'Username is already taken.'})

        # Test POST with same username
        response_post_ajax_same_username = self.client.post(reverse('update_profile_usr', args=[self.user.id]), {
            'fullName': 'testing05',
            'username': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_same_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_same_username.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST with empty username
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

        # Test POST with XMLHttpRequest
        response_post_ajax = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'testing05',
            'renewpassword': 'testing05'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'valid': False})

    def test_10_change_password_invalid(self):
        self.client.login(username='testing05', password='testing05')
        response = self.client.post(reverse('change-password_usr'), {
            'password': 'testing05',
            'newpassword': 'testing051',
            'renewpassword': 'testing052'
        })
        self.assertRedirects(response, reverse('profile-user'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testing05'))  # Password should not change

    def test_14_post_valid_brs(self):
        """Test valid BRS upload"""
        # Create a PDF file in memory
        pdf_file = io.BytesIO()
        p = canvas.Canvas(pdf_file, pagesize=letter)
        p.drawString(100, 750, "This is a test PDF file.")
        p.save()
        pdf_file.seek(0)  # Reset file pointer to the beginning

        response = self.client.post(reverse('brs-to-excel'), {
            'pdf_file': SimpleUploadedFile("brs.pdf", pdf_file.read(), content_type='application/pdf'),
            'tgl_terbit': '2025-06-02'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())
        self.assertTrue(BRSExcel.objects.filter(judul_brs='Expected Title').exists())  # Replace with actual expected title

    def test_15_post_duplicate_brs_title(self):
        """Test duplicate BRS title upload"""
        # Create a PDF file in memory
        pdf_file = io.BytesIO()
        p = canvas.Canvas(pdf_file, pagesize=letter)
        p.drawString(100, 750, "This is a test PDF file.")
        p.save()
        pdf_file.seek(0)  # Reset file pointer to the beginning

        # First upload
        self.client.post(reverse('brs-to-excel'), {
            'pdf_file': SimpleUploadedFile("brs.pdf", pdf_file.read(), content_type='application/pdf'),
            'tgl_terbit': '2025-06-02'
        })
        
        # Reset the file pointer again for the second upload
        pdf_file.seek(0)

        # Second upload with the same title
        response = self.client.post(reverse('brs-to-excel'), {
            'pdf_file': SimpleUploadedFile("brs.pdf", pdf_file.read(), content_type='application/pdf'),
            'tgl_terbit': '2025-06-02'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], "BRS with this title has already been uploaded.")


