##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg, 2011             
# Distributed under the terms of the CeCILL-B license, as published by 
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to            
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html       
# for details.                                                      
##########################################################################

import numpy
from tools import MouseTool

class Select(MouseTool) :
    """ Change the cursor position in the image
    """
    
    def __init__(self) :
        super(Select, self).__init__()
    
    def start_interaction(self, rwi, slice) :
        self._set_cursor_position(rwi, slice)
    
    def dispatch_interaction(self, rwi, slice) :
        self._set_cursor_position(rwi, slice)
    
    def _set_cursor_position(self, rwi, slice) :
        index_position = self._display_to_image_index(rwi.GetEventPosition(), slice)
        if not slice.layers or slice.layers[0].image.is_inside(index_position) :
            # Using cursor_physical_position would also work, but we have
            # already computed index_position, so we use it
            slice.cursor_index_position = index_position
            rwi.Render()
    
    def stop_interaction(self, rwi, slice) :
        pass

class Pencil(MouseTool) :
    """ Draw on the image with a given color
    """
    def __init__(self, value, layer=0):
        super(Pencil, self).__init__()
        self.value = value
        self.layer = layer
    
    def start_interaction(self, rwi, slice):
        self._paint(rwi, slice)
    
    def dispatch_interaction(self, rwi, slice) :
        self._paint(rwi, slice)
    
    def _paint(self, rwi, slice) :
        slice_position = self._display_to_slice(rwi.GetEventPosition(), slice)
        
        slice_position[0] = numpy.dot(slice.world_to_slice, 
                                      slice.cursor_physical_position)[0]
        
        world_position = numpy.dot(slice.slice_to_world, slice_position)
        
        image = slice.layers[self.layer].image
        index_position = tuple(((world_position-image.origin)/image.spacing).round())
        
        if image.is_inside(index_position) :
            image[index_position] = self.value
            image.modified()
            rwi.Render()

class Zoom(MouseTool) :
    """ Zoom in (or out, depending on factor)
    """
    def __init__(self, factor) :
        super(Zoom, self).__init__()
        self.factor = factor
    
    def dispatch_interaction(self, rwi, slice) :
        slice.zoom *= self.factor
        rwi.Render()

class MotionZoom(MouseTool):
    """ Zoom in or out, depending on the motion and zoom direction
    """
    
    def __init__(self, factor, direction):
        super(MotionZoom, self).__init__()
        self.factor = factor
        self.direction = direction
    
    def dispatch_interaction(self, rwi, slice):
        position = rwi.GetEventPosition()
        previous_position = rwi.GetLastEventPosition()
        motion = numpy.subtract(position, previous_position)
        
        dot = numpy.dot(motion, self.direction)
        if dot > 0 :
            slice.zoom *= self.factor
        elif dot < 0 :
            slice.zoom /= self.factor
        
        rwi.Render()

class WindowLevel(MouseTool) :
    """ Change the window and level (display range, contrast) of first layer
    """
    def __init__(self, synchronize_layers=False) :
        super(WindowLevel, self).__init__()
        self.synchronize_layers = synchronize_layers
        self._epsilon = 0.01
    
    def dispatch_interaction(self, rwi, slice) :
        size = slice.renderer.GetSize()
        
        # This code comes from vtkInria3D (vtkInteractorStyleImage2D and
        # vtkViewImage2DCommand, heavily inspired by vtkImageViewer)
        
        event_position = rwi.GetEventPosition()
        last_event_position = rwi.GetLastEventPosition()
        
        # Compute normalized delta
        dx = 4.0*(event_position[0]-last_event_position[0])/size[0]
        dy = 4.0*(event_position[1]-last_event_position[1])/size[1]
        
        # Get current window and level
        colormap_min, colormap_max = slice.layers[0].colormap.display_range
        window = (colormap_max-colormap_min)
        level = (colormap_max+colormap_min)/2.0
        
        #  Scale by current values
        if abs(window) > self._epsilon :
            dx *= window
        else :
            dx *= -self._epsilon if window < 0 else self._epsilon
        if abs(level) > self._epsilon :  
            dy *= level
        else :
            dy *= -self._epsilon if level < 0 else self._epsilon
        
        # Abs so that direction does not flip
        if window < 0.0 :
            dx = -dx
        if level < 0.0 :
            dy = -dy
        
        # Compute new window level
        newWindow = dx + window
        newLevel = level - dy
      
        # Stay away from zero and really
        if abs(newWindow) < self._epsilon :
            newWindow *= -self._epsilon if newWindow < 0 else self._epsilon
        if abs(newLevel) < self._epsilon :
            newLevel *= -self._epsilon if newWindow < 0 else self._epsilon
        
        colormap_min = newLevel-newWindow/2.
        colormap_max = newLevel+newWindow/2.
        
        if self.synchronize_layers :
            for layer in slice.layers :
                layer.colormap.display_range = (colormap_min, colormap_max)
        else :
            slice.layers[0].colormap.display_range = (colormap_min, colormap_max)
        
        rwi.Render()

class Pan(MouseTool) :
    """ Change the position (not cursor_position, but image_position) of the 
        slice
    """
    def __init__(self) :
        super(Pan, self).__init__()
        self._interaction_dispatched = False
    
    def start_interaction(self, rwi, slice):
        self._interaction_dispatched = False
    
    def dispatch_interaction(self, rwi, slice) :
        self._interaction_dispatched = True
        
        p1 = self._display_to_slice(rwi.GetEventPosition(), slice)
        p2 = self._display_to_slice(rwi.GetLastEventPosition(), slice)
        
        motion = numpy.subtract(p2, p1)
        motion[0] = 0
        
        if slice.display_coordinates == "index" :
            slice_position = numpy.dot(slice.world_to_slice, 
                                       slice.image_index_position)
        else :
            slice_position = numpy.dot(slice.world_to_slice, 
                                       slice.image_physical_position)
        slice_position = numpy.add(slice_position, motion[-slice.layers[0].image.ndim:])
        world_position = numpy.dot(slice.slice_to_world, slice_position)
        
        if slice.display_coordinates == "index" :
            slice.image_index_position = world_position
        else :
            slice.image_physical_position = world_position
        
        rwi.Render()
        
    def stop_interaction(self, rwi, slice) :
        if not self._interaction_dispatched :
            slice_position = self._display_to_slice(rwi.GetEventPosition(), slice)
            
            image = slice.layers[0].image
            
            if slice.display_coordinates == "physical" :
                slice_position[0] = numpy.dot(slice.world_to_slice, 
                                              slice.cursor_physical_position)[0]
                world_position = numpy.dot(slice.slice_to_world, slice_position)
                index_position = (world_position-image.origin)/image.spacing
            else :
                slice_position[0] = numpy.dot(slice.world_to_slice, 
                                              slice.cursor_index_position)[0]
                index_position = numpy.dot(slice.slice_to_world, slice_position)
                world_position = image.origin+index_position*image.spacing
            
            if image.is_inside(index_position) :
                slice.center_on_physical_position(world_position)
                rwi.Render()