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
import medipy.gui.network.dicom
import medipy.gui.control
import medipy.base
import medipy.io.dicom
import medipy.network.dicom


class QueryDialog(medipy.gui.base.Panel):

    _connections = "network/dicom/connections"
    _current_connection = "network/dicom/current_connection"
    _queries_fields = "network/dicom/queries"
  
    tree_headers = ['patients_birth_date','patients_sex',
    'modalities_in_study','study_date',
    'study_time','modality','number_of_series_related_instances']
  

    class UI(medipy.gui.base.UI):
        def __init__(self):
            self.qu_panel = None
            self.search = None
            self.download = None
            self.directory = None
            self.preferences = None
            self.selected_connection = None
            self.results = None
            self.radio_dl = None
            self.radio_view = None
            self.set_queries = None
                        
            self.controls = ["qu_panel","search","download","directory",
                "preferences","selected_connection","results",
                "radio_dl","radio_view","set_queries"]
            
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
        sizer.Add(self.destination,1,wx.EXPAND|wx.BOTTOM)
        self.queries = self.ui.qu_panel.GetSizer()
        
        self.tree = wx.gizmos.TreeListCtrl(self,name='Patient',
            style=wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_EXTENDED|wx.TR_MULTIPLE)
        treesizer=self.ui.results.GetSizer()
        treesizer.Add(self.tree,1,wx.EXPAND)
        
        #Set Events
        self.ui.search.Bind(wx.EVT_BUTTON,self.OnSearch)
        self.ui.download.Bind(wx.EVT_BUTTON,self.OnDownLoad)
        self.destination.add_observer("value", self.OnDestination)
        self.ui.results.Bind(wx.EVT_LIST_ITEM_SELECTED,self.OnResult)
        self.ui.results.Bind(wx.EVT_LIST_ITEM_DESELECTED,self.OnResult)
        self.ui.preferences.Bind(wx.EVT_BUTTON,self.OnPreferences)
        self.ui.selected_connection.Bind(wx.EVT_CHOICE,self.OnChoice)
        self.ui.radio_dl.Bind(wx.EVT_RADIOBOX,self._update_download)
        self.ui.set_queries.Bind(wx.EVT_BUTTON,self.OnSetQueries)

        self._update_choice()
        self._update_queries()
        self.update_tree_column()
        
        self.Show(True)
    
    #------------------------------------
    #       GUI Update
    #------------------------------------
        
    def _update_queries(self):
        """ Query fields update based on stored queries preferences
        """
        #TODO : Catch exception when an unknown label is entered for name_dictionary
        
        self.queries.Clear(True)
        self.query_ctrl = {}
        self.update_tree()
        
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
            
        self.queries.Layout()
        
    def _update_choice(self, *args):
        """ Connection list update based on stored preferences
        """
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        self.ui.selected_connection.Clear()
        
        choice,_ = preferences.get(self._current_connection,[])

        list_connections = preferences.get(self._connections, [])
        for connection in list_connections:
            self.ui.selected_connection.Append(connection[1].host+' --- '+
                    str(connection[1].port)+' --- '+connection[0])

        self.ui.selected_connection.SetSelection(int(choice))
        
        self.OnChoice()

    def _update_download(self, *args, **kwargs):
        self.ui.download.Enable(
            (self.destination.validate() or self.ui.radio_dl.GetSelection()==1)
            and self.tree.GetSelections()!=-1)

    def update_tree_column(self):    
        self.tree.AddColumn("Patient Tree",width=250)
        self.tree.AddColumn("",width=100)
        self.tree.AddColumn("",width=100)
        self.tree.AddColumn("",width=100)
    
    def update_tree(self,datasets=[]):
        """ TreeCtrl update based on selected view (study or patient):
        """
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot(text='Root')
        for dataset in datasets:
            if self.ui.radio_view.GetSelection()==0:
                shortnames=['patients_name','study_description',
                        'series_description']
                values={}
                for name in shortnames:
                    values[name]=dataset[name].value
            else:
                shortnames=['study','sub_study','patients_name',
                    'study_description','series_description']
                study,sub_study,exam=dataset['study_description'].value.split('^')
                values = {'study':study,'sub_study':sub_study}
                values['patients_name']=dataset['patients_name'].value
                values['study_description']=exam
                values['series_description']=dataset['series_description'].value
                
            if self.tree.ItemHasChildren(self.root) :
                item=self.root
                for name in shortnames:
                    found,child = self.IsChild(item,values[name])
                    if not found:
                        self.CreateSubItems(item,values,
                                shortnames[shortnames.index(name):],dataset)
                        break
                    item=child                            
            else:
                self.CreateSubItems(self.root,values,shortnames,dataset)
            
        self.tree.SortChildren(self.root)
    
    #------------------------------------
    #   Related tree functions
    #------------------------------------
    def CreateSubItems(self,item,values,shortnames,dataset):
        """ Insert items under item
            Shortnames are the different tree sub-levels
            Values are the related values that will be shown in the TreeCtrl
            Related dataset is needed in SetInformations
        """
        for name in shortnames:
            child = self.tree.AppendItem(item,text=values[name])
            self.tree.SetItemPyData(child,name)
            self.SetInformations(child,dataset)
            self.tree.SortChildren(item)
            item=child
  
    def SetInformations(self,item,dataset):
        """ Set informations related to item
            Check item level with ItemPyData
            Format into a more readable piece of information (date, hour...)
        """
        if self.tree.GetItemPyData(item)=='patients_name':
            date = str(dataset['patients_birth_date'].value)
            date = date[6:]+'/'+date[4:6]+'/'+date[:4]
            self.tree.SetItemText(item,str(dataset['patients_sex'].value),1)
            self.tree.SetItemText(item,date,2)
        
        elif self.tree.GetItemPyData(item)=='study_description':
            date = str(dataset['study_date'].value)
            date = date[6:]+'/'+date[4:6]+'/'+date[:4]
            hour = str(dataset['study_time'].value)
            hour = hour[:2]+':'+hour[2:4]+':'+hour[4:6]
            self.tree.SetItemText(item,date,1)
            self.tree.SetItemText(item,hour,2)
            self.tree.SetItemText(item,str(dataset['modalities_in_study'].value),3)
        
        elif self.tree.GetItemPyData(item)=='series_description':
            self.tree.SetItemText(item,
               str(dataset['number_of_series_related_instances'].value)+' images',1)
            self.tree.SetItemText(item,str(dataset['modality'].value),2)

    def ItemQuery(self,item):
        """ Build query (dictionary) based on treectrl item
            If item has child, recursive call until not
            Return a list of queries
        """
        
        queries=[]
        if self.tree.ItemHasChildren(item):
            count = self.tree.GetChildrenCount(item,False)
            child,cookie = self.tree.GetFirstChild(item)
            for index in range(count):
                results = self.ItemQuery(child)
                queries = queries + results
                child,cookie = self.tree.GetNextChild(item,cookie)
        else:
            query={}
            while self.tree.GetItemText(item)!="Root":
                query[self.tree.GetItemPyData(item)]=self.tree.GetItemText(item)
                item = self.tree.GetItemParent(item)
            queries.append(query)
        return queries

    def IsChild(self,itemid,text):
        """ Search text in item.text of any child in itemid
            Return boolean and focused item if found, None if not
        """
        item,cookie = self.tree.GetFirstChild(itemid)
        count = self.tree.GetChildrenCount(itemid,False)
        found = False
        for index in range(count):
            if text == self.tree.GetItemText(item):
                found = True
                break
            else:
                item,cookie = self.tree.GetNextChild(itemid,cookie)
        if found == False:
            item = None
            
        return found,item
            
    #------------------------------------
    #       Event handlers
    #------------------------------------
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

    def OnChoice(self,*args,**kwargs):
        """ Store current connection in preferences (index)
        """
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        
        list_connections = preferences.get(self._connections,[])
        choice = self.ui.selected_connection.GetCurrentSelection()
        
        preferences.set(self._current_connection,(choice,list_connections[choice]))

    def OnPreferences(self,_):       
        self.pref_dlg = wx.Dialog(self,size=(1000,200),
                    style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME)
        self.pref_panel = medipy.gui.network.dicom.PreferencesDialog(self.pref_dlg)

        sizer = wx.BoxSizer()
        sizer.Add(self.pref_panel, 1, wx.EXPAND)
        self.pref_dlg.SetSizer(sizer)
        
        self.pref_dlg.ShowModal()
        self.pref_dlg.Destroy()
        
        self._update_choice()
        
    def OnSearch(self,_):
        """ Use relational to retrieve specified query
            Call update_tree to show results
        """
        
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        _,current = preferences.get(self._current_connection,[])
        connection = current[1]
        
        list_queries={}
        for key, control in self.query_ctrl.items():
            list_queries[key]=control.GetValue()

        echo = medipy.network.dicom.scu.Echo(connection)
        try:
            echo()
        except medipy.base.Exception, e:
            dlg = wx.MessageDialog(self, "Cannot contact entity.\nMake sure you entered the right parameters.",'Connection failure',wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            query = medipy.io.dicom.DataSet(**list_queries)

            for key in ["patient_id", "study_description","series_description"] :
                query.setdefault(key,"")
            
            for key in self.tree_headers:
                query.setdefault(key,"")

            datasets =  medipy.network.dicom.query.relational(
                        connection,"patient","patient",query)

            if datasets==[]:
                dlg = wx.MessageDialog(self, "No Results",'Try again',wx.OK|wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                self.update_tree(datasets)

    
    def OnDownLoad(self,_):
        """ DownLoad selected object in TreeListCtrl
            A path should be specified with control.Directory if stored
        """
        preferences = medipy.gui.base.Preferences(
                wx.GetApp().GetAppName(), wx.GetApp().GetVendorName())
        _,current = preferences.get(self._current_connection,[])
        connection = current[1]
        retrieve = current[2]
        retrieve_data = current[3]
        
        print connection, retrieve, retrieve_data
        
        query = self.build_retrieve_query(connection)
        retrieve_function = getattr(self, "{0}_dl".format(retrieve))
        datasets = retrieve_function(connection,retrieve_data, query)

        if self.ui.radio_dl.GetSelection()==0:  #Store is selected
            save = medipy.io.dicom.routing.SaveDataSet(
                                str(self.destination.value),mode="hierarchical")
            for dataset in datasets:
                save(dataset)
        else:
            series = medipy.io.dicom.series(datasets)
            for serie in series:
                stacks = medipy.io.dicom.split.stacks(serie)
                # Display dialog
                if len(stacks)>1:
                    dialog = medipy.gui.dicom.StacksDialog(self,False)
                    dialog.set_stacks(stacks)
                    if dialog.ShowModal() != wx.ID_OK :
                        stacks=[]
                    stacks = dialog.get_selected_stacks()
                images = [medipy.io.dicom.image(stack) for stack in stacks]
                wx.GetApp().frame.append_image([{"image":image} for image in images])
                            
        dlg = wx.MessageDialog(self, "Successful DownLoad",'Success',
                    wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
            
            
    #------------------
    #   Retrieve
    #------------------

    def build_retrieve_query(self,connection):
        """ Build a list of queries based on selected area in ListCtrl
            Return a list of DataSet
        """
        retrieve_query = []
        
        for item in self.tree.GetSelections():
            list_queries = self.ItemQuery(item)
            for queries in list_queries:
                #Query for any useful uid
                query = medipy.io.dicom.DataSet(**queries)
                for key in ["patient_id", "study_instance_uid", 
                                "series_instance_uid", "sop_instance_uid"] :
                    query.setdefault(key, None)
                datasets =  medipy.network.dicom.query.relational(
                        connection,"patient","patient",query)
                for dataset in datasets:
                    retrieve_query.append(medipy.io.dicom.DataSet(
                        patient_id = dataset.patient_id.value,
                        study_instance_uid = dataset.study_instance_uid.value,
                        series_instance_uid = dataset.series_instance_uid.value,
                        sop_instance_uid = dataset.sop_instance_uid.value))
                        
        return retrieve_query

    def wado_dl(self,connection,wado_url,retrieve_query):
        """ Download data specified in query from wado_url
            Return a list of DataSets
        """
        datasets_wado = []
        for query in retrieve_query:
            datasets_wado.append(medipy.network.dicom.wado.get(wado_url,query))
            
        return datasets_wado
    
    def move_dl(self,connection,destination,retrieve_query):
        """ Move SCU call to download specified query to desination
            Return a list of DataSets
        """
        move_query = medipy.io.dicom.DataSet(sop_instance_uid='')
        for query in retrieve_query:
            sop_uid = str(query.sop_instance_uid.value)
            mv_sop = str(move_query.sop_instance_uid.value) + '\\' + sop_uid
            move_query.__setattr__('sop_instance_uid',mv_sop)
            
        move = medipy.network.dicom.scu.Move(connection, "patient", "image",
                destination, move_query)
        results = move()
        return results
