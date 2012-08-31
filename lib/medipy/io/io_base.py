##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg, 2011             
# Distributed under the terms of the CeCILL-B license, as published by 
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to            
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html       
# for details.                                                      
##########################################################################

class IOBase(object):
    """ Base class for all IO classes.
    """
    
    def __init__(self, filename=None, report_progress=None):
        self._filename = filename
        self._report_progress = report_progress
    
    filename = property(lambda self:self._filename)