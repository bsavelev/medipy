"""
Metabolites corpus order
"""
import xml_gen as xml
def gen_ord(tab):
    #tab=ser.read_s()
    #tab1=ser.read()
    b_v=xml.cell2tab(tab)
    h=sorted(b_v, key=lambda b: b[2])
    #xml.gen_s(h,nom)
    return h
    
    
def gen_ord1(tab):
    #tab=ser.read_s()
    #tab1=ser.read()
    b_v=xml.cell2tab1(tab)
    h=sorted(b_v, key=lambda b: b[2])
    #xml.gen_s(h,nom)
    return h
        
    
    
