from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('operator', password='test-password')

    def test_login_redirects_to_requested_page(self):
        destination = reverse('settings')
        response = self.client.post(reverse('login'), {
            'username': 'operator', 'password': 'test-password', 'next': destination,
        })
        self.assertEqual('ok', response.json()['result'])
        self.assertEqual(destination, response.json()['redirect_to'])
        self.assertEqual(str(self.user.pk), self.client.session['_auth_user_id'])

    def test_remember_me_controls_session_expiry(self):
        for remember, closes_with_browser in [('0', True), ('1', False)]:
            self.client.logout()
            response = self.client.post(reverse('login'), {
                'username': 'operator', 'password': 'test-password', 'remember': remember,
            })
            self.assertEqual('ok', response.json()['result'])
            self.assertEqual(closes_with_browser, self.client.session.get_expire_at_browser_close())
            if remember == '1':
                self.assertEqual(settings.SESSION_COOKIE_AGE, self.client.session.get_expiry_age())

    def test_invalid_credentials_do_not_create_authenticated_session(self):
        response = self.client.post(reverse('login'), {
            'username': 'operator', 'password': 'wrong', 'remember': '1',
        })
        self.assertNotEqual('ok', response.json()['result'])
        self.assertNotIn('_auth_user_id', self.client.session)
