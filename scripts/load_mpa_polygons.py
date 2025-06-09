import geopandas as gpd

from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import MultiPolygon, GEOSGeometry

from dto import models

# Auto-generated `LayerMapping` dictionary for mpa model
mpa_mapping = {
    'name_e': 'SitNm_E',
    'name_f': 'NmDSt_F',
    'url_e': 'URL_E',
    'url_f': 'URL_F',
    'km2': 'Km2',
    'geom': 'MULTIPOLYGON',
}

mpa_shape = r'scripts/data/MPAs/MPA_polygons.shp'


def merge_zones():
    for mpa in models.MPAName.objects.all():
        geom = None
        map_zone_union = models.MPAZone.objects.filter(name=mpa).aggregate(area=Union('geom'))
        try:
            geom = MultiPolygon(GEOSGeometry(map_zone_union['area']))
            # print(f"Map area: {map_zone_union['area']}")
        except TypeError as e:
            for zone in mpa.zones.all():
                if geom:
                    geom += zone.geom
                else:
                    geom = zone.geom

        zone_names_e = ", ".join([zone.zone_e for zone in mpa.zones.all()])
        zone_names_f = ", ".join([zone.zone_f for zone in mpa.zones.all()])
        meta = mpa.zones.first()
        area = geom.area
        try:
            print(f"{mpa.name_e.encode('utf-8')} - {area / 1000000}")
        except UnicodeEncodeError as ex:
            print(f"Could not decode mpa name - {area / 1000000}")

        merged_zone = models.MPAZone(name=mpa, zone_e=f'Union: {zone_names_e}', zone_f=f'Union: {zone_names_f}',
                                     url_e=meta.url_e, url_f=meta.url_e, regulation=meta.regulation,
                                     reglement=meta.reglement, km2=(area / 1000000), geom=geom, )
        merged_zone.save()
        print(merged_zone.zone_e)


def load_mpas():
    data = gpd.read_file(mpa_shape, encoding='ISO-8859-1')

    for shp in data.iterrows():
        print(shp[1])
        mpa = None
        if (mpa:=models.MPAZones.objects.filter(site_id=shp[1].OBJECTI)).exists():
            mpa.delete()

        try:
            geo = str(shp[1].geometry)
            geom = None
            if geo.startswith('MULTIPOLYGON'):
                geom = GEOSGeometry(geo)
            else:
                geom = MultiPolygon(GEOSGeometry(geo))
            mpa = models.MPAZones.objects.create(site_id=shp[1].OBJECTI, area_km2=shp[1].Km2, polygon=geom)
        except Exception as ex:
            print(f"Could not load zone {shp[1].OBJECTI} - {shp[1].SitNm_E}")
            print(f"{str(ex)}")

        mpa_english = models.MPATranslations.objects.create(
            mpa=mpa, name=shp[1].SitNm_E, language='en', url=shp[1].URL_E, description=shp[1].Clssf_E, lead_agency=shp[1].LdAgn_E
        )
        mpa_french = models.MPATranslations.objects.create(
            mpa=mpa, name=shp[1].NmDSt_F, language='fr', url=shp[1].URL_F, description=shp[1].Clssf_F, lead_agency=shp[1].AgncP_F
        )

