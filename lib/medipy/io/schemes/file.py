##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

""" Load and save files from the local filesystem.
    
    The path is interpreted as an usual filesystem path.
    
    The fragment must be empty.
"""

import urlparse

import numpy

import medipy.base
from medipy.base import Image

from medipy.io.dicom_io import Dicom
from medipy.io.ipb import IPB
from medipy.io.itk_io import ITK
from medipy.io.nmr2D import Nmr2D
from medipy.io.wx_image import WXImage
io_classes = [Dicom, ITK, IPB, WXImage, Nmr2D]

def save_serie(limages, path, saver=None) :
    """ Save a serie of N 3D images as a volume.
    
        If specified, the "saver" must be an image saver. If not specified,
        a suitable saver will be found automatically.
    """
    
    attributes = ["shape", "origin", "spacing", "direction"]
    for attribute in attributes :
        values = [getattr(image, attribute) for image in limages]
        values = set([tuple(numpy.asarray(x).flatten()) for x in values])
        if len(values) != 1 :
            print values
            raise medipy.base.Exception("All {0}s must be the same".format(attribute))
    
    data = numpy.asarray([image.data for image in limages])
    origin = numpy.hstack(([0], limages[0].origin))
    spacing = numpy.hstack(([1], limages[0].spacing))
    direction = numpy.identity(1+limages[0].ndim)
    direction[1:,1:] = limages[0].direction
    
    composite_image = Image(
        data=data, origin=origin, spacing=spacing, direction=direction)
    
    # Add DWI metadata if they exist
    if all(["mr_diffusion_sequence" in image.metadata for image in limages]) :
        mr_diffusion_sequence = [image.metadata["mr_diffusion_sequence"][0]
                                 for image in limages]
        composite_image.metadata["mr_diffusion_sequence"] = mr_diffusion_sequence
    
    save(composite_image, path, saver)

def load(path, fragment=None, loader=None) :
    """ Load images.
    
        If specified, the "loader" must be an image loader. If not specified,
        a suitable loader will be found automatically.
    """
    
    loader = loader or get_loader(path)
    
    result = []
    
    for index in range(loader.number_of_images()):
    
        data = loader.load_data(index)
        metadata = loader.load_metadata(index)
        metadata["loader"] = {
            "loader" : loader
        }
        
        args = {}
        names = [
            "direction", "origin", "spacing", 
            "data_type", "annotations"
        ]
        if not isinstance(loader, Dicom) :
            names.append("image_type")
        for name in names :
            if name in metadata :
                args[name] = metadata[name]
                del metadata[name]
        args["metadata"] = metadata
        
        result.append(Image(data=data, **args))
    
    return result

def save(image, path, saver=None) :
    """ Save an image.
    
        If specified, the "saver" must be an image saver. If not specified,
        a suitable saver will be found automatically.
    """
    
    saver = saver or get_saver(image, path)
    saver.save(image)

def number_of_images(path, fragment=None, loader=None):
    """ Return the number of images at given path.
    
        If specified, the "loader" must be an image loader. If not specified,
        a suitable loader will be found automatically.
    """
    
    loader = loader or get_loader(path)
    return loader.number_of_images()

def get_loader(path, report_progress=None) :
    """ Search for a suitable loader in io_classes.
    """
    
    for loader_class in io_classes : 
        loader = loader_class(path, report_progress=report_progress)
        if loader.can_load() :
            return loader
    
    # If we get here, no loader was found
    raise medipy.base.Exception("No loader available for {0}".format(path))

def get_saver(image, path, report_progress=None) :
    """ Search for a suitable saver in io_classes.
    """
    
    for saver_class in io_classes : 
        saver = saver_class(path, report_progress=report_progress)
        if saver.can_save(image) :
            return saver
    
    # If we get here, no loader was found
    raise medipy.base.Exception("No saver available for {0}".format(path))
