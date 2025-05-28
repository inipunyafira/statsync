from django.test import TestCase, Client
from django.urls import reverse
from .models import CustomUser, Role
from django.contrib.messages import get_messages

class AuthViewsWhiteboxTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Membuat role
        self.role_user = Role.objects.create(nama_role='User')
        self.role_admin = Role.objects.create(nama_role='Admin')

        # Membuat user untuk tes username duplikat
        self.existing_user = CustomUser.objects.create_user(
            username='existinguser', password='password123'
        )
        self.existing_user.id_role = self.role_user
        self.existing_user.save()

    def test_001_user_register_valid(self):
        # Daftar user valid
        response = self.client.post(reverse('register'), {
            'name': 'Testing',
            'username': 'testing05',
            'password': 'testing05',
            'confirmPassword': 'testing05'
        })
        self.assertEqual(response.status_code, 302)  # Redirect setelah berhasil
        user = CustomUser.objects.get(username='testing05')
        self.assertEqual(str(user), 'testing05')  # Cek __str__ CustomUser
        self.assertEqual(user.id_role.nama_role, 'User')  # Cek link role
        self.assertTrue(CustomUser.objects.filter(username='testing05').exists())
        self.assertRedirects(response, reverse('login'))

        # Cek __str__ Role
        self.assertEqual(str(self.role_user), 'User')

    def test_002_user_register_invalid_password(self):
        # Password dan confirmPassword beda, user tidak dibuat
        response = self.client.post(reverse('register'), {
            'name': 'Test',
            'username': 'testuser',
            'password': 'password123',
            'confirmPassword': 'different123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect ke register
        self.assertRedirects(response, reverse('register'))
        self.assertFalse(CustomUser.objects.filter(username='testuser').exists())

    def test_sdsdads_(self):
        # Password terlalu pendek
        response_short_password = self.client.post(reverse('register'), {
            'name': 'ShortPasswordUser',
            'username': 'shortpassworduser',
            'password': 'short',
            'confirmPassword': 'short'
        })
        self.assertEqual(response_short_password.status_code, 302)  # Redirect ke register
        self.assertRedirects(response_short_password, reverse('register'))
        self.assertFalse(CustomUser.objects.filter(username='shortpassworduser').exists())

        # Ambil pesan error setelah redirect
        messages = list(get_messages(response_short_password.wsgi_request))
        error_messages = [m.message for m in messages if m.level_tag == 'error']

        # Pastikan ada pesan error password kurang kuat
        self.assertIn('Password must be at least 8 characters long and include both letters and numbers.', error_messages)

    def test_003_user_register_username_taken(self):
        # Daftar dengan username sudah ada via AJAX
        response = self.client.post(
            reverse('register'),
            {
                'name': 'User2',
                'username': 'existinguser',
                'password': 'newpassword123',
                'confirmPassword': 'newpassword123'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)  # Respon JSON AJAX
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Username is already taken.', data['message'])

        # Pastikan tidak ada user duplikat
        self.assertEqual(CustomUser.objects.filter(username='existinguser').count(), 1)

    def test_004_user_login_valid(self):
        # Buat user admin
        admin = CustomUser.objects.create_user(username='adminuser', password='adminpass')
        admin.first_name = 'AdminUser'
        admin.id_role = self.role_admin
        admin.save()

        # Buat user biasa
        user = CustomUser.objects.create_user(username='normaluser', password='userpass')
        user.first_name = 'NormalUser'
        user.id_role = self.role_user
        user.save()

        # Login admin berhasil
        response_admin = self.client.post(reverse('login'), {
            'username': 'adminuser',
            'password': 'adminpass'
        })
        self.assertEqual(response_admin.status_code, 302)
        self.assertRedirects(response_admin, reverse('dashboard-admin'))

        # Login user biasa berhasil
        response_user = self.client.post(reverse('login'), {
            'username': 'normaluser',
            'password': 'userpass'
        })
        self.assertEqual(response_user.status_code, 302)
        self.assertRedirects(response_user, reverse('dashboard-user'))

    def test_005_user_login_invalid(self):
        # Login dengan password salah
        user = CustomUser.objects.create_user(username='normaluser', password='userpass')

        # Login biasa gagal, redirect ke login
        response = self.client.post(reverse('login'), {
            'username': 'normaluser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

        # Login AJAX gagal
        response_ajax = self.client.post(
            reverse('login'),
            {
                'username': 'normaluser',
                'password': 'wrongpassword'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response_ajax.status_code, 200)
        self.assertEqual(response_ajax['Content-Type'], 'application/json')
        data = response_ajax.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Incorrect username or password!')

    def test_008_user_logout(self):
        user = CustomUser.objects.create_user(username='logoutuser', password='logoutpass')
        user.id_role = self.role_user
        user.save()
        self.client.login(username='logoutuser', password='logoutpass')

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

        # Setelah logout, user tidak terautentikasi
        response_after = self.client.get(reverse('dashboard-user'))
        self.assertEqual(response_after.status_code, 302)  # Redirect ke login karena logout

