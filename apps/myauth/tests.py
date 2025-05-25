from django.test import TestCase, Client
from django.urls import reverse
from .models import CustomUser , Role

class AuthViewsWhiteboxTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create roles
        self.role_user = Role.objects.create(nama_role='User ')
        self.role_admin = Role.objects.create(nama_role='Admin')

    def test_001_user_register_valid(self):
        # Register a valid user
        response = self.client.post(reverse('register'), {
            'name': 'Testing',
            'username': 'testing05',
            'password': 'testing05',
            'confirmPassword': 'testing05'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(CustomUser .objects.filter(username='testing05').exists())
        # The redirect should be to 'login' page
        self.assertRedirects(response, reverse('login'))
        # Attempt to register the same username again
        response_duplicate = self.client.post(reverse('register'), {
            'name': 'DuplicateUser ',
            'username': 'testing05',  # Same username
            'password': 'newpassword',
            'confirmPassword': 'newpassword'
        })
        self.assertEqual(response_duplicate.status_code, 200)  # Should render the registration page again
        self.assertFalse(CustomUser .objects.filter(username='testing05').count() > 1)  # Ensure no duplicate user
        self.assertContains(response_duplicate, "Username is already taken!")  # Check for error message

    def test_002_user_register_invalid_password(self):
        # Password and confirmPassword do not match, should not create user
        response = self.client.post(reverse('register'), {
            'name': 'Test',
            'username': 'testuser',
            'password': 'password123',
            'confirmPassword': 'different123'
        })
        self.assertEqual(response.status_code, 200)  # Render register page again without redirect
        self.assertFalse(CustomUser .objects.filter(username='testuser').exists())

    def test_003_user_login_valid(self):
        # Create admin user
        admin = CustomUser.objects.create_user(username='adminuser', password='adminpass')
        admin.first_name = 'AdminUser'
        admin.id_role = self.role_admin
        admin.save()

        # Create regular user
        user = CustomUser.objects.create_user(username='normaluser', password='userpass')
        user.first_name = 'NormalUser'
        user.id_role = self.role_user
        user.save()

        # Test admin login
        response_admin = self.client.post(reverse('login'), {
            'username': 'adminuser',
            'password': 'adminpass'
        })
        self.assertEqual(response_admin.status_code, 302)
        self.assertRedirects(response_admin, reverse('dashboard-admin'))

        # Test regular user login
        response_user = self.client.post(reverse('login'), {
            'username': 'normaluser',
            'password': 'userpass'
        })
        self.assertEqual(response_user.status_code, 302)
        self.assertRedirects(response_user, reverse('dashboard-user'))

    def test_004_user_login_invalid(self):
        # Login attempt with invalid password
        user = CustomUser .objects.create_user(username='normaluser', password='userpass')
        response = self.client.post(reverse('login'), {
            'username': 'normaluser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 302)  # Redirect back to login on failure
        self.assertRedirects(response, reverse('login'))

    def test_005_dashboard_admin_access(self):
        admin = CustomUser.objects.create_user(username='adminuser', password='adminpass')
        admin.id_role = self.role_admin
        admin.save()
        self.client.login(username='adminuser', password='adminpass')
        response = self.client.get(reverse('dashboard-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dashboard-admin.html')

    def test_006_dashboard_user_access(self):
        user = CustomUser .objects.create_user(username='normaluser', password='userpass')
        user.id_role = self.role_user
        user.save()
        self.client.login(username='normaluser', password='userpass')
        response = self.client.get(reverse('dashboard-user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/dashboard-user.html')

    def test_007_user_logout(self):
        user = CustomUser .objects.create_user(username='logoutuser', password='logoutpass')
        user.id_role = self.role_user
        user.save()
        self.client.login(username='logoutuser', password='logoutpass')

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

        # After logout the user should not be authenticated
        response_after = self.client.get(reverse('dashboard-user'))
        self.assertEqual(response_after.status_code, 302)  # Redirect to login since logged out
