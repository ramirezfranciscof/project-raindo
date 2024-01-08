import os
import json
import requests

import ee
import rasterio
import numpy as np
import geopandas as gpd

def process_gee_data(year_min, year_max, filepath_aoi, filepath_cred, settings):
    """Get the monthly rasters from GEE."""
    nyears = 1 + year_max - year_min
    geometry0 = None

    for month in range(1,13):
        
        filepath_tif = settings.get('dirpath_out') / f'datarecord_m{month:02d}.tif'
        if filepath_tif.is_file():
            print(
                f'Averages for month {month:02d} already exist; '
                f'to re-calculate delete: {filepath_tif}'
            )
            continue

        if geometry0 is None:
            geometry0 = initialize_and_loadgeom(filepath_cred, filepath_aoi)

        print(f'Calculating averages for month {month}...')
        date_start = f'{year_min}-01-01'
        date_final = f'{year_max+1}-01-01'

        remote_collection = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
        remote_collection = remote_collection.filterDate(date_start, date_final)
        remote_collection = remote_collection.filter(ee.Filter.calendarRange(month, month, 'month'))
        remote_collection = remote_collection.map(lambda image: image.clip(geometry0))
        remote_collection = remote_collection.map(lambda image: image.gt(0.00001))

        remote_image = remote_collection.sum()

        # Not sure why this is not working as I would expect, so I need to normalize locally
        # remote_image0 = remote_image.multiply(1.0)
        # remote_image0 = remote_image.multiply(1/nyears)
        # remote_image0 = remote_image0.round()
        # remote_image0.copyProperties(remote_image, remote_image.propertyNames())
        # remote_image = remote_image0

        url = remote_image.getDownloadUrl({
            'bands': ['precipitation'],
            'region': geometry0,
            'scale': settings.get('scale'),
            'format': 'GEO_TIFF'
        })
        response = requests.get(url)

        filepath_tmp = settings.get('dirpath_out') / f'rainydays_m{month:02d}_tmp.tif'

        with open(filepath_tmp, "wb") as fileobj:
            fileobj.write(response.content)

        with rasterio.open(filepath_tmp, 'r') as rasterobj:
            data = rasterobj.read()
            metadata = rasterobj.meta

        data = np.rint(data / nyears)

        with rasterio.open(filepath_tif, 'w', **metadata) as rasterobj:
            rasterobj.write(data)
        os.remove(filepath_tmp)


def initialize_and_loadgeom(filepath_cred, filepath_aoi):
    """Initialize the GEE credentials."""
    print('Checking credentials...')

    with open(filepath_cred) as fileobj:
        cred_data = json.load(fileobj)
        service_account = cred_data['client_email']

    credentials = ee.ServiceAccountCredentials(service_account, filepath_cred)
    ee.Initialize(credentials)

    shape = gpd.read_file(filepath_aoi)
    json_data = json.loads(shape.to_json())
    geometry0 = ee.Geometry(ee.FeatureCollection(json_data).geometry())
    return geometry0