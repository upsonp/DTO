from load_mpa_polygons import load_mpas
from load_mpa_timeseries import load_mpa_timeseries

def setup():
    load_mpas()
    load_mpa_timeseries()