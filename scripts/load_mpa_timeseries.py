import os
import re
import math
import pytz
import pandas as pd
import numpy as np

from django.utils import timezone
from pathlib import Path
from dto import models
from tqdm import tqdm

import logging

logger = logging.getLogger('dto')


def load_series(mpa_name, timeseries, depth=None, parameter=models.Timeseries.TEMPERATURE):
    total_rows = len(timeseries)
    optimal_batch_size = 5000  # Keep this as a memory safeguard

    progress_bar = tqdm(
        total=total_rows,
        desc=f"Loading {parameter} data for {mpa_name.translations.get(language='en').name}" + (
            f" at depth {depth}m" if depth else ""),
        unit=' records'
    )

    # Process in memory-efficient chunks
    for start_idx in range(0, total_rows, optimal_batch_size):
        end_idx = min(start_idx + optimal_batch_size, total_rows)
        chunk = timeseries.iloc[start_idx:end_idx]

        # Create batch for current chunk
        batch = [
            models.Timeseries(
                mpa=mpa_name,
                timestamp=timestamp,
                value=float(series.iloc[0] if len(series) == 1 else series.values[0]) if pd.notna(
                    series.iloc[0]) else np.nan,
                depth=depth,
                parameter=parameter
            )
            for timestamp, series in chunk.iterrows()
        ]

        models.Timeseries.objects.bulk_create(batch)
        progress_bar.update(len(batch))

    progress_bar.close()


def read_timeseries(mpa_name, filename, date_col='Date'):
    # Use efficient CSV reading options
    timeseries = pd.read_csv(
        filename,
        parse_dates=[date_col],
        index_col=date_col,
        dtype={'value': np.float32}  # Reduce memory usage
    )
    # Localize the datetime index to UTC, I assume that's what the GLORYS model uses.
    timeseries.index = timeseries.index.tz_localize('UTC')

    load_series(mpa_name, timeseries)


def read_depth_timeseries(mpa_name, filename, date_col='Date'):
    timeseries = pd.read_csv(
        filename,
        parse_dates=[date_col],
    )

    # Localize the datetime column to UTC
    timeseries[date_col] = pd.to_datetime(timeseries[date_col]).dt.tz_localize('UTC')

    timeseries = timeseries.set_index(date_col)

    for col in timeseries.columns:
        depth_timeseries = timeseries[[col]]

        depth = int(col.split(' ')[0])
        load_series(mpa_name, depth_timeseries, depth)


def load_mpas_from_dict(data: dict):
    from django.db import transaction

    for k, mpa_dict in data.items():
        try:
            with transaction.atomic():
                mpa = models.MPAZones.objects.get(site_id=k)
                mpa.timeseries.all().delete()

                bottom_ts = mpa_dict.get('BOTTOM_TS')
                depth_ts = mpa_dict.get('DEPTH_TS')

                if bottom_ts:
                    read_timeseries(mpa, bottom_ts)
                if depth_ts:
                    read_depth_timeseries(mpa, depth_ts)

        except Exception as e:
            logger.error(f"Failed to process MPA {k}: {str(e)}")
            continue


def build_mpa_dictionary() -> dict:
    data = {}
    data_directory = Path('./scripts/data/GLORYS/')
    id_regex = re.compile(r'.*?_(\d*)_.*?.csv')

    # Use Path for better file handling
    for f in data_directory.glob('*bottomT_*.csv'):
        if not (mpa_id := id_regex.match(f.name)):
            continue

        mpa_id = int(mpa_id.group(1))
        data.setdefault(mpa_id, {})

        if f.name.startswith('depth_'):
            data[mpa_id]['DEPTH_TS'] = str(f)
        else:
            data[mpa_id]['BOTTOM_TS'] = str(f)

    return data


def load_dictionary_mpas():
    mpas = build_mpa_dictionary()
    load_mpas_from_dict(mpas)


def load_mpa_timeseries():
    # this is how we'll actually load data when we have real data to load
    # for now, every MPA is getting loaded with the St. Anne's bank data
    data = build_mpa_dictionary()
    load_mpas_from_dict(data)
