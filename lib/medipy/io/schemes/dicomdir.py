##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg, 2011             
# Distributed under the terms of the CeCILL-B license, as published by 
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to            
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html       
# for details.                                                      
##########################################################################

""" Load images from a DICOMDIR.

    The path is interpreted as a local filesystem path to a DICOMDIR.
    
    The fragment is of form [ tag "=" value { "&" tag "=" value } ], where tag
    is a DICOM tag in one of the following forms :
      * Numerical (accepted forms : "(0020,000e)", "(0x0020,0x000e)", 
        "0020000e", "0x0020000e")
      * Named, in which case it must be a key of
        medipy.io.dicom.dictionary.name_dictionary
    
    A record in the Directory Record Sequence is considered a match for the 
    fragment if it (or one of its ancestors) contains all the tags in the 
    filters, and matches all the corresponding values. 
"""

import re

import medipy.io.dicom

def load(path, fragment=None) :
    """ Load an image.
    """
    
    datasets = _get_matching_datasets(path, fragment)
    
    if not datasets :
        return None
    else :
        datasets = medipy.io.dicom.load_dicomdir_records(datasets)
        return medipy.io.dicom.image(datasets)

def number_of_images(path, fragment=None) :
    """ Return the number of series in given DICOMDIR.
    """
    
    datasets = _get_matching_datasets(path, fragment)
    return len(medipy.io.dicom.series(datasets))

def _get_filters(fragment) :
    """ Return a list of filters from the URL fragment.
    """
    
    filters = []
    for element in fragment.split("&") :
        tag, value = element.split("=")
        matches = [re.match(r"^\((?:0x)?([\da-fA-F]{4}),(?:0x)?([\da-fA-F]{4})\)$", tag),
                   re.match(r"^(?:0x)?([\da-fA-F]+)$", tag)]
        if matches[0] :
            tag = medipy.io.dicom.Tag(int(matches[0].group(1), 16),
                                      int(matches[0].group(2), 16))
        elif matches[1] :
            tag = medipy.io.dicom.Tag(int(matches[1].group(1), 16))
        else :
            try :
                tag = medipy.io.dicom.Tag(medipy.io.dicom.dictionary.name_dictionary[tag])
            except KeyError :
                raise Exception("No such DICOM tag : \"{0}\"".format(tag))
        filters.append((tag, value))
    
    return filters

def _get_matching_datasets(path, fragment) :
    """ Return the datasets matching the filters defined in fragment
    """
    
    filters = _get_filters(fragment)
    
    dicomdir = medipy.io.dicom.parse(path)
    datasets = []
    
    for record in dicomdir.directory_record_sequence :
        match = True
        for tag, value in filters :
            if tag not in record or record[tag] != value :
                match = False
                break
        
        if match :
            queue = [record]
            while queue :
                dataset = queue.pop(0)
                datasets.append(dataset)
                for child in dataset.children :
                    queue.append(child)
    
    return datasets