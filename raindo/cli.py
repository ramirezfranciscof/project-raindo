import os
import click

from pathlib import Path

from raindo.core import process_chirps_data

@click.group()
def raindo():
    """Simple program to plot precipitation data from the CHIRPS database."""


@raindo.command()
@click.option('--miny',
    required=True,
    default=2010,
    show_default=True,
    prompt='Please indicate the initial year (incl)',
    type=int,
    help='Initial year for the period to be considered (incl).',
)
@click.option('--maxy',
    required=True,
    default=2020,
    show_default=True,
    prompt='Please indicate the final year (incl)',
    type=int,
    help='Final year for the period to be considered (incl).',
)
@click.option('--aoi',
    required=True,
    default='./aoi/aoi.shp',
    show_default=True,
    prompt='Please indicate the path to the shape file with the area of interest',
    type=click.Path(exists=True, dir_okay=False),
    help='Path to the shape file with the area of interest.',
)
@click.option('--dir-tmp',
    default='./chirps_tmp',
    show_default=True,
    type=click.Path(file_okay=False),
    help='Path where to store all temporary files.',
)
@click.option('--dir-dat',
    default='./chirps_dat',
    show_default=True,
    type=click.Path(file_okay=False),
    help='Path where to store all intermediate files.',
)
@click.option('--dir-out',
    default='./chirps_out',
    show_default=True,
    type=click.Path(file_okay=False),
    help='Path where to store the final plots.',
)
@click.option('--data-resolution',
    default='p25',
    show_default=True,
    type=click.Choice(['p25', 'p05'], case_sensitive=False),
    help='Degree resolution for the source data / final plots (p25 or p05).',
)
@click.option('--keep-tgzs', 
    is_flag=True,
    help='Keep the tif.gz zipped files from CHIRPS after uncompressing them.',
)
@click.option('--keep-tifs', 
    is_flag=True,
    help='Keep the tif files from CHIRPS after processing them.',
)
@click.option('--keep-proj', 
    is_flag=True,
    help='Keep the projected tif files after processing them.',
)
@click.option('--scale-max',
    show_default=True,
    type=int,
    help='Max number of days shown on the scale (by default, every plot will have its max value and the color criteria will not be comparable between them).',
)
#@click.option('--force-download', is_flag=True, help='Forces the downlad of files (even if the tif.gz already exist).')
#@click.option('--force-unzip', is_flag=True, help='Forces the unzipping of files (even if the tif already exist).')
#@click.option('--force-reproject', is_flag=True, help='Forces the re-projection of the tif files (even if the projected files already exist).')
def local(miny, maxy, aoi, dir_tmp, dir_dat, dir_out, data_resolution, keep_tgzs, keep_tifs, keep_proj, scale_max):
    """Get the data from CHIRPS database directly and operate locally."""

    if miny > 2020 or miny < 1981 or maxy > 2020 or maxy < 1981 or maxy < miny:
        raise click.ClickException(
            f'Wrong value for years: min {miny} <= max {maxy} ? '
            f'(additionally, values must be between 1981 and 2020)'
        )

    basepath = Path(dir_tmp)
    basepath.mkdir(exist_ok=True)

    paths_dict = {
        'file_aoi': Path(aoi),
        'dirs_tmp': Path(dir_tmp),
        'dirs_dat': Path(dir_dat),
        'dirs_out': Path(dir_out),
    }

    paths_dict['dirs_tmp'].mkdir(exist_ok=True)
    paths_dict['dirs_dat'].mkdir(exist_ok=True)
    paths_dict['dirs_out'].mkdir(exist_ok=True)

    opts_dict = {
        'resolution': data_resolution,
        'scale_max': scale_max,
        'keep_tifgz': keep_tgzs,
        'keep_tifs': keep_tifs,
        'keep_projected': keep_proj,
    }

    process_chirps_data(miny, maxy, paths_dict, opts_dict)
    print('Done!')

@raindo.command()
@click.option('--miny',
    required=True,
    default=1981,
    show_default=True,
    prompt='Please indicate the initial year (incl)',
    type=int,
    help='Initial year for the period to be considered (incl).',
)
@click.option('--maxy',
    required=True,
    default=2020,
    show_default=True,
    prompt='Please indicate the final year (incl)',
    type=int,
    help='Final year for the period to be considered (incl).',
)
@click.option('--aoi',
    required=True,
    default='./aoi/aoi.shp',
    show_default=True,
    prompt='Please indicate the path to the shape file with the area of interest',
    type=click.Path(exists=True, dir_okay=False),
    help='Path to the shape file with the area of interest.',
)
@click.option('--gee-cred',
    required=True,
    default='./gee_cred.json',
    show_default=True,
    prompt='Please indicate the path to the credentials file for the GEE account',
    type=click.Path(exists=True, dir_okay=False),
    help='Path to the credentials file for the GEE account.',
)
@click.option('--dir-out',
    default='./chirps_out',
    show_default=True,
    type=click.Path(file_okay=False),
    help='Path where to store the final plots.',
)
@click.option('--data-resolution',
    default='10000',
    show_default=True,
    type=int,
    help='Meters per pixel resolution for the source data / final plots (lower number is more granular).',
)
@click.option('--scale-max',
    show_default=True,
    type=int,
    help='Max number of days shown on the scale (by default, every plot will have its max value and the color criteria will not be comparable between plots).',
)
def geesrv(miny, maxy, aoi, dir_out, gee_cred, data_resolution, scale_max):
    """Uses Google Earth Engine (GEE) to get the CHIRPS data and operate on it.
    
    This is more efficient and faster compared to local processing of the data,
    but an account with the proper configuration is necessary.
    """
    from raindo.plotter import makeplot_raster
    from raindo.gee import process_gee_data

    if miny > 2020 or miny < 1981 or maxy > 2020 or maxy < 1981 or maxy < miny:
        raise click.ClickException(
            f'Wrong value for years: min {miny} <= max {maxy} ? '
            f'(additionally, values must be between 1981 and 2020)'
        )

    if data_resolution < 500:
        raise click.ClickException(
            f'Cannot do resolutions lower than 500 (GEE will not allow download of images that heavy)'
        )

    basedir_out = Path(dir_out)
    basedir_out.mkdir(exist_ok=True)

    dirpath_out = basedir_out / f'geesrv_{miny}-{maxy}_res{data_resolution}'
    dirpath_out.mkdir(exist_ok=True)

    gee_settings = {
        'scale': data_resolution,
        'dirpath_out': dirpath_out,
    }
    process_gee_data(miny, maxy, aoi, gee_cred, gee_settings)

    print(f'Plotting the rasters...')
    for month in range(1,13):
        filepath_tif = dirpath_out / f'datarecord_m{month:02d}.tif'
        filepath_pdf = dirpath_out / f'rasterplot_m{month:02d}.pdf'
        makeplot_raster(filepath_pdf, filepath_tif, {'scale_max': scale_max})

    print('Done!')

################################################################################
if __name__ == '__main__':
    raindo()
################################################################################
