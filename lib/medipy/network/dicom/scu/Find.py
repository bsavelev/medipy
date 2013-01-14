##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import glob
import os
import shutil
import subprocess
import tempfile

import medipy.base
import medipy.io.dicom
import medipy.io.dicom.dictionary

from SCU import SCU

class Find(SCU) :
    """ The Find SCU allows simple queries on a DICOM node. This SCU has three
        parameters :
            * the highest-level object that is returned (:attr:`root`)
            * the hierarchy level at which the query is made (:attr:`query_level`)
            * the query parameters (:attr:`query_parameters`)
        
        The following example returns one DataSet for each patient whose name
        begins by `L`. Each resulting DataSet will contain the Patient ID 
        attribute. ::
        
            connection = medipy.io.dicom.Connection("pacs.example.com", 104, 
                "MY_MACHINE", "REMOTE_PACS")
            
            query = medipy.io.dicom.DataSet()
            query.patients_name = medipy.io.dicom.PN("L*")
            query.patient_id = medipy.io.dicom.LO(None)
            
            find = medipy.network.dicom.scu.Find(connection, "patient", "patient", query)
            results = find()
        
        This kind of request is not recursive: a request of the Study Description
        attribute performed at the ``"patient"`` level is not allowed. Moreover,
        the key attributes of higher level must be present in ``query_parameters`` :
            * Patient ID (0010,0020) at the ``"patient"`` level
            * Study Instance UID (0020,000D) at the ``"study"`` level
            * Study Instance UID (0020,000E) at the ``"series"`` level
            * SOP Instance UID (0008,0018) at the ``"image"`` level
    """
    
    #: Query keys for each level.
    keys = {
        "patient" : {
            "patient" : [(0x0010,0x0020)], # Patient ID 
            "study" : [(0x0020,0x000d)], # Study Instance UID
            "series" : [(0x0020,0x000e)], # Series Instance UID
            "image" : [(0x0008,0x0018)], # SOP Instance UID 
        },
        "study" : {
            "study" : [(0x0020,0x000d)], # Study Instance UID
            "series" : [(0x0020,0x000e)], # Series Instance UID
            "image" : [(0x0008,0x0018)], # SOP Instance UID
        }
    }
    
    def __init__(self, connection, root="study", query_level="patient", query_parameters=None) :
        SCU.__init__(self, connection)
        
        # DIMSE
        self._root=None # patient, study. Patient-study not included, as it is retired
        
        # IOD
        self._query_level=None
        self._query_parameters=None
        # Patient ID (0010,0020) must be known for STUDY level
        # Study Instance UID (0020,000D) for SERIES level
        # Series Instance UID (0020,000E) for IMAGE level
        # TODO : define a list a allowed attributes for each level
        
        # Initialization
        self.root = root
        self.query_level = query_level
        self.query_parameters = query_parameters or medipy.io.dicom.DataSet()
    
    def __call__(self) :
        
        # Create a temporary directory for query files and results
        temporary_directory = tempfile.mkdtemp()
        
        # Build the command
        command = ["findscu"]
        
        command.extend(["--aetitle", self.connection.calling_ae_title])
        command.extend(["--call", self.connection.called_ae_title])
        
        root_option = { "patient" : "-P", "study" : "-S" }
        command.append(root_option[self.root])
        
        query_level_option = { "patient" : "PATIENT", "study" : "STUDY", 
                               "series" : "SERIES", "image" : "IMAGE" }
        command.extend([
            "-k", 
            "0008,0052={0}".format(query_level_option[self.query_level])
        ])
        
        command.append("--extract")
        
        command.append(self.connection.host)
        command.append(str(self.connection.port))
        
        query_file = self._create_query_file(self.query_parameters, temporary_directory)
        command.append(query_file)
                
        process = subprocess.Popen(command, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temporary_directory)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0 :
            raise medipy.base.Exception(stderr)
        
        # Process results
        datasets = []
        for filename in glob.glob(os.path.join(temporary_directory, "rsp*.dcm")) :
            dataset = medipy.io.dicom.read(filename)
            datasets.append(dataset)
        
        # Remove temporary directory
        shutil.rmtree(temporary_directory)
        
        return datasets
    
    ##############
    # Properties #
    ##############
    
    def _get_root(self) :
        """ Query root object, may be either ``"patient"`` or ``"study"``.
        """
        
        return self._root
    
    def _set_root(self, root) :
        if root not in ["patient", "study"] :
            raise medipy.base.Exception("Unknown Find root: {0}".format(root))
        if self.query_level is not None :
            # Check that query level is compatible with root
            self._check_root_and_level_compatibility(root, self.query_level)
        if None not in (self.query_level, self.query_parameters) :
            self._check_key_attributes(root, self.query_level, self.query_parameters)
        self._root = root
    
    def _get_query_level(self) :
        """ Query level, may be either ``"patient"``, ``"study"``, ``"series"``
            or ``"image"``.
        """
        
        return self._query_level
    
    def _set_query_level(self, query_level) :
        if query_level not in ["patient", "study", "series", "image"] :
            raise medipy.base.Exception("Unknown query level: {0}".format(query_level))
        if self.root is not None :
            # Check that query level is compatible with root
            self._check_root_and_level_compatibility(self.root, query_level)
        if None not in (self.root, self.query_parameters) :
            self._check_key_attributes(self.root, query_level, self.query_parameters)
        self._query_level = query_level
    
    def _get_query_parameters(self) :
        """ :class:`~medipy.io.dicom.DataSet` containing the queried attributes.
            The following values are allowed
                * a simple value (no wildcard): this criterion selects the 
                  DataSets whose attribute matches *exactly* the query attribute.
                  For string VRs, the criterion is case-dependent, except for 
                  the Person Name (PN) VR.
                * a UID list: the value must be a list of strings, separated by
                  the ``\\`` character. This criterion selects the DataSets whose
                  attribute have a value *contained* in the list.
                * an empty value (``None`` or ``""``): this criterion selects
                  *every* DataSet, and is used to specify an attribute that must
                  be returned by the query.
                * a string containing wildcards (``*`` and ``?``). These two
                  characters have the same meaning as in :py:mod:`fnmatch`: 
                  ``?`` matches any single character, while ``*`` matches any
                  sequence of characters.
                * a Sequence: the sequence shall have only one item, and the
                  criteria will be applied to the item using the rules defined
                  above.
        """
        
        return self._query_parameters
    
    def _set_query_parameters(self, query_parameters) :
        if None not in (self.root, self.query_level) :
            self._check_key_attributes(self.root, self.query_level, query_parameters)
        self._query_parameters = query_parameters
    
    root = property(_get_root, _set_root)
    query_level = property(_get_query_level, _set_query_level)
    query_parameters = property(_get_query_parameters, _set_query_parameters)
    
    #####################
    # Private interface #
    #####################
    
    def _create_query_file(self, query, temporary_directory) :
        f, query_file = tempfile.mkstemp(dir=temporary_directory)
        os.close(f)
        medipy.io.dicom.write(query, query_file)
        
        return query_file
    
    def _check_root_and_level_compatibility(self, root, level):
        if root == "study" and level == "patient" :
            raise medipy.base.Exception(
                "Cannot perform query at STUDY level with a PATIENT root")
    
    def _check_key_attributes(self, root, level, attributes):
        
        for key in Find.keys[root][level] :
            if key not in attributes :
                raise medipy.base.Exception( 
                    "Attributes with a root of {0} and a level of {1} must "
                    "contain {2}".format(root, level, key))
