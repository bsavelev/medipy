##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg, 2011             
# Distributed under the terms of the CeCILL-B license, as published by 
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to            
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html       
# for details.                                                      
##########################################################################

import logging
import sys

import itk
import numpy

from medipy.base import Image
import medipy.itk

from medipy.io.dicom.dictionary import data_dictionary
from medipy.io.dicom import Tag
import medipy.io.dicom.sort

default_skipped_tags = [
    (0x0002,0x0003), # Media Storage SOP Instance UID
    (0x0008,0x0018), # SOP Instance UID
    (0x0020,0x0013), # Instance Number
    (0x0020,0x0032), # Image Position (Patient)
    (0x0020,0x1041), # Slice Location
    (0x0020,0x9057), # In-Stack Position Number
    (0x0028,0x0010), # Rows
    (0x0028,0x0002), # Samples per Pixel
    (0x0028,0x0011), # Columns
    (0x0028,0x0106), # Smallest Image Pixel Value
    (0x0028,0x0107), # Largest Image Pixel Value
    (0x0028,0x1050), # Window Center
    (0x0028,0x1051), # Window Center
]

def to_axis_aligned_ras_space(image):
    """ Transform the image to the closest axis-aligned approximation of RAS
        (i.e. Nifti) space
    """
    
    MatrixType = itk.Matrix[itk.D, 3, 3]
    MatrixBridge = itk.MatrixBridge[MatrixType]
    
    # Transform a point from the (L,P,S) DICOM frame to the (R,A,S) NIfTI frame
    # ITK coordinates order (x,y,z)
    dicom_to_nifti = numpy.asarray([[-1, 0, 0],
                                    [ 0,-1, 0],
                                    [ 0, 0, 1]], dtype=numpy.float64)
    dicom_to_nifti = MatrixBridge.GetMatrixFromArray(dicom_to_nifti)
    
    original_direction = image.direction
    
    direction = best_fitting_axes_aligned_matrix(image.direction)
    itk_direction = numpy.fliplr(numpy.flipud(direction))
    itk_direction = MatrixBridge.GetMatrixFromArray(itk_direction)
    
    itk_image = medipy.itk.medipy_image_to_itk_image(image, False)
    itk_image.SetDirection(itk_direction)
    
    orienter = itk.OrientImageFilter[itk_image, itk_image].New()
    orienter.UseImageDirectionOn()
    orienter.SetInput(itk_image)
    orienter.SetDesiredCoordinateDirection(dicom_to_nifti)
    orienter.Update()
    
    medipy.itk.itk_image_to_medipy_image(orienter.GetOutput(), image, True)
    
    # Restore real orientation : the ideal original direction D_o has been 
    # transformed to D_t : D_t = M.D_o, hence M = D_t.D_o^-1
    # Since directions are orthogonal matrices, we have :
    transformation = numpy.dot(image.direction, direction.T)
    image.direction = numpy.dot(transformation, original_direction)

def best_fitting_axes_aligned_matrix(direction):
    """ Compute the transformation matrix that best fits the given direction 
        matrix while being aligned to the axes.
    """
        
    transformation_matrix = numpy.zeros((3,3))
    for index, v in enumerate(direction) :
        max_alignment = None
        best_model = None
        for model in [(1,0,0), (0,1,0), (0,0,1)] :
            model = numpy.asarray(model)
            
            alignment = numpy.dot(v, model)
            
            if alignment > max_alignment :
                best_model = model
                max_alignment = alignment
            
            model = -model
            
            alignment = numpy.dot(v, model)
            
            if alignment > max_alignment :
                best_model = model
                max_alignment = alignment
        transformation_matrix[index,:] = best_model
    
    return transformation_matrix

def data(datasets):
    """ Build 3-D or 4-D data from datasets.
        
        All Data Sets must belong to the same stack and be geometrically sorted.
    """
    
    sys_is_little_endian = (sys.byteorder == 'little')
    
    # TODO : mosaic/DTI ?
    
    if isinstance(datasets[0], tuple) :
        sample_dataset = datasets[0][0]
    else :
        sample_dataset = datasets[0]
        
    shape = (len(datasets), sample_dataset.rows, sample_dataset.columns)
    dtype = "int%d"%(sample_dataset.bits_allocated)
    if sample_dataset.pixel_representation :
        dtype = "u"+dtype
    dtype = numpy.dtype(dtype)
    
    array = numpy.ndarray(shape, dtype=dtype)
    
    for index, dataset in enumerate(datasets) :
        
        if isinstance(dataset, tuple) :
            transfer_syntax = dataset[0].transfer_syntax_uid
        else :
            transfer_syntax = dataset.transfer_syntax_uid
        
        # Explicit VR big endian. All other are little endian, either explicit
        # or implicit
        dataset_is_little_endian = (transfer_syntax != "1.2.840.10008.1.2.2")
        
        # Get data and swap bytes if necessary
        if isinstance(dataset, tuple) :
            pixel_data = numpy.fromstring(dataset[0].pixel_data, dtype)
            slice = shape[-1]*shape[-2]
            begin = dataset[1]*slice
            end = (1+dataset[1])*slice
            pixel_data = pixel_data[begin:end]
        else :
            pixel_data = numpy.fromstring(dataset.pixel_data, dtype)
        
        if sys_is_little_endian != dataset_is_little_endian :
            pixel_data.byteswap(True)
        
        # Insert into reconstructed data
        pixel_data = pixel_data.reshape(shape[1:])
        array[index] = pixel_data
    
    return array

