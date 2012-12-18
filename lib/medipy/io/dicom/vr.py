##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import copy
import operator

class VR(object):
    """ Base class for all VR classes.
    """
    
    def __init__(self, value):
        self.value = value
    
    def __contains__(self, item) :
        return self.value.__contains__(item)
    
    def __deepcopy__(self, memento) :
        new_value = copy.deepcopy(self.value, memento)
        new_object = type(self)(new_value)
        return new_object
    
    def __eq__(self, other):
        return self.value == other
    
    def __getitem__(self, key):
        return self.value.__getitem__(key)
    
    def __getattr__(self, key):
        return getattr(self.value, key)
    
    def __iter__(self) :
        return self.value.__iter__()
    
    def __len__(self):
        return self.value.__len__()
    
    def __ne__(self, other):
        return self.value != other
    
    def __str__(self):
        return str(self.value)
    
    def __unicode__(self):
        return unicode(self.value)
    
    def __repr__(self) :
        return self.value.__repr__()

class AE(VR): pass
class AS(VR): pass
class AT(VR): pass
class CS(VR): pass
class DA(VR): pass
class DS(VR): pass
class DT(VR): pass
class FL(VR): pass
class FD(VR): pass
class IS(VR): pass

class LO(VR): pass
class LT(VR): pass
class OB(VR): pass
class OF(VR): pass
class OW(VR): pass
class PN(VR): pass
class SH(VR): pass
class SL(VR): pass
class SQ(VR): pass
class SS(VR): pass

class UI(VR): pass
class TM(VR): pass
class ST(VR): pass
class UL(VR): pass
class UN(VR): pass
class US(VR): pass
class UT(VR): pass
