import geopandas as gpd
import rasterio
from rasterio.mask import mask
import datetime
import numpy as np

from raindo.plotter import makeplot_raster


def process_chirps_data(year_min, year_max, paths_dict, opts_dict):
    """Process all the months required for the selected year."""

    shapefile = gpd.read_file(paths_dict['file_aoi'])
    poly = shapefile.geometry.all()
    shapes = [poly]

    res_str = opts_dict['resolution']

    basepath_out = paths_dict['dirs_out'] / f'local_{res_str}_{year_min}-{year_max}'
    basepath_out.mkdir(exist_ok=True)

    for month in range(1,13):
        datafile_list = []
        for year in range(year_min, year_max+1):
            datafile_list.append(
                makedata_rainydays_local(shapes, year, month, paths_dict, opts_dict)
            )

        print(f'Calculating averages for month {month}...')
        filepath_avrg = basepath_out / f'datarecord_m{month:02d}.tif'
        datafile_avrg = makedata_average(filepath_avrg, datafile_list)

        print(f'Plotting data for month {month}...')
        filepath_pdfo = basepath_out / f'rasterplot_m{month:02d}.pdf'
        makeplot_raster(filepath_pdfo, datafile_avrg, opts_dict)


def makedata_rainydays_local(shapes, year, month, paths_dict, opts_dict):
    """Process a single month."""

    # DATE SETUPS
    thisset_y = year
    thisset_m = month
    nextset_y = year+1 if month == 12 else year
    nextset_m = 1 if month == 12 else month+1

    start_date = datetime.date(year=thisset_y, month=thisset_m, day=1)
    final_date = datetime.date(year=nextset_y, month=nextset_m, day=1)
    rain_accum = None

    res_str = opts_dict['resolution']

    # FOLDER AND FILENAMES
    dirpath_tifgz0 = paths_dict['dirs_tmp'] / f'tifgz0'
    dirpath_tifraw = paths_dict['dirs_tmp'] / f'tifraw'
    dirpath_tifaoi = paths_dict['dirs_tmp'] / f'tifaoi'

    dirpath_tifgz0.mkdir(exist_ok=True)
    dirpath_tifraw.mkdir(exist_ok=True)
    dirpath_tifaoi.mkdir(exist_ok=True)

    res_str = opts_dict['resolution']
    dirpath_tifout = paths_dict['dirs_dat'] / f'{year}'
    dirpath_tifout.mkdir(exist_ok=True)
    filepath_tifout = dirpath_tifout / f'rainydays-{res_str}-{year}-{month}.tif'

    # CHECK IF OUTPUT ALREADY EXISTS
    do_accumulation = not filepath_tifout.is_file()
    current_date = final_date
    if do_accumulation:
        current_date = start_date

    while current_date < final_date:
        print(f'Working on date: {current_date}')
        strdate = stringify_datetime(current_date)
        str_y, str_m, str_d = (strdate['y'], strdate['m'], strdate['d'])

        filepath_tifgz0 = dirpath_tifgz0 / f'chirpsv2-raw-{res_str}-{str_y}-{str_m}-{str_d}.tif.gz'
        filepath_tifraw = dirpath_tifraw / f'chirpsv2-raw-{res_str}-{str_y}-{str_m}-{str_d}.tif'
        filepath_tifaoi = dirpath_tifaoi / f'chirpsv2-aoi-{res_str}-{str_y}-{str_m}-{str_d}.tif'

        do_file_download = not filepath_tifgz0.is_file()
        do_file_unzip = not filepath_tifraw.is_file()
        do_projection = not filepath_tifaoi.is_file()

        if do_projection:
            if do_file_unzip:
                if do_file_download:
                    print(' > Downloading...')
                    urlget_tifgz(filepath_tifgz0, current_date, res_str=res_str)
                print(' > Unzipping...')
                unzip_tif(filepath_tifraw, filepath_tifgz0)
            print(' > Projecting')
            project_tif(filepath_tifaoi, filepath_tifraw, shapes)
        print(' > Accumulating')
        rain_accum = accum_rain_data(rain_accum, filepath_tifaoi)

        print(' > Cleaning up ...')
        if not opts_dict['keep_tifgz']:
            filepath_tifgz0.unlink(missing_ok=True)
        if not opts_dict['keep_tifs']:
            filepath_tifraw.unlink(missing_ok=True)
        if not opts_dict['keep_projected']:
            filepath_tifaoi.unlink(missing_ok=True)

        current_date += datetime.timedelta(days=1)
    
    if do_accumulation:
        print('Saving accum')
        create_rastertif(filepath_tifout, rain_accum)

    return filepath_tifout


def makedata_average(filepath_avrg, datafile_list):
    """Creates a file in `filepath_avrg` with the average of the files in `datafile_list`."""

    nfiles = len(datafile_list)
    days_acum = None

    for raster_inpfile in datafile_list:

        with rasterio.open(raster_inpfile, 'r') as src:
            src_data = src.read()
            src_meta = src.meta

        if days_acum is None:
            days_acum = {
                'metadata': src_meta,
                'data': np.zeros(src_data.shape),
            }

        days_acum['data'] += src_data

    #days_acum['data'] = days_acum['data'] / nfiles
    days_acum['data'] = np.rint(days_acum['data'] / nfiles)
    create_rastertif(filepath_avrg, days_acum)
    return filepath_avrg


def create_rastertif(target_filepath, raster_data):
    """Save the tif file with the accumulated data of rainy days."""
    out_meta = raster_data['metadata']
    out_data = raster_data['data']
    with rasterio.open(target_filepath, "w", **out_meta) as dest:
        dest.write(out_data)


def accum_rain_data(rain_accum, filepath_tifaoi, minval=1E-8):
    """Accumulate the data from rainy days by analizing the precipitation tif file."""

    with rasterio.open(filepath_tifaoi, 'r') as src:
        src_data = src.read()
        src_meta = src.meta

    if rain_accum is None:
        rain_accum = {
            'metadata': src_meta,
            'data': np.zeros(src_data.shape),
        }

    rain_accum['data'] += np.where(src_data > minval, 1, 0)
    return rain_accum


def project_tif(target_filename, source_filename, polygon_list):
    """Projects the tif file into the area of interest."""

    with rasterio.open(source_filename, 'r') as src:
        out_image, out_transform = mask(src, polygon_list, crop=True)
        out_meta = src.meta

    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    with rasterio.open(target_filename, "w", **out_meta) as dest:
        dest.write(out_image)


def urlget_tifgz(target_filepath, datetime_object, res_str='p25'):
    """Get the tif from the CHIRPS online database."""
    import requests
    strdate = stringify_datetime(datetime_object)
    str_y, str_m, str_d = (strdate['y'], strdate['m'], strdate['d'])

    remote_filepath = f"{res_str}/{str_y}/chirps-v2.0.{str_y}.{str_m}.{str_d}.tif.gz"
    URL = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/{remote_filepath}"
    response = requests.get(URL)

    with open(target_filepath, "wb") as fileobj:
        fileobj.write(response.content)


def unzip_tif(filename_tgt, filename_src):
    """Unzip the tif file in gz format."""
    import gzip
    import shutil
    with gzip.open(filename_src, 'rb') as f_in:
        with open(filename_tgt, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def stringify_datetime(datetime_object):
    """Stringify a datetime object"""
    str_y = f"{datetime_object.year}"
    str_m = f"{datetime_object.month:02d}"
    str_d = f"{datetime_object.day:02d}"
    return {'y': str_y, 'm': str_m, 'd': str_d}
