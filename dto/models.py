from django.contrib.gis.db import models

class MPAZones(models.Model):
    site_id = models.CharField(max_length=50)
    area_km2 = models.FloatField()
    polygon = models.MultiPolygonField(srid=4326)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpa_zones'


class MPATranslations(models.Model):
    mpa = models.ForeignKey(MPAZones, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('fr', 'French')])
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    lead_agency = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'mpa_translations'
        unique_together = ('mpa', 'language')


class Timeseries(models.Model):
    TEMPERATURE = 'temperature'
    SALINITY = 'salinity'
    OXYGEN = 'oxygen'
    CHLOROPHYLL = 'chlorophyll'

    PARAMETER_CHOICES = [
        (TEMPERATURE, 'Temperature'),
        (SALINITY, 'Salinity'),
        (OXYGEN, 'Dissolved Oxygen'),
        (CHLOROPHYLL, 'Chlorophyll'),
    ]

    mpa = models.ForeignKey(MPAZones, on_delete=models.CASCADE, related_name='timeseries')
    timestamp = models.DateTimeField()
    value = models.FloatField()
    parameter = models.CharField(max_length=50, choices=PARAMETER_CHOICES)
    depth = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['mpa', 'timestamp', 'parameter']),
        ]
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.mpa.site_id} - {self.parameter} - {self.timestamp}"