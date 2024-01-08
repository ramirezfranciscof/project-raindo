"""Module for plotting tools."""
import rasterio
from rasterio.plot import show

import numpy as np
import matplotlib.pyplot as plt


def makeplot_raster(target_file, source_file, opts_dict):
    """Creates the raster plots from the tif file."""
    fig, ax = plt.subplots(figsize=(10,6))

    scale_max = opts_dict['scale_max']

    with rasterio.open(source_file) as raster:
        raster_data = raster.read()
        extra_data = np.reshape(raster_data, (raster_data.shape[0]*raster_data.shape[1], raster_data.shape[2]))
        extra_image = plt.imshow(extra_data, cmap='viridis_r')
        if scale_max is not None:
            subplot  = show(raster, cmap='viridis_r', vmin=0, vmax=scale_max, title='Number of rainy days in month')
        else:
            subplot  = show(raster, cmap='viridis_r', title='Number of rainy days in month')
        # This is an image like extra_image but somehow it is not a mappable and does not allow to set colorbar?
        #subplot_image = subplot.get_images()
        #print(extra_image)
        #for image in subplot.get_images():
        #    print(image, image == extra_image)

    if scale_max is not None:
        plt.clim(0,scale_max)
        
    colorbar = fig.colorbar(extra_image,  ax=ax)
    plt.savefig(target_file, dpi=300)
