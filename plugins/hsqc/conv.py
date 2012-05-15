"""
Convert ppm2pixel
"""
import numpy as np
import os
import wx
from medipy.gui import colormaps
from medipy.base import Image
from numpy import linalg
from medipy.io import load
import medipy.io.rbnmr as rbnmr
from decimal import *
import fun

def convc(root):
    Co=fun.offset(root,'proc2s')
    CW=fun.SW(root,'proc2s')
    CI=fun.SI(root,'proc2s')
    CF=fun.SF(root,'proc2s')
    cy1=Co-CW/CI/CF/2
    cyn=Co-CW/CF+CW/CI/CF/2
    cnp=CI
    CA=(cyn-cy1)/(cnp-1)
    CB=(cnp*cy1-cyn)/(cnp-1)
    #CA=CA.quantize(Decimal('.0000000001'), rounding=ROUND_HALF_UP)
    #CB=CB.quantize(Decimal('.0000000001'), rounding=ROUND_HALF_UP)
    res=[CA,CB]
    #print CA,CB
    return res
def convh(root):
    Co=fun.offset(root,'procs')
    CW=fun.SW(root,'procs')
    CI=fun.SI(root,'procs')
    CF=fun.SF(root,'procs')
    cy1=Co-CW/CI/CF/2
    cyn=Co-CW/CF+CW/CI/CF/2
    cnp=CI
    CA=(cyn-cy1)/(cnp-1)
    CB=(cnp*cy1-cyn)/(cnp-1)
    #CA=CA.quantize(Decimal('.0000000001'), rounding=ROUND_HALF_UP)
    #CB=CB.quantize(Decimal('.0000000001'), rounding=ROUND_HALF_UP)
    #print CA,CB
    res=[CA,CB]
    return res