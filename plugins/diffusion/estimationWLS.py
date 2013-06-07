##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import itk
import medipy.itk

def weigthed_least_squares(images, nb_iter=None):
    """ Least Square Second Order Symmetric Tensor Estimation.
        A diffusion serie is composed of a float reference image (first element 
        in the list) and a set of float diffusion weighted images (on shell, 
        i.e. one bval).
        
        All images must have the same shape and the same dtype, and must 
        contain diffusion metadata.
        
        <gui>
            <item name="images" type="ImageSerie" label="Input"/>
            <item name="nb_iter" type="Int" initializer="1" label="Iteartion Count"
                tooltip="Number of iteration of the WLS estimation"/>
            <item name="output" type="Image" initializer="output=True" 
                  role="return" label="Output"/>
        </gui>
    """
    
    # We're in the same package as itkSecondOrderSymmetricTensorReconstructionFilter, 
    # so it has already been included in itk by __init__
    
    PixelType = medipy.itk.dtype_to_itk[images[0].dtype.type]
    Dimension = images[0].ndim
    InputImage = itk.Image[PixelType, Dimension]
    OutputImage = itk.VectorImage[PixelType, Dimension]
    EstimationFilter = itk.WeightedLeastSquaresImageFilter[
        InputImage, OutputImage]
    
    estimation_filter = EstimationFilter.New()
    estimation_filter.SetBVal(images[1].metadata["mr_diffusion_sequence"][0].diffusion_bvalue.value)
    estimation_filter.SetIterationCount(nb_iter)
    for cnt,image in enumerate(images) :
        itk_image = medipy.itk.medipy_image_to_itk_image(image, False)
        estimation_filter.SetInput(cnt,itk_image)
        
        gradient = image.metadata["mr_diffusion_sequence"][0].\
            diffusion_gradient_direction_sequence.value[0].diffusion_gradient_orientation.value
        estimation_filter.SetGradientDirection(cnt, [float(x) for x in gradient])
    
    itk_output = estimation_filter()[0]
    tensors = medipy.itk.itk_image_to_medipy_image(itk_output,None,True)
    tensors.image_type = "tensor_2"

    return tensors
  