def metadata(datasets, skipped_tags="default"):
    
    if skipped_tags == "default" :
        skipped_tags = default_skipped_tags
    
    special_processing = [
        (0x0020,0x0032), # Image Position (Patient) : keep only one
        (0x0020,0x0037), # Image Orientation Patient : keep only one
        (0x0028,0x0030), # Pixel Spacing : keep only one
        (0x7fe0,0x0010), # Pixel Data : skip
    ]
    
    result = {}
    for dataset in datasets :
        if isinstance(dataset, tuple) :
            dataset = dataset[0]
        for key, value in dataset.items() :
            
            if key in skipped_tags or key in special_processing :
                continue
            
            if key.private==1 :
                if key.element == 0x0010 :
                    # Private creator
                    private_creator = None
                else :
                    private_creator = dataset.get((key.group, 0x0010), None)
                name = str(key)
            else :
                private_creator = None
                name = data_dictionary[Tag(key, private_creator)][4]
            
            if name not in result :
                result[name] = []
            if value not in result[name] :
                result[name].append(value)
    
    for key, value in result.items() :
        if len(value) == 1 :
            result[key] = value[0]
    
    # Origin
    if isinstance(datasets[0], tuple) :
        functional_group = datasets[0][0].perframe_functional_groups_sequence[datasets[0][1]]
        if "plane_position_sequence" in functional_group :
            origin = functional_group.plane_position_sequence[0].image_position_patient
        else :
            origin = (0,0,0)
    else :
        origin = datasets[0].get("image_position_patient", (0,0,0))
    result["origin"] = tuple(reversed(origin))

    # Spacing
    if isinstance(datasets[0], tuple) :
        functional_group = datasets[0][0].perframe_functional_groups_sequence[datasets[0][1]]
        if "pixel_measures_sequence" in functional_group :
            spacing = functional_group.pixel_measures_sequence[0].get("pixel_spacing", (1.,1.))
        else :
            spacing = (1., 1.)
            
        functional_group_0 = datasets[0][0].perframe_functional_groups_sequence[datasets[0][1]]
        if "plane_position_sequence" in functional_group_0 :
            p0 = functional_group_0.plane_position_sequence[0].image_position_patient
        else :
            p0 = (0,0,0)
        
        functional_group_1 = datasets[1][0].perframe_functional_groups_sequence[datasets[1][1]]
        if "plane_position_sequence" in functional_group_1 :
            p1 = functional_group_1.plane_position_sequence[0].image_position_patient
        else :
            p1 = (0,0,0)
        
        slice_spacing = numpy.linalg.norm(numpy.subtract(p0, p1))
    else :
        spacing = datasets[0].get("pixel_spacing", (1.,1.))
        
        slice_spacing = numpy.linalg.norm(numpy.subtract(
            datasets[0].get("image_position_patient", (0,0,0)), 
            datasets[1].get("image_position_patient", (0,0,0))))
    
    if slice_spacing == 0 :
        slice_spacing = 1.
    result["spacing"] = (slice_spacing,)+tuple(reversed(spacing))
    
    # Orientation
    if isinstance(datasets[0], tuple) :
        functional_group = datasets[0][0].perframe_functional_groups_sequence[datasets[0][1]]
        if "plane_orientation_sequence" in functional_group :
            orientation = functional_group.plane_orientation_sequence[0].get(
                "image_orientation_patient", (1., 0., 0., 
                                              0., 1., 0))
        else :
            logging.warning("Plane Orientation Sequence absent")
            orientation = (1., 0., 0., 0., 1., 0)
    else :
        orientation = datasets[0].get("image_orientation_patient", (1., 0., 0., 
                                                                    0., 1., 0))
    # Use column vectors, cf. PS 3.3, C.7.6.2.1.1
    v1 = orientation[:3]
    v2 = orientation[3:]
    normal = numpy.cross(v1, v2)
    result["direction"] = numpy.transpose(numpy.asarray(
        (tuple(reversed(normal)), tuple(reversed(v2)), tuple(reversed(v1)))))
    
    return result 

def image(datasets, skipped_tags="default", do_sort=True, sort_function=None, 
          align_to_ras=True):
    
    if do_sort :
        medipy.io.dicom.sort.sort(datasets, sort_function)
    
    dictionary = metadata(datasets, skipped_tags)
    origin, spacing, direction = dictionary["origin"], dictionary["spacing"], dictionary["direction"]
    del dictionary["origin"]
    del dictionary["spacing"]
    del dictionary["direction"]
    
    image = Image(data=data(datasets), 
                  origin=origin, spacing=spacing, direction=direction,
                  metadata=dictionary)
    
    if align_to_ras :
        to_axis_aligned_ras_space(image)
    
    return image