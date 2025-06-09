from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import MPAZones, MPATranslations


class MPATranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MPATranslations
        fields = ['language', 'name', 'description', 'lead_agency', 'url']


class MPAZoneSerializer(GeoFeatureModelSerializer):
    mpa_name = serializers.SerializerMethodField()

    def get_mpa_name(self, obj):
        # Get translation in current language
        translation = obj.translations.filter(
            language=self.context['request'].LANGUAGE_CODE
        ).first()
        return translation.name if translation else ''

    class Meta:
        model = MPAZones
        geo_field = 'polygon'  # Use simplified geometry
        fields = ['id', 'site_id', 'area_km2', 'mpa_name']