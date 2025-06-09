import logging
import pandas as pd

from datetime import datetime, timedelta

from django.db import models
from django.db.models import Avg, Q
from django.db.models.functions import Extract

from rest_framework import viewsets
from .models import MPAZones, Timeseries
from .serializers import MPAZoneSerializer

from django.http import JsonResponse

logger = logging.getLogger("dto")


class MPAViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MPAZones.objects.all().prefetch_related('translations')
    serializer_class = MPAZoneSerializer


def mpa_zones_geojson(request):
    current_language = request.LANGUAGE_CODE

    # First get distinct MPA IDs that have timeseries data
    # This is more efficient than filtering with timeseries__isnull=False
    timeseries_ids = Timeseries.objects.values_list('mpa', flat=True).distinct()

    zones = MPAZones.objects.filter(
        translations__language=current_language,
        id__in=timeseries_ids
    ).prefetch_related('translations').distinct()

    serializer = MPAZoneSerializer(
        zones,
        many=True,
        context={'request': request}
    )

    return JsonResponse(serializer.data, safe=False)


def get_latest_timeseries_date(request):
    try:
        latest_date = Timeseries.objects.filter(
            parameter='temperature'  # Since we're only using temperature for now
        ).latest('timestamp').timestamp

        # Calculate start date (10 years before)
        start_date = latest_date - timedelta(days=365 * 10)

        return JsonResponse({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': latest_date.strftime('%Y-%m-%d')
        })
    except Timeseries.DoesNotExist:
        # Fallback to current date if no data exists
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 10)
        return JsonResponse({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })


def get_mpa_timeseries(request, mpa_id, parameter, depth=None):
    # Validate parameter choice
    if parameter not in dict(Timeseries.PARAMETER_CHOICES):
        return JsonResponse({'error': 'Invalid parameter'}, status=400)

    # Get date range from request parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base query
    query = Q(mpa_id=mpa_id, parameter=parameter, depth=depth)

    if not start_date or not end_date:
        date_range = Timeseries.objects.filter(query).aggregate(
            min_date=models.Min('timestamp'),
            max_date=models.Max('timestamp')
        )
        start_date = start_date or date_range['min_date'].strftime('%Y-%m-%d')
        end_date = end_date or date_range['max_date'].strftime('%Y-%m-%d')

    # Get filtered timeseries data
    timeseries = Timeseries.objects.filter(query).order_by('timestamp').values('timestamp', 'value')

    # Convert to pandas DataFrame
    df = pd.DataFrame(timeseries)

    # Filter for climatology calculation (1993-2022)
    climatology_mask = (df['timestamp'] >= '1993-01-01') & (df['timestamp'] <= '2022-12-31')
    df_climatology = df[climatology_mask].copy()
    df_climatology['day_of_year'] = df_climatology['timestamp'].dt.dayofyear

    # Calculate daily climatology using pandas
    climatology = df_climatology.groupby('day_of_year')['value'].agg([  # Changed from df to df_climatology
        ('avg_value', 'mean'),
        ('p10', lambda x: x.quantile(0.1)),
        ('p90', lambda x: x.quantile(0.9))
    ]).reset_index()

    # Calculate differences between timeseries and climatology for all data
    df_all = df.copy()  # Use all data, not just filtered range
    df_all['day_of_year'] = df_all['timestamp'].dt.dayofyear

    # Merge climatology with full timeseries
    df_differences = pd.merge(df_all, climatology, on='day_of_year', how='left')
    df_differences['difference'] = df_differences['value'] - df_differences['avg_value']

    # Get min and max differences
    min_difference = df_differences['difference'].min()
    max_difference = df_differences['difference'].max()

    # Before the DataFrame filtering, convert timezone-naive dates to timezone-aware
    start_date = pd.to_datetime(start_date).tz_localize('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC')

    # Filter the DataFrame for the specified date range
    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

    response_data = {
        'parameter': parameter,
        'timeseries': df.to_dict('records'),
        'climatology': climatology.to_dict('records'),
        'stats': {
            'min_difference': float(min_difference),
            'max_difference': float(max_difference)
        }
    }

    return JsonResponse(response_data)


def get_available_parameters(request, mpa_id):
    # Convert parameter choices directly to the desired format
    available_parameters = [
        {'value': value, 'label': label}
        for value, label in Timeseries.PARAMETER_CHOICES
        if value == 'temperature'
    ]

    return JsonResponse({'parameters': available_parameters})