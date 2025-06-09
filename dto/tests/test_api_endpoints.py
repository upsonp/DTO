from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.gis.geos import Polygon, MultiPolygon
from dto.models import MPAZones, MPATranslations  # Fixed import path


class MPAAPITests(APITestCase):
    def setUp(self):
        # Create a simple polygon for testing
        polygon = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        )

        # Create test MPA
        self.mpa = MPAZones.objects.create(
            site_id='TEST01',
            area_km2=100.0,
            polygon=polygon
        )

        # Create English translation
        MPATranslations.objects.create(
            mpa=self.mpa,
            language='en',
            name='Test MPA',
            description='Test Description',
            lead_agency='Test Agency',
            url='http://test.com'
        )

    def test_list_mpas(self):
        url = reverse('dto:mpa-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['features']), 1)

        feature = response.data['features'][0]
        self.assertEqual(feature['properties']['site_id'], 'TEST01')
        self.assertEqual(feature['properties']['area_km2'], 100.0)

        translation = feature['properties']['translations'][0]
        self.assertEqual(translation['name'], 'Test MPA')
        self.assertEqual(translation['language'], 'en')