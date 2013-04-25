/*************************************************************************
 * MediPy - Copyright (C) Universite de Strasbourg
 * Distributed under the terms of the CeCILL-B license, as published by
 * the CEA-CNRS-INRIA. Refer to the LICENSE file or to
 * http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
 * for details.
 ************************************************************************/

#include "parameter_estimation.h"
#include "itkParameterEstimationImageFilter.h"

void parameter_estimation(itk::VectorImage<float, 3>::Pointer dt6, 
    itk::VectorImage<float, 3>::Pointer mean, itk::VectorImage<float, 3>::Pointer var,
    itk::Image<float, 3>::Pointer mask, 
    unsigned int w_size_plane, unsigned int w_size_depth, bool masked)
{
    typedef itk::VectorImage<float, 3> VectorImage;

    typedef itk::ParameterEstimationImageFilter<VectorImage, VectorImage> Filter;
    Filter::Pointer filter = Filter::New();
    filter->SetSizePlane(w_size_plane);
    filter->SetSizeDepth(w_size_depth);
    if (masked) { filter->SetMask(mask); }
    filter->GraftNthOutput(0,mean);
    filter->GraftNthOutput(1,var);
    filter->SetInput(0,dt6);
    filter->Update();
}



	  		
