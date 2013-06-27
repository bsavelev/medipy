##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################
import wx
import os

import medipy.gui.base
import medipy.base

import medipy.gui.control
import medipy.io.dicom
import medipy.network.dicom
import medipy.gui.base
import medipy.base
import medipy.gui.network.dicom

class QueryDialog(medipy.gui.base.Panel):

    _connections = "network/dicom/connections"
    _current_connection = "network/dicom/current_connection"
    _ssh_connections = "network/dicom/ssh"
    _queries_fields = "network/dicom/queries"

    class UI(medipy.gui.base.UI):
        def __init__(self):
            self.qu_panel = None
            self.search = None
            self.download = None
            self.directory = None
            self.preferences = None
            self.selected_connection = None
            self.results = None
            self.radio = None
            self.set_queries = None
            self.ssh = None
                        
            self.controls = ["qu_panel","search","download","directory",
                "preferences","selected_connection","results","radio","set_queries",
                "ssh"]
            
    def __init__(self, parent=None, *args, **kwargs):
        
        self.connection = None
        self.query_ctrl={}      #Dictionary for wx.controls
        
        # User interface
        self.ui = QueryDialog.UI()
        
        xrc_file = medipy.base.find_resource(os.path.join("resources", "gui", "query_dialog.xrc"))
        wrappers = []
        medipy.gui.base.Panel.__init__(self, xrc_file, "Search and Download", 
            wrappers, self.ui, self.ui.controls, parent, *args, **kwargs)

        #Set Controls
        self.destination = medipy.gui.control.Directory(self.ui.directory)
        sizer=self.ui.directory.GetSizer()
        sizer.Add(self.destination,1,wx.EXPAND)
        self.queries = self.ui.qu_panel.GetSizer()
        
        #Set Events
        self.ui.search.Bind(wx.EVT_BUTTON,self.OnSearch)
        self.ui.download.Bind(wx.EVT_BUTTON,self.OnDownLoad)
        self.destination.add_observer("value", self.OnDestination)
        self.ui.results.Bind(wx.EVT_LIST_ITEM_SELECTED,self.OnResult)
        self.ui.results.Bind(wx.EVT_LIST_ITEM_DESELECTED,self.OnResult)
        self.ui.preferences.Bind(wx.EVT_BUTTON,self.OnPreferences)
        self.ui.selected_connection.Bind(wx.EVT_CHOICE,self.OnChoice)
        self.ui.radio.Bind(wx.EVT_RADIOBOX,self._update_download)
        self.ui.set_queries.Bind(wx.EVT_BUTTON,self.OnSetQueries)
        self.ui.ssh.Bind(wx.EVT_CHECKBOX,self._update_choice)

        self._update_download()
        self._update_choice()
        self._update_queries()
        
        self.Show(True)
    
    #------------------
    #   Update GUI
    #------------------
        
    def _update_queries(self):

        self.queries.Clear(True)
        self.query_ctrl = {}
        self.ui.results.ClearAll()
        
        #Load query preferences
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        self.fields = preferences.get(self._queries_fields,[])
        
        if self.fields == []:
            self.fields = ['patients_name','series_description','study_description']
        self.queries.SetRows(len(self.fields))
                    
        for field in self.fields:
            tag = medipy.io.dicom.dictionary.name_dictionary[field]
            label = medipy.io.dicom.dictionary.data_dictionary[tag][2]
            self.query_ctrl[field] = wx.TextCtrl(self.ui.qu_panel)
            self.queries.Add(wx.StaticText(self.ui.qu_panel,label=label),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.queries.Add(self.query_ctrl[field],proportion=1,
                    flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
            self.ui.results.InsertColumn(
                self.ui.results.GetColumnCount(),label,width=150)
            
            self.queries.Layout()
        
    def _update_choice(self, *args):
        
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        self.ui.selected_connection.Clear()
        
        (choice,self.connection,_,__) = preferences.get(self._current_connection,[])
        
        if not self.ui.ssh.GetValue():
            list_connections = preferences.get(self._connections, [])        
            for connection in list_connections:
                self.ui.selected_connection.Append(connection[1].host+' --- '+
                        str(connection[1].port)+' --- '+connection[0])

        else:
            list_connections = preferences.get(self._ssh_connections, [])
            for connection in list_connections:
                self.ui.selected_connection.Append(connection[1].host+' --- '+
                    str(connection[1].port)+' --- '+connection[1].username+' --- '
                    +connection[0])
        
        self.ui.selected_connection.SetSelection(choice)
            
        
    def _update_download(self, *args, **kwargs):
        self.ui.download.Enable(
            (self.destination.validate() or self.ui.radio.GetSelection()==1)
            and self.ui.results.GetFirstSelected()!=-1)
            
    #------------------
    #   Event handlers
    #------------------
    def OnResult(self, _):
        self._update_download()
    
    def OnDestination(self, _):
        self._update_download()

    def OnSetQueries(self,_):
        self.quer_dlg = wx.Dialog(self,size=(250,300))
        self.quer_panel = medipy.gui.network.dicom.SetQueriesDialog(self.quer_dlg)
        sizer = wx.BoxSizer()
        sizer.Add(self.quer_panel,1,wx.EXPAND)
        
        self.quer_dlg.ShowModal()
        self.quer_dlg.Destroy()
        
        self._update_queries()

    def OnChoice(self,_):
        
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
                
        if not self.ui.ssh.GetValue():
            list_connections = preferences.get(self._connections, [])        
        else :
            list_connections = preferences.get(self._ssh_connections, [])
                   
        choice = self.ui.selected_connection.GetCurrentSelection()
        self.connection = list_connections[choice][1]
        retrieve = list_connections[choice][2]
        retrieve_data = list_connections[choice][3]
        preferences.set(self._current_connection,[choice, self.connection, retrieve,
                retrieve_data])

    def OnPreferences(self,_):
       
        self.pref_dlg = wx.Dialog(self,size=(900,400),
                    style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME)
        if not self.ui.ssh.GetValue():
            self.pref_panel = medipy.gui.network.dicom.PreferencesDialog(self.pref_dlg)
        else :
            self.pref_panel = medipy.gui.network.dicom.SSHDialog(self.pref_dlg)

        sizer = wx.BoxSizer()
        sizer.Add(self.pref_panel, 1, wx.EXPAND)
        self.pref_dlg.SetSizer(sizer)
        
        self.pref_dlg.ShowModal()
        self.pref_dlg.Destroy()
        
        self._update_choice()
        
    def OnSearch(self,_):
        """ Send specified query on dicom.Dataset and show results in ListCtrl
        """
        self.ui.results.DeleteAllItems()
        list_queries={}
        for key, control in self.query_ctrl.items():
            list_queries[key]=control.GetValue()

        echo = medipy.network.dicom.scu.Echo(self.connection)
        try:
            echo()
        except medipy.base.Exception, e:
            dlg = wx.MessageDialog(self, "Cannot contact entity.\nMake sure you entered the right parameters.",'Connection failure',wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            query = medipy.io.dicom.DataSet(**list_queries)
            datasets =  medipy.network.dicom.query.relational(
                        self.connection,"patient","patient",query)

            if datasets==[]:
                self.ui.results.InsertStringItem(0,'No results')
            else:
                for dataset in datasets:
                    index = self.ui.results.InsertStringItem(
                            0,dataset[self.fields[0]].value)

                    for column, key in enumerate(self.fields[1:]) :
                        self.ui.results.SetStringItem(index,1+column,dataset[key].value)

    
    def OnDownLoad(self,_):
        """ DownLoad selected object in ListCtrl
            A path should be specified with control.Directory
        """

        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        (_,self.connection,retrieve,retrieve_data) = preferences.get(self._current_connection, []) 

        query = self.build_retrieve_query()
        if retrieve == 'wado':
            datasets = self.wado_dl(retrieve_data,query)
        elif retrieve == 'move':
            datasets = self.move_dl(retrieve_data,query)
        elif retrieve == 'get':
            pass

        if self.ui.radio.GetSelection()==0:
            save = medipy.io.dicom.routing.SaveDataSet(
                                str(self.destination.value),mode="hierarchical")
            for dataset in datasets:
                save(dataset)
        else:
            images = []
            layers = []
            images.append(medipy.io.dicom.image(datasets))
            for image in images:
                layers.append({"image":image})
            wx.GetApp().frame.append_image(layers)
                            
        dlg = wx.MessageDialog(self, "Successful DownLoad",'Success',
                    wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
  
    #------------------
    #   Retrieve
    #------------------

    def build_retrieve_query(self):
        """ Build a list of queries based on selected area in ListCtrl
        """
        retrieve_query = []
        
        for count in range(self.ui.results.GetItemCount()):
            list_queries={}
            if self.ui.results.IsSelected(count) :  
                for column, key in enumerate(self.fields):
                    if column==0 :
                        list_queries[key] = self.ui.results.GetItemText(count)
                    else :
                        data = self.ui.results.GetItem(count,column)
                        list_queries[key] = data.GetText()

                #Query for any useful uid
                query = medipy.io.dicom.DataSet(**list_queries)
                for key in ["patient_id", "study_instance_uid", 
                                "series_instance_uid", "sop_instance_uid"] :
                    query.setdefault(key, None)
                datasets =  medipy.network.dicom.query.relational(
                        self.connection,"patient","patient",query)
                for dataset in datasets:
                    retrieve_query.append(medipy.io.dicom.DataSet(
                        patient_id = dataset.patient_id.value,
                        study_instance_uid = dataset.study_instance_uid.value,
                        series_instance_uid = dataset.series_instance_uid.value,
                        sop_instance_uid = dataset.sop_instance_uid.value))
                        
        return retrieve_query

    def wado_dl(self,wado_url,retrieve_query):
        datasets_wado = []
        for query in retrieve_query:
            datasets_wado.append(medipy.network.dicom.wado.get(wado_url,query))
            
        return datasets_wado
    
    def move_dl(self,destination,retrieve_query):
        datasets_move = []
        for query in retrieve_query:
            move = medipy.network.dicom.scu.Move(self.connection,"patient","image",
                    destination,query)
            result = move()
            for dataset in result:
                datasets_move.append(dataset)
            
        return datasets_move
