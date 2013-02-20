##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import itk
import numpy
import vtk

from medipy.base import Object3D 
import medipy.itk

from utils import length, generate_image_sampling

def streamline_tractography(model, seeds=None, step=1.0, min_fa=0.2, 
                            max_angle=numpy.pi/3.0, min_length=25.0, 
                            propagation_type="Euler"):
    """ Streamline 2nd order tensor tractography 
 
    <gui>
        <item name="model" type="Image" label="Input"/>
        <item name="step" type="Float" initializer="1.0" label="Propagation step"/>
        <item name="min_fa" type="Float" initializer="0.2" label="FA threshold"/>
        <item name="max_angle" type="Float" initializer="1.04" label="Angle threshold"/>
        <item name="min_length" type="Float" initializer="25.0" label="Length threshold"/>
        <item name="propagation_type" type="Enum" 
            initializer="('Euler', 'Runge Kutta 4')" 
            label="Choose propagation order"/>
        <item name="output" type="Object3D" role="return" label="Output"/>
    </gui>
    """
    
    if seeds is None :
        seeds = generate_image_sampling(model,step=2.0*model.spacing)
    ndim = len(model.shape)

    VectorImage = itk.VectorImage[medipy.itk.dtype_to_itk[model.dtype.type], model.ndim]
    Image = itk.Image[medipy.itk.dtype_to_itk[model.dtype.type], model.ndim]

    tractography_filter = itk.StreamlineTractographyAlgorithm[VectorImage, Image].New()

    itk_model = medipy.itk.medipy_image_to_itk_image(model, False)
    tractography_filter.SetInputModel(itk_model)
    for seed in seeds:
        tractography_filter.AppendSeed(seed)
    tractography_filter.SetStepSize(step)
    if propagation_type=="Euler" :
        tractography_filter.SetUseRungeKuttaOrder4(False)
    else :
        tractography_filter.SetUseRungeKuttaOrder4(True)
    tractography_filter.SetThresholdAngle(max_angle)
    tractography_filter.SetThresholdFA(min_fa)
    tractography_filter.Update()

    nb_fiber = tractography_filter.GetNumberOfFibers()
    fibers = []
    for i in range(nb_fiber) :
        fibers.append(tractography_filter.GetOutputFiberAsPyArray(i))

    fusion = vtk.vtkAppendPolyData()

    for fiber in fibers :

        if length(fiber,step)>=min_length :
            nb_points = fiber.shape[0]
            scalars = vtk.vtkFloatArray()
            points= vtk.vtkPoints()
            line = vtk.vtkCellArray()
            line.InsertNextCell(nb_points)

            for i in range(nb_points):
                z,y,x = fiber[i]
                points.InsertPoint(i,(x,y,z))
                scalars.InsertTuple1(i,1.0)
                line.InsertCellPoint(i)

            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            polydata.GetPointData().SetScalars(scalars)
            polydata.SetLines(line) 

            fusion.AddInput(polydata)
   
    fusion.Update()
    output = Object3D(fusion.GetOutput(),"Streamline Tractography")
    return output