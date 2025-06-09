import os
import requests
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from django.utils import timezone
from dto.models import Timeseries, MPAZones

import geopandas as gpd


def list_shp_fields():
    shapefile_path = 'scripts/data/MPAs/MPA_polygons.shp'
    gdf = gpd.read_file(shapefile_path)

    print("Fields in the shapefile:")
    for column in gdf.columns:
        print("-", column)


def download_glorys_data():
    # Create the directory structure if it doesn't exist
    save_dir = Path('scripts/data/GLORYS')
    save_dir.mkdir(parents=True, exist_ok=True)

    # GitHub API endpoint for the GLORYS directory
    repo_url = "https://api.github.com/repos/dfo-mar-odis/dto/contents/scripts/data/GLORYS"

    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        files = response.json()

        for file in files:
            if file['type'] == 'file':
                print(f"Downloading {file['name']}...")

                # Get the raw file content
                download_response = requests.get(file['download_url'])
                download_response.raise_for_status()

                # Save the file
                file_path = save_dir / file['name']
                with open(file_path, 'wb') as f:
                    f.write(download_response.content)

                print(f"Saved to {file_path}")

        print("Download complete!")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading files: {str(e)}")


def plot_mpa_temperature(mpa_id, save_path=None):
    """
    Plot temperature timeseries for a specific MPA using matplotlib.

    Args:
        mpa_id: ID of the MPA to plot
        save_path: Optional path to save the plot
    """
    # Get MPA name
    mpa = MPAZones.objects.get(site_id=mpa_id)
    mpa_name = mpa.translations.get(language='en').name

    # Get temperature data
    timeseries = mpa.timeseries.filter(parameter='temperature', depth=None).order_by('timestamp').values('timestamp', 'value')

    # Convert to DataFrame
    df = pd.DataFrame(timeseries)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    # Calculate climatology (1993-2022)
    mask = (df['timestamp'].dt.year >= 1993) & (df['timestamp'].dt.year <= 2022)
    df_clim = df[mask].copy()
    df_clim['day_of_year'] = df_clim['timestamp'].dt.dayofyear
    climatology = df_clim.groupby('day_of_year')['value'].mean()

    # Get recent data (last 2 years)
    two_years_ago = timezone.now() - timedelta(days=730)
    recent_data = df[df['timestamp'] >= two_years_ago]

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Plot climatology
    days = climatology.index
    plt.plot(days, climatology.values, '--', color='#FF9800',
             label='Climatology (1993-2022)', alpha=0.8)

    # Plot recent data
    plt.plot(recent_data['timestamp'].dt.dayofyear, recent_data['value'],
             color='#2196F3', label='Recent Data')

    plt.title(f'Temperature Timeseries - {mpa_name}')
    plt.xlabel('Day of Year')
    plt.ylabel('Temperature (°C)')
    plt.grid(True, alpha=0.3)
    plt.legend()

    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

    plt.close()