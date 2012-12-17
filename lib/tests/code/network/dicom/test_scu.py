import unittest

import medipy.io.dicom
import medipy.network.dicom

class TestSCU(unittest.TestCase):
    
    def setUp(self):
        host = "www.dicomserver.co.uk"
        port = 104
        caller_ae_title = "CALLER"
        called_ae_title = "REMOTE"
        
        self.connection = medipy.network.dicom.Connection(
            host, port, caller_ae_title, called_ae_title)
    
    def test_echo(self):
        echo = medipy.network.dicom.scu.Echo(self.connection)
        echo()
    
    def test_find(self):
        query_parameters = medipy.io.dicom.DataSet()
        query_parameters.patients_name = medipy.io.dicom.PN("*")
        query_parameters.patient_id = medipy.io.dicom.LO("")
    
        patient_find = medipy.network.dicom.scu.Find(
            self.connection, "patient", "patient", query_parameters)
        result = patient_find()
        
        self.assertTrue(len(result)>0)
        self.assertTrue(isinstance(result[0], medipy.io.dicom.DataSet))
        
        dataset = result[0]
        self.assertTrue("patients_name" in dataset)
        self.assertTrue("patient_id" in dataset)

if __name__ == "__main__" :
    unittest.main()
