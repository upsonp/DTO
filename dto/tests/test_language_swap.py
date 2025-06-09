# File: dto/tests/test_language_swaper.py
from django.test import TestCase
from django.urls import reverse

class LanguageSwapTests(TestCase):
    def test_language_swap(self):
        # Send a POST request to change the language to French
        response = self.client.post(reverse('set_language'), {
            'language': 'fr',
            'next': '/'
        }, follow=True)
        # Check if the response redirects to the next page
        self.assertRedirects(response, '/fr/')
        # Check if the language cookie is set to French
        self.assertEqual(self.client.cookies['django_language'].value, 'fr')

    def test_invalid_language(self):
        # Send a POST request with an invalid language code
        response = self.client.post(reverse('set_language'), {
            'language': 'invalid',
            'next': '/'
        }, follow=True)
        # Check if the response still redirects
        self.assertRedirects(response, '/en/')
        # Ensure the language cookie is not changed
        self.assertNotIn('invalid', self.client.cookies.get('django_language', ''))