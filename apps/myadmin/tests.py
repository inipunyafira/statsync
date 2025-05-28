from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.myauth.models import Role
from apps.myuser.models import BRSExcel
from django.utils.timezone import now

User  = get_user_model()

class AdminViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.role_admin = Role.objects.create(id_role=1, nama_role='Admin')
        self.admin_user = User.objects.create_user(username='myadmin', password='myadmin1')
        self.admin_user.id_role = self.role_admin
        self.admin_user.save()

    def test_01_custom_login_valid(self):
        response = self.client.post(reverse('custom_login'), {
            'username': 'myadmin',
            'password': 'myadmin1'
        })
        self.assertRedirects(response, reverse('dashboard-admin'))
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, 'myadmin')

    def test_02_custom_login_invalid(self):
        response = self.client.post(reverse('custom_login'), {
            'username': 'myadmin',
            'password': 'myadmin123'
        }, follow=True)
        self.assertRedirects(response, reverse('login'))
        messages = list(response.context.get('messages'))
        self.assertTrue(any("Incorrect username or password" in str(m) for m in messages))
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

    def test_03_dashboard_admin(self):
        self.client.login(username='myadmin', password='myadmin1')
        BRSExcel.objects.create(id=self.admin_user, tgl_up=now(), tgl_terbit=now())
        BRSExcel.objects.create(id=self.admin_user, tgl_up=now(), tgl_terbit=now())
        response = self.client.get(reverse('dashboard-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dashboard-admin.html')
        self.assertIn('total_users', response.context)
        self.assertIn('user_brs_count', response.context)
        self.assertIn('total_brs_uploaded', response.context)
        self.assertIn('usernames', response.context)
        self.assertIn('upload_counts', response.context)

    def test_04_manage_users(self):
        """TC_WB_ADM_001: Test manage_users() after login."""
        self.client.login(username='myadmin', password='myadmin1')
        response = self.client.get(reverse('manage-users'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/manage-users.html')
        self.assertIn('users', response.context)
        self.assertIn('roles', response.context)

    def test_05_change_user_role_valid(self):
        self.client.login(username='myadmin', password='myadmin1')

        # Valid POST change role
        user = User.objects.create_user(username='testing05', password='testing05')
        role_new = Role.objects.create(id_role=2, nama_role='User ')
        response_post = self.client.post(reverse('change_user_role'), {'user_id': user.id, 'role_id': role_new.id_role})
        self.assertEqual(response_post.status_code, 200)
        self.assertJSONEqual(response_post.content, {"success": True, "new_role": role_new.nama_role})
        user.refresh_from_db()
        self.assertEqual(user.id_role, role_new)

        # Missing coverage: call with GET should return error json
        response_get = self.client.get(reverse('change_user_role'))
        self.assertEqual(response_get.status_code, 200)
        self.assertJSONEqual(response_get.content, {"success": False, "error": "Invalid request"})

        # Test POST without parameters
        response_post_missing_params = self.client.post(reverse('change_user_role'), {})
        self.assertEqual(response_post_missing_params.status_code, 200)
        self.assertJSONEqual(response_post_missing_params.content, {"success": False, "error": "Missing parameters"})

    def test_06_log_activity(self):
        self.client.login(username='myadmin', password='myadmin1')
        BRSExcel.objects.create(id=self.admin_user, tgl_up=now(), tgl_terbit=now())
        response = self.client.get(reverse('log-activity'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/log-activity.html')
        self.assertIn('log_data', response.context)
        self.assertIn(self.admin_user.username, response.context['log_data'])

    def test_07_profile_admin(self):
        self.client.login(username='myadmin', password='myadmin1')
        response = self.client.get(reverse('profile-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/profile-admin.html')

    def test_08_update_profile_adm(self):
        self.client.login(username='myadmin', password='myadmin1')

        # POST update profile
        response_post = self.client.post(reverse('update_profile_adm', args=[self.admin_user.id]), {
            'fullName': 'myadmin',
            'username': 'myadmin1'
        })
        self.assertEqual(response_post.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.first_name, 'myadmin')
        self.assertEqual(self.admin_user.username, 'myadmin1')

        # Missing coverage: GET should render profile with user in context
        response_get = self.client.get(reverse('update_profile_adm', args=[self.admin_user.id]))
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'common/profile-admin.html')
        self.assertIn('user', response_get.context)

        # Test POST dengan XMLHttpRequest
        response_post_ajax = self.client.post(reverse('update_profile_adm', args=[self.admin_user.id]), {
            'fullName': 'myadmin',
            'username': 'myadmin1'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST dengan XMLHttpRequest dan username yang sudah digunakan
        User.objects.create_user(username='myadmin2', password='testpass')
        response_post_ajax_duplicate_username = self.client.post(reverse('update_profile_adm', args=[self.admin_user.id]), {
            'fullName': 'myadmin',
            'username': 'myadmin2'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_duplicate_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_duplicate_username.content, {'status': 'error', 'message': 'Username is already taken.'})

        # Test POST dengan XMLHttpRequest dan username yang sama dengan yang sudah ada
        response_post_ajax_same_username = self.client.post(reverse('update_profile_adm', args=[self.admin_user.id]), {
            'fullName': 'myadmin',
            'username': 'myadmin'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_same_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_same_username.content, {'status': 'success', 'message': 'Profile updated successfully.'})

        # Test POST dengan XMLHttpRequest dan username yang kosong
        response_post_ajax_empty_username = self.client.post(reverse('update_profile_adm', args=[self.admin_user.id]), {
            'fullName': 'myadmin',
            'username': ''
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax_empty_username.status_code, 200)
        self.assertJSONEqual(response_post_ajax_empty_username.content, {'status': 'success', 'message': 'Profile updated successfully.'})

    def test_09_change_password_valid(self):
        self.client.login(username='myadmin', password='myadmin1')
        response = self.client.post(reverse('change-password_adm'), {
            'password': 'myadmin1',
            'newpassword': 'myadmin123',
            'renewpassword': 'myadmin123'
        })
        self.assertRedirects(response, reverse('profile-admin'))
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('myadmin123'))

        # Test POST dengan XMLHttpRequest
        response_post_ajax = self.client.post(reverse('change-password_adm'), {
            'password': 'myadmin1',
            'newpassword': 'myadmin123',
            'renewpassword': 'myadmin123'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_post_ajax.status_code, 200)
        self.assertJSONEqual(response_post_ajax.content, {'valid': False})  # Ubah menjadi {'valid': False}

    def test_10_change_password_invalid(self):
        self.client.login(username='myadmin', password='myadmin1')
        response = self.client.post(reverse('change-password_adm'), {
            'password': 'myadmin1',
            'newpassword': 'admin1',
            'renewpassword': 'admin12'
        })
        self.assertRedirects(response, reverse('profile-admin'))
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('myadmin1'))