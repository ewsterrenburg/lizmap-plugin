# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Lizmap
                                 A QGIS plugin
 Publication plugin for Lizmap web application, by 3liz.com
                                -------------------
        begin                : 2011-11-01
        copyright            : (C) 2011 by 3liz
        email                : info@3liz.com
 ***************************************************************************/

/****** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1

 The contents of this file are subject to the Mozilla Public License Version
 1.1 (the "License"); you may not use this file except in compliance with
 the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/

 Software distributed under the License is distributed on an "AS IS" basis,
 WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 for the specific language governing rights and limitations under the
 License.

 The Original Code is 3liz code,

 The Initial Developer of the Original Code are René-Luc D'Hont rldhont@3liz.com
 and Michael Douchin mdouchin@3liz.com
 Portions created by the Initial Developer are Copyright (C) 2011
 the Initial Developer. All Rights Reserved.

 Alternatively, the contents of this file may be used under the terms of
 either of the GNU General Public License Version 2 or later (the "GPL"),
 or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.

 ***** END LICENSE BLOCK ***** */
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from lizmapdialog import lizmapDialog
# import other needed tool
import sys, os, glob
# ftp lib
import ftplib
# configuration parser
import ConfigParser
# date and time
import time, datetime
# json handling
import json
# supprocess module, to load external command line tools
import subprocess

class lizmap:
    if sys.platform.startswith('win'):
        style = ['0', '0', '0', '5%']
        margin = '4.0'
    else:
        style = ['225', '225', '225', '90%']
        margin = '2.5'
    STYLESHEET = "QGroupBox::title {background-color: transparent; \
                                    subcontrol-origin: margin; \
                                    margin-left: 6px; \
                                    subcontrol-position: top left; \
                                    }"
    STYLESHEET += "QGroupBox {background-color: rgba(%s, %s, %s, %s" % tuple(style)
    STYLESHEET += ");"
    STYLESHEET += "border:1px solid rgba(0,0,0,20%);  \
                   border-radius: 5px; \
                   font-weight: bold;"
    STYLESHEET += "margin-top: %s" % margin
    STYLESHEET += "ex; }"

    def __init__(self, iface):
        '''Save reference to the QGIS interface'''
        self.iface = iface
        # Qgis version
        try:
            self.QgisVersion = unicode(QGis.QGIS_VERSION_INT)
        except:
            self.QgisVersion = unicode(QGis.qgisVersion)[ 0 ]

        # initialize plugin directory
        self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/lizmap"
        # initialize locale
        localePath = ""
        self.locale = QSettings().value("locale/userLocale")[0:2]

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/lizmap_" + self.locale + ".qm"

        self.translator = QTranslator()
        if QFileInfo(localePath).exists():
            self.translator.load(localePath)
        else:
            self.translator.load(self.plugin_dir + "/i18n/lizmap_en.qm")

        if qVersion() > '4.3.3':
            QCoreApplication.installTranslator(self.translator)

        # Create the dialog and keep reference
        self.dlg = lizmapDialog()

        # FTP Sync only active for linux and windows users.
        if not sys.platform.startswith('linux') and sys.platform != 'win32' :
            self.dlg.ui.tabWidget.setTabEnabled(3, False)
            self.dlg.ui.btSync.setEnabled(False)
            
        # Set stylesheet for QGroupBox
        self.dlg.ui.gb_tree.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_layerSettings.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_visibleTools.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_Scales.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_externalLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_locateByLayer.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_editionLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_loginFilteredLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_ftpParams.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_ftpDir.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_winscp.setStyleSheet(self.STYLESHEET)

        # Disable winscp path field for non windows users
        if sys.platform != 'win32':
            self.dlg.ui.inWinscpPath.setEnabled(False)
            self.dlg.ui.btWinscpPath.setEnabled(False)
            self.dlg.ui.lbWinscpHelp.setEnabled(False)
            self.dlg.ui.lbWinscpIn.setEnabled(False)
            self.dlg.ui.inWinscpSession.setEnabled(False)
            self.dlg.ui.lbWinscpSession.setEnabled(False)
            self.dlg.ui.inWinscpCriteria.setEnabled(False)
            self.dlg.ui.lbWinscpCriteria.setEnabled(False)

        # List of ui widget for data driven actions and checking
        
        self.globalOptions = {
            'mapScales': {
                'widget': self.dlg.ui.inMapScales, 
                'wType': 'text', 'type': 'intlist', 'default': [500000, 250000, 100000, 25000]
            },
            'minScale': {
                'widget': self.dlg.ui.inMinScale, 
                'wType': 'text', 'type': 'integer', 'default': 1
            },
            'maxScale': {
                'widget': self.dlg.ui.inMaxScale, 
                'wType': 'text', 'type': 'integer', 'default': 1000000000
            },
        
            'googleKey': {
                'widget': self.dlg.ui.inGoogleKey, 
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'googleHybrid' : {
                'widget': self.dlg.ui.cbGoogleHybrid, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleSatellite' : {
                'widget': self.dlg.ui.cbGoogleSatellite, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleTerrain' : {
                'widget': self.dlg.ui.cbGoogleTerrain, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleStreets' : {
                'widget': self.dlg.ui.cbGoogleStreets, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'osmMapnik' : {
                'widget': self.dlg.ui.cbOsmMapnik, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'osmMapquest' : {
                'widget': self.dlg.ui.cbOsmMapquest, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            
            'rootGroupsAsBlock' : {
                'widget': self.dlg.ui.cbRootGroupsAsBlock, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            
            'print' : {
                'widget': self.dlg.ui.cbActivatePrint, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'measure' : {
                'widget': self.dlg.ui.cbActivateMeasure, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'externalSearch' : {
                'widget': self.dlg.ui.liExternalSearch, 
                'wType': 'list', 'type': 'string', 'default': '', 'list':['', 'nominatim']
            },
            'zoomHistory' : {
                'widget': self.dlg.ui.cbActivateZoomHistory, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'geolocation' : {
                'widget': self.dlg.ui.cbActivateGeolocation, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'remoteDir': {
                'widget': self.dlg.ui.inRemotedir, 
                'wType': 'text', 'type': 'string', 'default': ''
            }
        }
        
        self.layerOptionsList = {
            'title': {
                'widget': self.dlg.ui.inLayerTitle, 
                'wType': 'text', 'type': 'string', 'default':'', 'isMetadata':True
            },
            'abstract': {
                'widget': self.dlg.ui.teLayerAbstract, 
                'wType': 'textarea', 'type': 'string', 'default': '', 'isMetadata':True
            },
            'link': {
                'widget': self.dlg.ui.inLayerLink, 
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'minScale': {
                'widget': None, 
                'wType': 'text', 'type': 'integer', 'default': 1
            },
            'maxScale': {
                'widget': None, 
                'wType': 'text', 'type': 'integer', 'default': 1000000000000
            },
            'toggled': {
                'widget': self.dlg.ui.cbToggled, 
                'wType': 'checkbox', 'type': 'boolean', 'default': True
            },
            'popup': {
                'widget': self.dlg.ui.cbPopup, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'popupTemplate': {
                'widget': None, 
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'groupAsLayer': {
                'widget': self.dlg.ui.cbGroupAsLayer, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'baseLayer': {
                'widget': self.dlg.ui.cbLayerIsBaseLayer, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'singleTile': {
                'widget': self.dlg.ui.cbSingleTile, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False, 
                'exclude': {'widget': self.dlg.ui.cbCached, 'key': 'cached'}
            },
            'imageFormat': {
                'widget': self.dlg.ui.liImageFormat, 
                'wType': 'list', 'type': 'string', 'default': 'image/png', 
                'list':["image/png", "image/png; mode=8bit", "image/jpeg"]
            },
            'cached': {
                'widget': self.dlg.ui.cbCached, 
                'wType': 'checkbox', 'type': 'boolean', 'default': False, 
                'exclude': {'widget': self.dlg.ui.cbSingleTile, 'key': 'singleTile'}
            },
            'cacheExpiration': {
                'widget': self.dlg.ui.inCacheExpiration, 
                'wType': 'spinbox', 'type': 'integer', 'default': 0
            },
            'metatileSize': {
                'widget': self.dlg.ui.inMetatileSize, 
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'clientCacheExpiration': {
                'widget': self.dlg.ui.inClientCacheExpiration, 
                'wType': 'spinbox', 'type': 'integer', 'default': 300
            }
        }
        
        # map qgis geometry type
        self.mapQgisGeometryType = {
            0 : 'point',
            1 : 'line',
            2 : 'polygon',
            3 : 'unknown',
            4 : 'none'
        }
        
        # Disable checkboxes on the layer tab
        self.enableCheckBox(False)

        # Catch user interaction on layer tree and inputs
        self.dlg.ui.treeLayer.itemSelectionChanged.connect(self.setItemOptions)

        # Catch user interaction on Map Scales input
        self.dlg.ui.inMapScales.editingFinished.connect(self.getMinMaxScales)
        
        # Connect widget signals to setLayerProperty method depending on widget type
        from functools import partial
        for key, item in self.layerOptionsList.items():
            if item['widget']:
                control = item['widget']
                slot = partial(self.setLayerProperty, key)
                if item['wType'] in ('text', 'spinbox'):
                    control.editingFinished.connect(slot)
                elif item['wType'] == 'textarea':
                    control.textChanged.connect(slot)
                elif item['wType'] == 'checkbox':
                    control.stateChanged.connect(slot)
                elif item['wType'] == 'list':
                    control.currentIndexChanged.connect(slot)


    def initGui(self):
        '''Create action that will start plugin configuration'''
        self.action = QAction(QIcon(":/plugins/lizmap/icon.png"),
                                    "lizmap", self.iface.mainWindow())

        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Create action for help dialog
        self.action_help = QAction(QIcon(":/plugins/lizmap/help.png"),
                                    "&Help...", self.iface.mainWindow())
        # connect help action to help dialog
        self.action_help.triggered.connect(self.showHelp)

        # Create action for about dialog
        self.action_about = QAction(QIcon(":/plugins/lizmap/help.png"),
                                    "&About...", self.iface.mainWindow())
        # connect about action to about dialog
        self.action_about.triggered.connect(self.showAbout)

        # connect Lizmap signals and functions
        # save button clicked
        self.dlg.ui.btSave.clicked.connect(self.getMapOptions)
        # ftp sync button clicked
        self.dlg.ui.btSync.clicked.connect(self.ftpSync)
        # winscp get path button
        self.dlg.ui.btWinscpPath.clicked.connect(self.chooseWinscpPath)
        # clear log button clicked
        self.dlg.ui.btClearlog.clicked.connect(self.clearLog)
        # Cancel FTP Sync
        self.dlg.ui.btCancelFtpSync.clicked.connect(self.ftpSyncCancel)
        # refresh layer tree button click
#        QObject.connect(self.dlg.ui.btRefreshTree, SIGNAL("clicked()"), self.refreshLayerTree )
        # refresh layer tree button click
        self.dlg.ui.btHelp.clicked.connect(self.showHelp)
        # configure popup button
        self.dlg.ui.btConfigurePopup.clicked.connect(self.configurePopup)
        # detect close event
        self.dlg.ui.buttonClose.rejected.connect(self.warnOnClose)
        self.dlg.rejected.connect(self.warnOnClose)
        
        
        
        # Locate by layers
        # detect layer locate list has changed to refresh layer field list
        self.dlg.ui.liLocateByLayerLayers.currentIndexChanged[str].connect(self.updateLocateFieldListFromLayer)
        # add a layer to the locateByLayerList
        self.dlg.ui.btLocateByLayerAdd.clicked.connect(self.addLayerToLocateByLayer)
        # remove a layer from the locateByLayerList
        self.dlg.ui.btLocateByLayerDel.clicked.connect(self.removeLayerFromLocateByLayer)
        
        # Edition layers
        # add a layer to the editionLayerList
        self.dlg.ui.btEditionLayerAdd.clicked.connect(self.addLayerToEditionLayer)
        # remove a layer from the editionLayerList
        self.dlg.ui.btEditionLayerDel.clicked.connect(self.removeLayerFromEditionLayer)

        # Login filtered layers
        # detect layer locate list has changed to refresh layer field list
        self.dlg.ui.liLoginFilteredLayerLayers.currentIndexChanged[str].connect(self.updateLoginFilteredFieldListFromLayer)
        # add a layer to the list
        self.dlg.ui.btLoginFilteredLayerAdd.clicked.connect(self.addLayerToLoginFilteredLayer)
        # remove a layer from the list
        self.dlg.ui.btLoginFilteredLayerDel.clicked.connect(self.removeLayerFromLoginFilteredLayer)

        # first check if Web menu availbale in this QGIS version
        if hasattr(self.iface, "addPluginToWebMenu"):
            #add plugin to the web plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action)
            #add plugin help to the plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action_help)
            #add plugin about to the plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action_about)
            # and add button to the Web panel
            self.iface.addWebToolBarIcon(self.action)
        else:
            #add icon to the toolbar
            self.iface.addToolBarIcon(self.action)
            #add plugin to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action)
            #add plugin help to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action_help)
            #add plugin about to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action_about)


    def unload(self):
        '''Remove the plugin menu item and icon'''
        # first check if Web menu availbale in this QGIS version
        if hasattr(self.iface, "addPluginToWebMenu"):
            # new menu used, remove submenus from main Web menu
            self.iface.removePluginWebMenu(u"&LizMap", self.action)
            # also remove button from Web toolbar
            self.iface.removeWebToolBarIcon(self.action)
            # Remove help menu entry
            self.iface.removePluginWebMenu(u"&LizMap", self.action_help)
            # Remove about menu entry
            self.iface.removePluginWebMenu(u"&LizMap", self.action_about)
        else:
            #remove plugin
            self.iface.removePluginMenu(u"&LizMap", self.action)
            #remove icon
            self.iface.removeToolBarIcon(self.action)
            # Remove help menu entry
            self.iface.removePluginMenu(u"&LizMap", self.action_help)
            # Remove about menu entry
            self.iface.removePluginMenu(u"&LizMap", self.action_about)


    def showHelp(self):
        '''Opens the html help file content with default browser'''
        if self.locale in ('fr'):
            localHelpUrl = "http://docs.3liz.com/%s/" % self.locale
        else:
            localHelpUrl = 'http://translate.google.fr/translate?sl=fr&tl=%s&js=n&prev=_t&hl=fr&ie=UTF-8&eotf=1&u=http://docs.3liz.com' % self.locale
        QDesktopServices.openUrl( QUrl(localHelpUrl) )

    def showAbout(self):
        '''Opens the about html content with default browser'''
        localAbout = "http://hub.qgis.org/projects/lizmapplugin"
        self.log(localAbout, abort=True, textarea=self.dlg.ui.outLog)
        QDesktopServices.openUrl( QUrl(localAbout) )


    def log(self,msg, level=1, abort=False, textarea=False):
        '''Log the actions and errors and optionnaly print them in given textarea'''
        if abort:
            sys.stdout = sys.stderr
        if textarea:
            textarea.append(msg)
        if abort:
            self.isok = 0

    def clearLog(self):
        '''Clear the content of the textarea log'''
        self.dlg.ui.outLog.clear()
        self.dlg.ui.outState.setText('<font color="green"></font>')

    def enableCheckBox(self, value):
        '''Enable/Disable checkboxes and fields of the Layer tab'''
        for key,item in self.layerOptionsList.items():
            if item['widget']:
                item['widget'].setEnabled(value)
        self.dlg.ui.btConfigurePopup.setEnabled(value)
        
    def getMinMaxScales(self):
        ''' Get Min Max Scales from scales input field'''
        minScale = 1
        maxScale = 1000000000
        inMapScales = str(self.dlg.ui.inMapScales.text())
        mapScales = [int(a.strip(' \t') ) for a in inMapScales.split(',') if str(a.strip(' \t')).isdigit()]
        mapScales.sort()
        if len(mapScales) < 2:
            myReturn = False
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "log.map.mapScales.warning"),
                QMessageBox.Ok)
        else:
            minScale = min(mapScales)
            maxScale = max(mapScales)
            myReturn = True
        self.dlg.ui.inMinScale.setText(str(minScale))
        self.dlg.ui.inMaxScale.setText(str(maxScale))
        self.dlg.ui.inMapScales.setText(', '.join(map(str, mapScales)))
        
        return myReturn


    def getConfig(self):
        ''' Get the saved configuration from lizmap.cfg file
        and from the projet.qgs.cfg config file.
        Populate the gui fields accordingly'''

        # Get the global config file
        cfg = ConfigParser.ConfigParser()
        configPath = os.path.join( self.plugin_dir, "lizmap.cfg")
        if os.path.exists(configPath):
            cfg.read(configPath)
            # Set the FTP tab fields values
            self.dlg.ui.inHost.setText(cfg.get('Ftp', 'host'))
            self.dlg.ui.inUsername.setText(cfg.get('Ftp', 'username'))
            self.dlg.ui.inWinscpPath.setText(str(cfg.get('Ftp', 'winscppath')).decode('utf-8'))
            self.dlg.ui.inPort.setText(cfg.get('Ftp', 'port'))
            self.dlg.ui.inWinscpSession.setText(cfg.get('Ftp', 'winscpSession'))
            self.dlg.ui.inWinscpCriteria.setText(cfg.get('Ftp', 'winscpCriteria'))
        else:
            configPath = os.path.join( self.plugin_dir, "lizmap.cfg")
            cfg.add_section('Ftp')
            cfg.set('Ftp', 'host', '')
            cfg.set('Ftp', 'username', '')
            cfg.set('Ftp', 'port', '')
            cfg.set('Ftp', 'winscppath', '')
            cfg.set('Ftp', 'winscpSession', '')
            cfg.set('Ftp', 'winscpCriteria', 'time')
            cfg.write(open(configPath,"w"))
            cfg.read(configPath)

        # Get the project config file (projectname.qgs.cfg)
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        jsonOptions = {}
        jsonLocateByLayer = {}
        jsonEditionLayers = {}
        jsonLoginFilteredLayers = {}
        if os.path.exists(unicode(jsonFile)):
            f = open(jsonFile, 'r')
            jsonFileReader = f.read()
            try:
                sjson = json.loads(jsonFileReader)
                jsonOptions = sjson['options']
                if sjson.has_key('locateByLayer'):
                    jsonLocateByLayer = sjson['locateByLayer']
                if sjson.has_key('editionLayers'):
                    jsonEditionLayers = sjson['editionLayers']
                if sjson.has_key('loginFilteredLayers'):
                    jsonLoginFilteredLayers = sjson['loginFilteredLayers']
            except:
                isok=0
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    QMessageBox.Ok)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    abort=True,
                    textarea=self.dlg.ui.outLog)

        
        # Set the global options (map, tools, FTP remote dir, etc.)
        for key, item in self.globalOptions.items():
            if item['widget']:
                if item['wType'] == 'checkbox':
                    item['widget'].setChecked(item['default'])
                    if jsonOptions.has_key(key):
                        if jsonOptions[key].lower() in ('yes', 'true', 't', '1'):
                            item['widget'].setChecked(True)

                if item['wType'] in ('text', 'textarea'):
                    if isinstance(item['default'], (list, tuple)):
                        item['widget'].setText(", ".join(map(str, item['default'])))
                    else:
                        item['widget'].setText(str(item['default']))
                    if jsonOptions.has_key(key):
                        if isinstance(jsonOptions[key], (list, tuple)):
                            item['widget'].setText(", ".join(map(str, jsonOptions[key])))
                        else:
                            item['widget'].setText(str(jsonOptions[key]))
                            
                    
                if item['wType'] == 'spinbox':
                    item['widget'].setValue(int(item['default']))
                    if jsonOptions.has_key(key):
                        item['widget'].setValue(int(jsonOptions[key]))
                    
                if item['wType'] == 'list':
                    listDic = {item['list'][i]:i for i in range(0, len(item['list']))}
                    item['widget'].setCurrentIndex(listDic[item['default']])
                    if jsonOptions.has_key(key):
                        item['widget'].setCurrentIndex(listDic[jsonOptions[key]])           
                
        # Fill the locateByLayer table widget
        # empty previous content
        lblTableWidget = self.dlg.ui.twLocateByLayerList
        for row in range(lblTableWidget.rowCount()):
            lblTableWidget.removeRow(row)
        lblTableWidget.setRowCount(0)
        # fill from the json if exists
        if jsonLocateByLayer:
            # load content from json file
            for k,v in jsonLocateByLayer.items():
                twRowCount = lblTableWidget.rowCount()
                # add a new line
                lblTableWidget.setRowCount(twRowCount + 1)
                lblTableWidget.setColumnCount(4)                
                # layer name
                newItem = QTableWidgetItem(k)
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 0, newItem)
                # layer field
                newItem = QTableWidgetItem(v['fieldName'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 1, newItem)
                # displayGeom
                newItem = QTableWidgetItem(v['displayGeom'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 2, newItem)
                # layer id
                newItem = QTableWidgetItem(v['layerId'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 3, newItem)
        lblTableWidget.setColumnHidden(3, True)
        
        # Edition layers tool
        # empty previous content
        lblTableWidget_2 = self.dlg.ui.twEditionLayerList
        for row in range(lblTableWidget_2.rowCount()):
            lblTableWidget_2.removeRow(row)
        lblTableWidget_2.setRowCount(0)
        # fill from the json if exists
        if jsonEditionLayers:
            # load content from json file
            for k,v in jsonEditionLayers.items():
                twRowCount = lblTableWidget_2.rowCount()
                # add a new line
                lblTableWidget_2.setRowCount(twRowCount + 1)
                lblTableWidget_2.setColumnCount(6)         
                # layer name
                newItem = QTableWidgetItem(k)
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 0, newItem)
                # create
                newItem = QTableWidgetItem(v['capabilities']['createFeature'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 1, newItem)
                # modify attributes
                newItem = QTableWidgetItem(v['capabilities']['modifyAttribute'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 2, newItem)                
                # modify geometry
                newItem = QTableWidgetItem(v['capabilities']['modifyGeometry'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 3, newItem)
                # delete
                newItem = QTableWidgetItem(v['capabilities']['deleteFeature'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 4, newItem)
                # layer id
                newItem = QTableWidgetItem(v['layerId'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget_2.setItem(twRowCount, 5, newItem)
        lblTableWidget_2.setColumnHidden(5, True)

        # Fill the loginFilteredLayers table widget
        # empty previous content
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        for row in range(lblTableWidget.rowCount()):
            lblTableWidget.removeRow(row)
        lblTableWidget.setRowCount(0)
        # fill from the json if exists
        if jsonLoginFilteredLayers:
            # load content from json file
            for k,v in jsonLoginFilteredLayers.items():
                twRowCount = lblTableWidget.rowCount()
                # add a new line
                lblTableWidget.setRowCount(twRowCount + 1)
                lblTableWidget.setColumnCount(3)
                # layer name
                newItem = QTableWidgetItem(k)
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 0, newItem)
                # layer field
                newItem = QTableWidgetItem(v['filterAttribute'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 1, newItem)
                # layer id
                newItem = QTableWidgetItem(v['layerId'])
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, 2, newItem)
        lblTableWidget.setColumnHidden(2, True)

        return True



    def getQgisLayerById(self, myId):
        '''Get a QgsLayer by its Id'''
        for layer in self.iface.legendInterface().layers():
            if myId == layer.id():
                return layer
        return None
        
    def getQgisLayerByNameFromCombobox(self, layerComboBox):
        '''Get a layer by its name'''
        returnLayer = None
        uniqueId = unicode(layerComboBox.itemData(layerComboBox.currentIndex()))
        try:
            myInstance = QgsMapLayerRegistry.instance()
            layer = myInstance.mapLayer(uniqueId)
            if layer:
                if layer.isValid():
                    returnLayer = layer
        except:
            returnLayer = None
        return returnLayer        


    def populateLayerCombobox(self, combobox, ltype='all', providerTypeList=['all']):
        '''
            Get the list of layers and add them to a combo box
            * ltype can be : all, vector, raster
            * providerTypeList is a list and can be : ['all'] or a list of provider keys
            as ['spatialite', 'postgres'] or ['ogr', 'postgres'], etc.
        '''
        # empty combobox
        combobox.clear()
        # add empty item
        combobox.addItem ( '---', -1)
        # get canvas
        canvas = self.iface.mapCanvas()
        # loop though the layers
        for i in range( canvas.layerCount() ):
            layer = canvas.layer( i )
            layerId = layer.id()
            # vector
            if layer.type() == QgsMapLayer.VectorLayer and ltype in ('all', 'vector'):
                if 'all' in providerTypeList or layer.providerType() in providerTypeList:
                    combobox.addItem ( layer.name(), unicode(layerId))
            # raster
            if layer.type() == QgsMapLayer.RasterLayer and ltype in ('all', 'raster'):
                combobox.addItem ( layer.name(),unicode(layerId))
                
                
    def updateLocateFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields 
            for the layer chosen with the liLayerLocateLayer combobox
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLocateByLayerLayers)

        # remove previous items
        self.dlg.ui.liLocateByLayerFields.clear()
        # populate the columns combo box
        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                provider = layer.dataProvider()
                fields = provider.fields()
                for field in fields:
                    self.dlg.ui.liLocateByLayerFields.addItem(
                        unicode(field.name()),
                        unicode(field.name())
                    )           
        else:
            return None

    def updateLoginFilteredFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields 
            for the layer chosen with the liLayerLocateLayer combobox
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLoginFilteredLayerLayers)

        # remove previous items
        self.dlg.ui.liLoginFilteredLayerFields.clear()
        # populate the columns combo box
        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                provider = layer.dataProvider()
                fields = provider.fields()
                for field in fields:
                    self.dlg.ui.liLoginFilteredLayerFields.addItem(
                        unicode(field.name()),
                        unicode(field.name())
                    )           
        else:
            return None


    def addLayerToLocateByLayer(self):
        '''Add a layer in the list of layers 
        for which to have the "locate by layer" tool'''
        
        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLocateByLayerLayers)
        if not layer:
            return False
        
        # Check that the chosen layer is checked in the WFS Capabilities (OWS tab)
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]
        hasWfsOption = False
        for l in wfsLayersList:
            if layer.id() == l:
                hasWfsOption = True
        if not hasWfsOption:
            QMessageBox.critical(
                self.dlg, 
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "ui.msg.warning.locateByLayer.notInWfs"), 
                QMessageBox.Ok)
            return False
          
        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fieldCombobox = self.dlg.ui.liLocateByLayerFields
        fieldName = fieldCombobox.currentText()
        displayGeom = str(self.dlg.ui.cbLocateByLayerDisplayGeom.isChecked())
        lblTableWidget = self.dlg.ui.twLocateByLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 3:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(4)
                       
            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add field name to the line
            newItem = QTableWidgetItem(fieldName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add displayGeom option to the line
            newItem = QTableWidgetItem(displayGeom)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
        lblTableWidget.setColumnHidden(3, True)
         

    def removeLayerFromLocateByLayer(self):
        '''Remove a layer from the list of layers 
        for which to have the "locate by layer" tool'''
        lblTableWidget = self.dlg.ui.twLocateByLayerList
        lblTableWidget.removeRow(lblTableWidget.currentRow())



    def addLayerToEditionLayer(self):
        '''Add a layer in the list of edition layers'''
        
        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liEditionLayer)
        if not layer:
            return False
        
        # Retrieve layer information        
        layerName = layer.name()
        layerId = layer.id()
        createFeature = str(self.dlg.ui.cbEditionLayerCreate.isChecked())
        modifyAttribute = str(self.dlg.ui.cbEditionLayerModifyAttribute.isChecked())
        modifyGeometry = str(self.dlg.ui.cbEditionLayerModifyGeometry.isChecked())
        deleteFeature = str(self.dlg.ui.cbEditionLayerDeleteFeature.isChecked())
        lblTableWidget = self.dlg.ui.twEditionLayerList
        
        # check at least one checkbox is active
        if not self.dlg.ui.cbEditionLayerCreate.isChecked() \
        and not self.dlg.ui.cbEditionLayerModifyAttribute.isChecked() \
        and not self.dlg.ui.cbEditionLayerModifyGeometry.isChecked() \
        and not self.dlg.ui.cbEditionLayerDeleteFeature.isChecked():
            return False
           
        # count table widget lines
        twRowCount = lblTableWidget.rowCount()
        
        # check if layer already added
        if twRowCount > 0:
            for row in range(twRowCount):
                itemLayerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                if layerId == itemLayerId:
                    return False    
        
        # Add layer
        if twRowCount < 5:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(6)
                       
            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # create feature
            newItem = QTableWidgetItem(createFeature)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # modify attributes
            newItem = QTableWidgetItem(modifyAttribute)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # modify geometry
            newItem = QTableWidgetItem(modifyGeometry)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # delete feature
            newItem = QTableWidgetItem(deleteFeature)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 5, newItem)
        lblTableWidget.setColumnHidden(5, True)
         

    def removeLayerFromEditionLayer(self):
        '''Remove a layer from the list of edition layers '''
        lblTableWidget = self.dlg.ui.twEditionLayerList
        lblTableWidget.removeRow(lblTableWidget.currentRow())


    def addLayerToLoginFilteredLayer(self):
        '''Add a layer in the list of layers 
        for which to have the "login filtered layer" tool'''
        
        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLoginFilteredLayerLayers)
        if not layer:
            return False
          
        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fieldCombobox = self.dlg.ui.liLoginFilteredLayerFields
        filterAttribute = fieldCombobox.currentText()
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 3:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(3)
                       
            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add field name to the line
            newItem = QTableWidgetItem(filterAttribute)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
        lblTableWidget.setColumnHidden(2, True)
         

    def removeLayerFromLoginFilteredLayer(self):
        '''Remove a layer from the list of layers 
        for which to have the "login filtered layer" tool'''
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        lblTableWidget.removeRow(lblTableWidget.currentRow())


    def refreshLayerTree(self):
        '''Refresh the layer tree on user demand. Uses method populateLayerTree'''
        # Ask confirmation
        refreshIt = QMessageBox.question(
            self.dlg,
            QApplication.translate("lizmap", 'ui.msg.question.refresh.title'),
            QApplication.translate("lizmap", "ui.msg.question.refresh.content"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if refreshIt == QMessageBox.Yes:
            self.populateLayerTree()

    def setTreeItemData(self, itemType, itemKey, jsonLayers):
        '''Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        '''
        # Type : group or layer
        self.myDic[itemKey]['type'] = itemType

        # DEFAULT VALUES : generic default values for layers and group
        self.myDic[itemKey]['name'] = "%s" % itemKey
        for key, item in self.layerOptionsList.items():
            self.myDic[itemKey][key] = item['default']
        self.myDic[itemKey]['title'] = self.myDic[itemKey]['name']

        # DEFAULT VALUES : layers have got more precise data
        keepMetadata = False
        if itemType == 'layer':
            # layer name
            layer = self.getQgisLayerById(itemKey)
            lname = '%s' % layer.name()
            self.myDic[itemKey]['name'] = layer.name()
            # title and abstract
            self.myDic[itemKey]['title'] = layer.name()
            if hasattr(layer, "title"): # only from qgis>=1.8
                if layer.title():
                    self.myDic[itemKey]['title'] = layer.title()
                    keepMetadata = True
                if layer.abstract():
                    self.myDic[itemKey]['abstract'] = layer.abstract()
                    keepMetadata = True
            # hide non geo layers (csv, etc.)
            if layer.type() == 0:
                if layer.geometryType() == 4:
                    self.ldisplay = False
            # layer scale visibility
            if layer.hasScaleBasedVisibility():
                self.myDic[itemKey]['minScale'] = layer.minimumScale()
                self.myDic[itemKey]['maxScale'] = layer.maximumScale()
            # toggled : check if layer is toggled in qgis legend
            self.myDic[itemKey]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
            # group as layer : always False obviously because it is already a layer
            self.myDic[itemKey]['groupAsLayer'] = False

        # OVERRIDE DEFAULT FROM CONFIGURATION FILE
        if jsonLayers.has_key('%s' % self.myDic[itemKey]['name']):
            jsonKey = '%s' % self.myDic[itemKey]['name']
            # loop through layer options to override
            for key, item in self.layerOptionsList.items():
                # override only for ui widgets
                if item['widget']:
                    if jsonLayers[jsonKey].has_key(key):
                        # checkboxes
                        if item['wType'] == 'checkbox':
                            if jsonLayers[jsonKey][key].lower() in ('yes', 'true', 't', '1'):
                                self.myDic[itemKey][key] = True
                            else:
                                self.myDic[itemKey][key] = False
                        # spin box
                        elif item['wType'] == 'spinbox':
                            if jsonLayers[jsonKey][key] != '':
                                self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                        # text inputs
                        elif item['wType'] in ('text', 'textarea'):
                            if jsonLayers[jsonKey][key] != '':
                                if item.has_key('isMetadata'): # title and abstract
                                    if not keepMetadata:
                                        self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                                else:
                                    self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                        # lists
                        elif item['wType'] == 'list':
                            if jsonLayers[jsonKey][key] in item['list']:
                                self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                # popupContent
                if key == 'popupTemplate':
                    if jsonLayers[jsonKey].has_key(key):
                        self.myDic[itemKey][key] = jsonLayers[jsonKey][key]


    def populateLayerTree(self):
        '''Populate the layer tree of the Layers tab from Qgis legend interface
        Needs to be refactored.
        '''

        # initialize the tree
        myTree = self.dlg.ui.treeLayer
        myTree.clear()
        myTree.headerItem().setText(0, QApplication.translate("lizmap", QApplication.translate("lizmap", "layers.tree.title")))
        self.myDic = {}
        myGroups = self.iface.legendInterface().groups()

        # Check if a json configuration file exists (myproject.qgs.cfg)
        isok = 1
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        jsonLayers = {}
        if os.path.exists(unicode(jsonFile)):
            f = open(jsonFile, 'r')
            jsonFileReader = f.read()
            try:
                sjson = json.loads(jsonFileReader)
                jsonLayers = sjson['layers']
            except:
                isok=0
                QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), (u""), QMessageBox.Ok)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
            f.close()

#        # Loop through groupLayerRelationship to reconstruct the tree
        for a in self.iface.legendInterface().groupLayerRelationship():
            # Initialize values
            parentItem = None
            myId = a[0]

            # Select an existing item, select the header item or create the item
            if myId in self.myDic:
                # If the item already exists in self.myDic, select it
                parentItem = self.myDic[myId]['item']
            elif myId == '':
                # If the id is empty string, this is a root layer, select the headerItem
                parentItem = myTree.headerItem()
            else:
                # else create the item and add it to the header item
                # add the item to the dictionary
                self.myDic[myId] = {'id' : myId}
                self.ldisplay = True
                if myId in myGroups:
                    # it is a group
                    self.setTreeItemData('group', myId, jsonLayers)
                else:
                    # it is a layer
                    self.setTreeItemData('layer', myId, jsonLayers)

                if self.ldisplay:
                    parentItem = QTreeWidgetItem(['%s' % unicode(self.myDic[myId]['name']), '%s' % unicode(self.myDic[myId]['id']), '%s' % self.myDic[myId]['type']])
                    myTree.addTopLevelItem(parentItem)
                    self.myDic[myId]['item'] = parentItem
                else:
                    del self.myDic[myId]

            # loop through the children and add children to the parent item
            for b in a[1]:
                self.myDic[b] = {'id' : b}
                self.ldisplay = True
                if b in myGroups:
                    # it is a group
                    self.setTreeItemData('group', b, jsonLayers)
                else:
                    # it is a layer
                    self.setTreeItemData('layer', b, jsonLayers)

                # add children item to its parent
                if self.ldisplay:
                    childItem = QTreeWidgetItem(['%s' % unicode(self.myDic[b]['name']), '%s' % unicode(self.myDic[b]['id']), '%s' % self.myDic[b]['type']])
                    if myId == '':
                        myTree.addTopLevelItem(childItem)
                    else:
                        parentItem.addChild(childItem)
                    self.myDic[b]['item'] = childItem
                else:
                    del self.myDic[b]

        myTree.expandAll()

        # Add the self.myDic to the global layerList dictionary
        self.layerList = self.myDic

        self.enableCheckBox(False)

    def setItemOptions(self):
        '''Restore layer/group input values when selecting a layer tree item'''
        # get the selected item
        item = self.dlg.ui.treeLayer.currentItem()
        if item:
            self.enableCheckBox(True)
        else:
            self.enableCheckBox(False)

        if self.layerList.has_key(item.text(1)):
            # get information about the layer or the group from the layerList dictionary
            selectedItem = self.layerList[item.text(1)]

            # set options
            for key,val in self.layerOptionsList.items():
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(selectedItem[key])
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(int(selectedItem[key]))
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(selectedItem[key])
                    elif val['wType'] == 'list':
                        listDic = {val['list'][i]:i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[selectedItem[key]])
            # deactivate popup configuration for groups
            isLayer = selectedItem['type'] == 'layer'
            self.dlg.ui.btConfigurePopup.setEnabled(isLayer)
#            self.dlg.ui.cbPopup.setEnabled(isLayer)
#            if not isLayer:
#                self.dlg.ui.cbPopup.setChecked(False)
        else:
            # set default values for this layer/group
            for key,val in self.layerOptionsList.items():
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(val['default'])
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':
                        listDic = {val['list'][i]:i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[val['default']])


    def setLayerProperty(self, key, *args):    
        '''
            Set a layer property in global self.layerList 
            when the corresponding ui widget has sent changed signal
        '''
        key = str(key)
        # get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        # get the definition for this property
        layerOption = self.layerOptionsList[key]
        # modify the property for the selected item
        if item and self.layerList.has_key(item.text(1)):
            if layerOption['wType'] == 'text':
                self.layerList[item.text(1)][key] = layerOption['widget'].text()
                self.setLayerMeta(item, key)
            elif layerOption['wType'] == 'textarea':
                self.layerList[item.text(1)][key] = layerOption['widget'].toPlainText()
                self.setLayerMeta(item, key)
            elif layerOption['wType'] == 'spinbox':
                self.layerList[item.text(1)][key] = layerOption['widget'].value()
            elif layerOption['wType'] == 'checkbox':
                self.layerList[item.text(1)][key] = layerOption['widget'].isChecked()
            elif layerOption['wType'] == 'list':
                self.layerList[item.text(1)][key] = layerOption['list'][layerOption['widget'].currentIndex()]
            
            # Deactivate the "exclude" widget if necessary
            if (layerOption.has_key('exclude')
                and layerOption['wType'] == 'checkbox'
                and layerOption['widget'].isChecked()
                and layerOption['exclude']['widget'].isChecked()
            ):
                layerOption['exclude']['widget'].setChecked(False)
                self.layerList[item.text(1)][layerOption['exclude']['key']] = False
                
                

    def setLayerMeta(self, item, key):
        '''Set a the title/abstract Qgis metadata when corresponding item is changed
        Used in setLayerProperty'''
        if self.layerOptionsList[key].has_key('isMetadata'):
            # modify the layer.title|abstract() if possible (qgis >= 1.8)
            if self.layerList[item.text(1)]['type'] == 'layer':
                layer = self.getQgisLayerById(item.text(1))
                if layer:
                    if hasattr(layer, key):
                        if key == 'title':
                            layer.setTitle(u"%s" % self.layerList[item.text(1)][key])
                        if key == 'abstract':
                            layer.setAbstract(u"%s" % self.layerList[item.text(1)][key])


    def configurePopup(self):
        '''Open the dialog with a text field to store the popup template for one layer/group'''
        # get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        if item and self.layerList.has_key(item.text(1)):
            # do nothing if no popup configured for this layer/group
            if self.layerList[item.text(1)]['popup'] == 'False':
                return False

            # Import the code for the dialog
            from lizmappopupdialog import lizmapPopupDialog
            self.lizmapPopupDialog = lizmapPopupDialog()
            
            self.lizmapPopupDialog.ui.groupBox.setStyleSheet(self.STYLESHEET)
            self.lizmapPopupDialog.ui.groupBox_2.setStyleSheet(self.STYLESHEET)

            # Connect popup dialog signals and slots
            # When the plain text template is modified
            self.lizmapPopupDialog.ui.txtPopup.textChanged.connect(self.updatePopupHtml)
            # When the ui is closed with the x
            self.lizmapPopupDialog.rejected.connect(self.popupNotConfigured)
            # When the ui is closed with the OK button
            self.lizmapPopupDialog.ui.bbConfigurePopup.accepted.connect(self.popupConfigured)
            # When the ui is closed with the CANCEL button
            self.lizmapPopupDialog.ui.bbConfigurePopup.rejected.connect(self.popupNotConfigured)

            # Set the content of the QTextEdit if needed
            if self.layerList[item.text(1)].has_key('popupTemplate'):
                self.layerList[item.text(1)]['popup'] = True
                self.lizmapPopupDialog.ui.txtPopup.setPlainText(self.layerList[item.text(1)]['popupTemplate'])
                self.lizmapPopupDialog.ui.htmlPopup.setHtml(self.layerList[item.text(1)]['popupTemplate'])

            # Show the popup configuration window
            self.lizmapPopupDialog.show()

    def updatePopupHtml(self):
        '''Update the html preview of the popup dialog from the plain text template text'''
        # Get the content
        popupContent = unicode(self.lizmapPopupDialog.ui.txtPopup.toPlainText())

        # Update html preview
        self.lizmapPopupDialog.ui.htmlPopup.setHtml(popupContent)

    def popupConfigured(self):
        '''Save the content of the popup template'''
        # Get the content before closing the dialog
        popupContent = unicode(self.lizmapPopupDialog.ui.txtPopup.toPlainText())

        # Close the popup dialog
        self.lizmapPopupDialog.close()

        # Get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        if item and self.layerList.has_key(item.text(1)):
            # Write the content into the global object
            self.layerList[item.text(1)]['popupTemplate'] = popupContent


    def popupNotConfigured(self):
        '''Popup configuration dialog has been close with cancel or x : do nothing'''
        self.lizmapPopupDialog.close()



    def writeProjectConfigFile(self):
        '''Get general project options and user edited layers options from plugin gui. Save them into the project.qgs.cfg config file in the project.qgs folder (json format)'''
        myJson = '{'

        # get information from Qgis api
        r = QgsMapRenderer()
        # add all the layers to the renderer
        r.setLayerSet([a.id() for a in self.iface.legendInterface().layers()])
        # Get the project data
        p = QgsProject.instance()
        # options
        liz2json = {}
        liz2json["options"] = {}
        liz2json["layers"] = {}
        # projection
        # project projection
        mc = self.iface.mapCanvas()
        pCrs = mc.mapRenderer().destinationCrs()
        pAuthid = pCrs.authid()
        pProj4 = pCrs.toProj4()
        liz2json["options"]["projection"] = {}
        liz2json["options"]["projection"]["proj4"] = '%s' % pProj4
        liz2json["options"]["projection"]["ref"] = '%s' % pAuthid
        # wms extent
        pWmsExtent = p.readListEntry('WMSExtent','')[0]
        if len(pWmsExtent) > 1:
            bbox = eval('[%s, %s, %s, %s]' % (pWmsExtent[0],pWmsExtent[1],pWmsExtent[2],pWmsExtent[3]))
        else:
            bbox = []
        liz2json["options"]["bbox"] = bbox

        # gui user defined options
        for key, item in self.globalOptions.items():
            if item['widget']:
                inputValue = None
                
                # Get field value depending on widget type
                if item['wType'] == 'text':
                    inputValue = str(item['widget'].text()).strip(' \t')

                if item['wType'] == 'textarea':
                    inputValue = str(item['widget'].toPlainText()).strip(' \t')
                    
                if item['wType'] == 'spinbox':
                    inputValue = item['widget'].value()
                
                if item['wType'] == 'checkbox':
                    inputValue = str(item['widget'].isChecked())
                    
                if item['wType'] == 'list':
                    listDic = {item['list'][i]:i for i in range(0, len(item['list']))}
                    inputValue = item['list'][item['widget'].currentIndex()]
                
                # Cast value depending of data type
                if item['type'] == 'string':
                    if item['wType'] in ('text', 'textarea'):
                        inputValue = unicode(inputValue)
                    else:
                        inputValue = str(inputValue)
                elif item['type'] in ('intlist', 'list'):
                    if item['type'] == 'intlist':
                        inputValue = [int(a) for a in inputValue.split(', ') if a.isdigit()]
                    else:
                        inputValue = [a for a in inputValue.split(', ')]
                    inputValue.sort()
                elif item['type'] == 'integer':
                    try:
                        inputValue = int(inputValue)
                    except:
                        inputValue = int(item['default'])
                elif item['type'] == 'boolean':
                    inputValue = str(inputValue)
                               
                # Add value to the option
                if (inputValue and inputValue != "False"):
                    liz2json["options"][key] = inputValue
                else:
                    if item.has_key('alwaysExport'):
                        liz2json["options"][key] = item['default']
                
       
        # list of layers for which to have the tool "locate by layer"
        lblTableWidget = self.dlg.ui.twLocateByLayerList
        twRowCount = lblTableWidget.rowCount()
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]        
        if twRowCount > 0:
            liz2json["locateByLayer"] = {}    
            for row in range(twRowCount):                   
                # check that the layer is checked in the WFS capabilities
                layerId = str(lblTableWidget.item(row, 3).text())
                if layerId in wfsLayersList:
                    layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                    fieldName = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                    displayGeom = str(lblTableWidget.item(row, 2).text())
                    layerId = str(lblTableWidget.item(row, 3).text().encode('utf-8'))
                    liz2json["locateByLayer"][layerName] = {}
                    liz2json["locateByLayer"][layerName]["fieldName"] = fieldName
                    liz2json["locateByLayer"][layerName]["displayGeom"] = displayGeom
                    liz2json["locateByLayer"][layerName]["layerId"] = layerId
                    
        # layer(s) for the edition tool
        lblTableWidget = self.dlg.ui.twEditionLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["editionLayers"] = {}
            for row in range(twRowCount):                   
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                createFeature = str(lblTableWidget.item(row, 1).text())
                modifyAttribute = str(lblTableWidget.item(row, 2).text())
                modifyGeometry = str(lblTableWidget.item(row, 3).text())
                deleteFeature = str(lblTableWidget.item(row, 4).text())
                layerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                layer = self.getQgisLayerById(layerId)
                geometryType = self.mapQgisGeometryType[layer.geometryType()]
                liz2json["editionLayers"][layerName] = {}
                liz2json["editionLayers"][layerName]["layerId"] = layerId
                liz2json["editionLayers"][layerName]["geometryType"] = geometryType
                liz2json["editionLayers"][layerName]["capabilities"] = {}
                liz2json["editionLayers"][layerName]["capabilities"]["createFeature"] = createFeature
                liz2json["editionLayers"][layerName]["capabilities"]["modifyAttribute"] = modifyAttribute
                liz2json["editionLayers"][layerName]["capabilities"]["modifyGeometry"] = modifyGeometry
                liz2json["editionLayers"][layerName]["capabilities"]["deleteFeature"] = deleteFeature
                

        # list of layers for which to have the tool "login filtered layer"
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        twRowCount = lblTableWidget.rowCount()     
        if twRowCount > 0:
            liz2json["loginFilteredLayers"] = {}    
            for row in range(twRowCount):                   
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                filterAttribute = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                layerId = str(lblTableWidget.item(row, 2).text().encode('utf-8'))
                liz2json["loginFilteredLayers"][layerName] = {}
                liz2json["loginFilteredLayers"][layerName]["filterAttribute"] = filterAttribute
                liz2json["loginFilteredLayers"][layerName]["layerId"] = layerId

        # gui user defined layers options
        for k,v in self.layerList.items():
            addToCfg = True
            ltype = v['type']
            gal = v['groupAsLayer']
            geometryType = -1
            if gal:
                ltype = 'layer'
            else:
                ltype = 'group'
            if self.getQgisLayerById(k):
                ltype = 'layer'
                gal = True
            if ltype == 'layer':
                layer = self.getQgisLayerById(k)
                if layer:
                    if layer.type() == 0: # if it is a vector layer
                        geometryType = layer.geometryType()

            # add layerOption only for geo layers
            if geometryType != 4:
                layerOptions = {}
                layerOptions["id"] = unicode(k)
                layerOptions["name"] = unicode(v['name'])
                layerOptions["type"] = ltype

                # Loop through the layer options and set properties from the dictionary
                for key, val in self.layerOptionsList.items():
                    propVal = v[key]
                    if val['type'] == 'string':
                        if val['wType'] in ('text', 'textarea'):
                            propVal = unicode(propVal)
                        else:
                            propVal = str(propVal)
                    elif val['type'] == 'integer':
                        propVal = int(propVal)
                    elif val['type'] == 'boolean':
                        propVal = str(propVal)
                    layerOptions[key] = propVal

                # Cache Metatile: unset metatileSize if empty
                # this is to avoid, but lizmap web client must change accordingly to avoid using empty metatileSize (2.2.0 does not handle it)
                import re
                p = re.compile('ab*')
                # unset metatileSize
                if not re.match('\d,\d', layerOptions['metatileSize']):
                    del layerOptions['metatileSize']
                # unset cacheExpiration if False
                if layerOptions['cached'].lower() == 'false':
                    del layerOptions['cacheExpiration']
                # unset popupTemplate if popup False
                if layerOptions['popup'].lower() == 'false':
                    del layerOptions['popupTemplate']
                # unset clientCacheExpiration if needed
                if layerOptions['clientCacheExpiration'] < 0:
                    del layerOptions['clientCacheExpiration']

                liz2json["layers"]["%s" % unicode(v['name'])] = layerOptions

        # Write json to the cfg file
        jsonFileContent = json.dumps(
            liz2json,
            sort_keys=True,
            indent=4
        )

        # Get the project data
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        f = open(jsonFile, 'w')
        f.write(jsonFileContent.encode('utf-8'))
        f.close()




    def checkGlobalProjectOptions(self):
        ''' Checks that the needed options are correctly set : relative path, project saved, etc.'''

        isok = True;
        errorMessage = ''
        # Get the project data from api
        p = QgsProject.instance()
        if not p.fileName():
            errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.init.open.project")+'\n'
            isok = False

        # Check the project state (saved or not)
        if isok and p.isDirty():
            saveIt = QMessageBox.question(self.dlg, QApplication.translate("lizmap", "ui.msg.question.save.project.title"), QApplication.translate("lizmap", "ui.msg.question.save.project.content"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if saveIt == QMessageBox.Yes:
                p.write()
            else:
                isok = False

        if isok:
            # Get the project folder
            projectDir, projectName = os.path.split(os.path.abspath('%s' % p.fileName()))
            self.dlg.ui.inLocaldir.setText(projectDir)

        if isok:
            # Check relative/absolute path
            if p.readEntry('Paths', 'Absolute')[0] == 'true':
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.option.path.relative")+'\n'
                isok = False

            # check active layers path layer by layer
            layerSourcesOk = []
            layerSourcesBad = []
            mc = self.iface.mapCanvas()
            layerPathError = ''
            
            for i in range(mc.layerCount()):
                layerSource =    unicode('%s' % mc.layer( i ).source() )  
                layerProviderKey = mc.layer( i ).providerType()
                # Only for layers stored in disk
                if layerProviderKey in ('delimitedtext', 'gdal', 'gpx', 'grass', 'grassraster', 'ogr'):
                    try:
                        relativePath = os.path.normpath(
                            os.path.relpath(os.path.abspath(layerSource), projectDir)
                        )
                        if not relativePath.startswith('../../') and not relativePath.startswith('..\\..\\'):
                            layerSourcesOk.append(os.path.abspath(layerSource))
                        else:
                            layerSourcesBad.append(layerSource)
                            layerPathError+='--> %s \n' % relativePath
                            isok = False                        
                    except:
                        isok = False
                        layerSourcesBad.append(layerSource)
                        layerPathError+='--> %s \n' % mc.layer( i ).name()                        


                    
                    
            if len(layerSourcesBad) > 0:
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative {}").format(projectDir)+'\n'
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative {}")
                    .format(projectDir) + str(layerSourcesBad),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
                errorMessage+= layerPathError

            # check if a title has been given in the project OWS tab configuration
            # first set the WMSServiceCapabilities to true
            p.writeEntry('WMSServiceCapabilities', "/", "True")
            p.write()
            if p.readEntry('WMSServiceTitle','')[0] == u'':
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.wms.title")+'\n'
                isok = False


            # check if a bbox has been given in the project OWS tab configuration
            pWmsExtent = p.readListEntry('WMSExtent','')[0]
            if len(pWmsExtent) < 1 :
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.wms.extent")+'\n'
                isok = False
            else:
                if not pWmsExtent[0] or not pWmsExtent[1] or not pWmsExtent[2] or not pWmsExtent[3]:
                    errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.wms.extent")+'\n'
                    isok = False

        if not isok and errorMessage:
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                errorMessage,
                QMessageBox.Ok)

        # for linux users, check if lftp has been installed
        if isok and sys.platform.startswith('linux'):
            lftpCheck = u'lftp --version'
            workingDir = os.getcwd()
            proc = subprocess.Popen( lftpCheck, cwd=workingDir, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            output = proc.communicate()
            proc.wait()
            if "LFTP" not in output[0]:
                self.log(
                    QApplication.translate("lizmap", "ui.msg.warning.lftp.installation"),
                    abort=False,
                    textarea=self.dlg.ui.outLog)
                self.dlg.ui.tabWidget.setTabEnabled(3, False)
                self.dlg.ui.btSync.setEnabled(False)

        return isok


    def getMapOptions(self):
        '''Check the user defined data from gui and save them to both global and project config files'''
        self.isok = 1
        # global project option checking
        isok = self.checkGlobalProjectOptions()

        if isok:
            # Get configuration from input fields
            
            # Need to get theses values to check for Pseudo Mercator projection            
            in_osmMapnik = self.dlg.ui.cbOsmMapnik.isChecked()
            in_osmMapquest = self.dlg.ui.cbOsmMapquest.isChecked()
            in_googleStreets = self.dlg.ui.cbGoogleStreets.isChecked()
            in_googleSatellite = self.dlg.ui.cbGoogleSatellite.isChecked()
            in_googleHybrid = self.dlg.ui.cbGoogleHybrid.isChecked()
            in_googleTerrain = self.dlg.ui.cbGoogleTerrain.isChecked()
            
            isok = True

            # log
            self.dlg.ui.outLog.append('=' * 20)
            self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.map.option.title"))
            self.dlg.ui.outLog.append('=' * 20)

            # Checking configuration data
            # Get the project data from api to check the "coordinate system restriction" of the WMS Server settings
            p = QgsProject.instance()

            # public baselayers: check that the 3857 projection is set in the "Coordinate System Restriction" section of the project WMS Server tab properties
            if in_osmMapnik or in_osmMapquest or in_googleStreets or in_googleSatellite or in_googleHybrid or in_googleTerrain:
                good = False
                for i in p.readListEntry('WMSCrsList','')[0]:
                    if i == 'EPSG:3857':
                        good = True
                if not good:
                    self.log(
                        QApplication.translate("lizmap", "log.map.externalBaseLayers.warning"),
                        abort=True,
                        textarea=self.dlg.ui.outLog)
                        
                

            # list of layers for which to have the tool "locate by layer" set
            lblTableWidget = self.dlg.ui.twLocateByLayerList
            twRowCount = lblTableWidget.rowCount()
            wfsLayersList = p.readListEntry('WFSLayers','')[0]
            if twRowCount > 0:
                good = True
                for row in range(twRowCount):                   
                    # check that the layer is checked in the WFS capabilities
                    layerId = str(lblTableWidget.item(row, 3).text())
                    if layerId not in wfsLayersList:
                        good = False
                if not good:
                    self.log(
                        QApplication.translate("lizmap", "ui.msg.warning.locateByLayer.notInWfs"),
                        abort=True,
                        textarea=self.dlg.ui.outLog)
                        

            if self.isok:
                # write data in the QgisWebClient json config file (to be send with the project file)
                self.writeProjectConfigFile()
                self.log(
                    QApplication.translate("lizmap", "ui.msg.map.parameters.ok"),
                    abort=False,
                    textarea=self.dlg.ui.outLog)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.configuration.save.ok"),
                    abort=False,
                    textarea=self.dlg.ui.outLog)
            else:
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.map.parameters.bad"),
                    QMessageBox.Ok)

            self.dlg.ui.outState.setText('<font color="green"></font>')
            # Go to Log tab
            self.dlg.ui.tabWidget.setCurrentIndex(4)
            
            # Get and check map scales
            if self.isok:
                self.getMinMaxScales()

        return self.isok



    def chooseWinscpPath(self):
        '''Ask the user to select a folder and write down the path to inWinscpPath field'''
        winscpPath = QFileDialog.getExistingDirectory( None,"Choose the folder where WinScp portable is installed", str(self.dlg.ui.inWinscpPath.text().encode('utf-8')).strip(' \t') )
        if os.path.exists(unicode(winscpPath)):
            self.dlg.ui.inWinscpPath.setText(unicode(winscpPath))
            if not os.path.exists(os.path.join(os.path.abspath('%s' % winscpPath), 'WinSCP.com')):
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.error.winscp.not.found {}")
                    .format(os.path.abspath('%s' % winscpPath)),
                    QMessageBox.Ok)


    def getFtpOptions(self):
        '''Get and check FTP options defined by user. Returns FTP options'''
        # Get FTP options
        in_username = str(self.dlg.ui.inUsername.text()).strip(' \t')
        in_password = str(self.dlg.ui.inPassword.text()).strip(' \t')
        in_host = str(self.dlg.ui.inHost.text()).strip(' \t')
        in_port = str(self.dlg.ui.inPort.text()).strip(' \t')
        in_localdir = str(self.dlg.ui.inLocaldir.text().encode('utf-8')).strip(' \t')
        in_remotedir = str(self.dlg.ui.inRemotedir.text().encode('utf-8')).strip(' \t')
        in_winscpPath = str(self.dlg.ui.inWinscpPath.text().encode('utf-8')).strip(' \t')
        in_winscpSession = str(self.dlg.ui.inWinscpSession.text().encode('utf-8')).strip(' \t')
        in_winscpCriteria = str(self.dlg.ui.inWinscpCriteria.text().encode('utf-8')).strip(' \t')

        self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.ftp.option.title"))
        self.dlg.ui.outLog.append('=' * 20)
        self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.ftp.option.title"))
        self.dlg.ui.outLog.append('=' * 20)

        # Check FTP options
        # host
        if len(in_host) == 0:
            host = ''
            self.log(
                QApplication.translate("lizmap", "log.ftp.hostname.missing.warning"),
                abort=True,
                textarea=self.dlg.ui.outLog)
        elif len(in_host) < 4:
            host=''
            self.log(
                QApplication.translate("lizmap", "log.ftp.hostname.wrong.warning {}")
                .format(in_host),
                abort=True,
                textarea=self.dlg.ui.outLog)
        else:
            host = unicode(in_host)
            self.log('host = %s' % host, abort=False, textarea=self.dlg.ui.outLog)

        # port
        port = 21
        if len(in_port) > 0:
            try:
                port = int(in_port)
            except (ValueError, IndexError):
                port = 21
                self.dlg.ui.inPort.setText('21')

        self.log('port = %d' % port, abort=False, textarea=self.dlg.ui.outLog)

        # remote directory
        if len(in_remotedir) > 0:
            remotedir = in_remotedir
            if not str(remotedir).startswith('/'):
                remotedir = '/' + remotedir
            if str(remotedir).endswith('/'):
                remotedir = remotedir.rstrip('/')
            self.log('remotedir = %s' % remotedir, abort=False, textarea=self.dlg.ui.outLog)
        else:
            remotedir=''
            self.log(
                QApplication.translate("lizmap", "log.ftp.remotedir.missing.warning"),
                abort=True,
                textarea=self.dlg.ui.outLog)

        # local directory
        localdir = in_localdir
        if not str(localdir).endswith('/'):
            localdir = localdir + '/'
        if not os.path.isdir(localdir):
            localdir=''
            self.log(
                QApplication.translate("lizmap", "log.ftp.localdir.warning %1")
                .arg(localdir),
                abort=True,
                textarea=self.dlg.ui.outLog)
        else:
            self.log('localdir = %s' % localdir, abort=False, textarea=self.dlg.ui.outLog)

        # For windows users : winscp path
        if sys.platform == 'win32':
            winscpPath = in_winscpPath
            #if not str(winscpPath).endswith('/'):
            #    winscpPath = winscpPath + '/'
            if not os.path.exists(os.path.join(os.path.abspath('%s' % winscpPath), 'WinSCP.com') ):
                self.log(
                    QApplication.translate("lizmap", "log.ftp.winscpPath.warning {}")
                    .format(winscpPath),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
                winscpPath=''
            else:
                self.log('winscp path = %s' % winscpPath, abort=False, textarea=self.dlg.ui.outLog)
                
            winscpSession = in_winscpSession
            winscpCriteria = in_winscpCriteria
            if not winscpCriteria in ('time', 'size'):
                winscpCriteria = 'time'
            
        else:
            winscpPath = ''
            winscpSession = ''
            winscpCriteria = ''

        # username
        if len(in_username) > 0:
            username = unicode(in_username)
            self.log('username = %s' % username, abort=False, textarea=self.dlg.ui.outLog)
        else:
            username=''
            self.log(
                QApplication.translate("lizmap", "log.ftp.username.missing.warning"),
                abort=True,
                textarea=self.dlg.ui.outLog)

        # password
        if len(in_password) > 0:
            password = unicode(in_password)
            self.log('password ok', abort=False, textarea=self.dlg.ui.outLog)
        else:
            password=''
            if not in_winscpSession:
                self.log(
                    QApplication.translate("lizmap", "log.ftp.password.missing.warning"),
                    abort=True,
                    textarea=self.dlg.ui.outLog)

        if self.isok:
            # write FTP options data in the python plugin config file
            cfg = ConfigParser.ConfigParser()
            configPath = os.path.join( self.plugin_dir, "lizmap.cfg")
            cfg.read(configPath)
            cfg.set('Ftp', 'host', host)
            cfg.set('Ftp', 'username', username)
            cfg.set('Ftp', 'port', port)
            cfg.set('Ftp', 'winscppath', winscpPath)
            cfg.set('Ftp', 'winscpSession', winscpSession)
            cfg.set('Ftp', 'winscpCriteria', winscpCriteria)
            cfg.write(open(configPath,"w"))
            cfg.read(configPath)
            # log the errors
            self.log(
                QApplication.translate("lizmap", "ui.msg.ftp.parameters.ok"),
                abort=False,
                textarea=self.dlg.ui.outLog)
        else:
            self.log(
                QApplication.translate("lizmap", "ui.msg.ftp.parameters.bad"),
                abort=True,
                textarea=self.dlg.ui.outLog)
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "ui.msg.ftp.parameters.bad"),
                QMessageBox.Ok)

        return [self.isok, host, port, username, password, localdir, remotedir, winscpPath, winscpSession, winscpCriteria]


    def ftpSyncStdout(self):
        '''Get the ftp sync process Stdout and append it to the log textarea'''
        data = self.proc.readAllStandardOutput()
        output = data.decode('utf-8')
        self.dlg.ui.outLog.append(output)

    def ftpSyncError(self):
        '''Get the ftp sync process Error and append it to the log textarea'''
        data = self.proc.readAllStandardError()
        output = data.decode('utf-8')
        self.dlg.ui.outLog.append(output)

    def ftpSyncFinished(self):
        '''Loaded when the sync process has finished its job.'''
        if self.proc.exitStatus() == 0:
            self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.sync.completed"))
            self.dlg.ui.outState.setText(QApplication.translate("lizmap", "log.outState.completed"))
        else:
            self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.sync.canceled"))
            self.dlg.ui.outState.setText(QApplication.translate("lizmap", "log.outState.canceled"))


    def ftpSyncCancel(self):
        '''Cancel the ftp sync process by killing it'''
        # Ask for confirmation
        letsGo = QMessageBox.question(
            self.dlg,
            QApplication.translate("lizmap", "ui.msg.warning.title"),
            QApplication.translate("lizmap", "log.kill.warning"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if letsGo == QMessageBox.Yes:
            try:
                self.proc.kill()
            except:
                return False
            return True
        else:
            return False


    def ftpSync(self):
        '''Synchronize data (project file, project config file and all data contained in the project file folder) from local computer to remote host.
        * linux : Based on lftp library which needs to be installed
        * windows : based on winscp portable which needs to be manually downloaded and installed
        * mac : needs to be done
        '''
        # Ask for confirmation
        letsGo = QMessageBox.question(
            self.dlg,
            QApplication.translate("lizmap", "ui.msg.warning.title"),
            QApplication.translate("lizmap", "ui.msg.warning.run.sync {} {}").format(self.dlg.ui.inLocaldir.text(), self.dlg.ui.inRemotedir.text()),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if letsGo == QMessageBox.Yes:
            isok = True
        else:
            isok = False
            return False

        self.isok = 1

        # Check user defined options
        getMapOptions = self.getMapOptions()
        if not getMapOptions:
            return False

        # Check FTP user defined options
        getFtpOptions = self.getFtpOptions()
        if not getFtpOptions[0]:
            return False

        # Go to Log tab
        self.dlg.ui.tabWidget.setCurrentIndex(4)
        time.sleep(1)
        self.dlg.ui.tabWidget.setCurrentIndex(4)

        # Check the platform
        # FTP Sync only active for linux and windows users.
        if not sys.platform.startswith('linux') and sys.platform != 'win32':
            QMessageBox.warning(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.warning.title"),
                QApplication.translate("lizmap", "ui.msg.configuration.saved {} {}")
                .format(localdir, remotedir),
                QMessageBox.Ok)
            return False

        # Get ftp user entered data from getMapOptions()
        host = getFtpOptions[1]
        port = getFtpOptions[2]
        username = getFtpOptions[3]
        password = getFtpOptions[4]
        localdir = getFtpOptions[5]
        remotedir = getFtpOptions[6]
        winscpPath = getFtpOptions[7]
        winscpSession = getFtpOptions[8]
        winscpCriteria = getFtpOptions[9]

        myOutput = ''
        # display the stateLabel
        self.dlg.ui.outState.setText(QApplication.translate("lizmap", "log.outState.running"))
        # setting progressbar refreshes the plygin ui
        self.dlg.ui.outLog.append('')
        self.dlg.ui.outLog.append('=' * 20)
        self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.log.ftp.sync.title"))
        self.dlg.ui.outLog.append('=' * 20)

        # Process the sync with lftp
        if self.isok:
            time_started = datetime.datetime.now()

            if sys.platform.startswith('linux'):
                # construction of ftp sync command line
                ftpStr1 = u'lftp ftp://%s:%s@%s -e "set ssl:verify-certificate no; mirror --verbose -e -R --use-cache %s %s ; quit"' % (username, password, host, localdir.decode('utf-8'), remotedir.decode('utf-8'))
#                self.log(ftpStr1, abort=False, textarea=self.dlg.ui.outLog)
                ftpStr2 = u'lftp ftp://%s:%s@%s -e "set ssl:verify-certificate no; chmod 775 -R %s ; quit"' % (username, password, host, remotedir.decode('utf-8'))

            else:
                winscp = os.path.join(os.path.abspath('%s' % winscpPath.decode('utf-8')), 'WinSCP.com')
                winLocaldir = localdir.replace("/", "\\")
                winLocaldir = winLocaldir.replace("\\", "\\\\")
                # needs to create the directory if not present
                if not winscpSession:
                    ftpStr0 = '"%s" /console /command "option batch off" "option confirm off" "open %s:%s@%s" "option transfer binary" "mkdir %s" "close" "exit"'    % (winscp, username, password, host, remotedir.decode('utf-8'))
                else:
                    ftpStr0 = '"%s" /console /command "option batch off" "option confirm off" "open "%s" "option transfer binary" "mkdir %s" "close" "exit"'    % (winscp, winscpSession, remotedir.decode('utf-8'))
                self.log(ftpStr0, abort=False, textarea=self.dlg.ui.outLog)
                self.proc = QProcess()
                #QObject.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self.ftpSyncStdout)
                QObject.connect(self.proc, SIGNAL("readyReadStandardError()"), self.ftpSyncError)
                QObject.connect(self.proc, SIGNAL("finished(int, QProcess::ExitStatus)"), self.ftpSyncFinished)
                self.proc.start(ftpStr0)
                self.proc.waitForFinished()
                # sync command
                if not winscpSession:
                    ftpStr1 = '"%s" /console /command "option batch off" "option confirm off" "open %s:%s@%s" "option transfer binary" "synchronize remote %s %s -mirror -delete -criteria=%s" "close" "exit"' % (winscp, username, password, host, winLocaldir.decode('utf-8'), remotedir.decode('utf-8'), winscpCriteria)
                else:
                    ftpStr1 = '"%s" /console /command "option batch off" "option confirm off" "open "%s"" "option transfer binary" "synchronize remote %s %s -mirror -delete -criteria=%s" "close" "exit"' % (winscp, winscpSession, winLocaldir.decode('utf-8'), remotedir.decode('utf-8'), winscpCriteria)
                self.log(ftpStr1, abort=False, textarea=self.dlg.ui.outLog)

            # run the ftp sync
            self.proc = QProcess()
            QObject.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self.ftpSyncStdout)
            QObject.connect(self.proc, SIGNAL("readyReadStandardError()"), self.ftpSyncError)
            QObject.connect(self.proc, SIGNAL("finished(int, QProcess::ExitStatus)"), self.ftpSyncFinished)
            self.proc.start(ftpStr1)

            if sys.platform.startswith('linux'):
                # chmod 775 (nb: must find a way to pass the right option to ftpStr1 instead)
                proc = subprocess.Popen( ftpStr2, cwd=os.getcwd(), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.wait()

        return self.isok


    def warnOnClose(self):
        '''Method triggered when the user closes the lizmap dialog by pressing Esc or clicking the x button'''

        self.writeProjectConfigFile()


    def test(self):
        '''Debug method'''
        self.log("test", abort=False, textarea=self.dlg.ui.outLog)
        QMessageBox.critical(self.dlg, "Lizmap debug", (u"test"), QMessageBox.Ok)


    def run(self):
        '''Plugin run method : launch the gui and some tests'''

        if self.dlg.isVisible():
            QMessageBox.warning(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.warning.title"),
                QApplication.translate("lizmap", "ui.msg.warning.window.opened"),
                QMessageBox.Ok)

        # show the dialog only if checkGlobalProjectOptions is true
        if not self.dlg.isVisible() and self.checkGlobalProjectOptions():
            self.dlg.show()
            
            # Fill the layer list for the locate by layer tool
            self.populateLayerCombobox(self.dlg.ui.liLocateByLayerLayers, 'vector')
            # Fill the layers lists for the edition tool
            self.populateLayerCombobox(self.dlg.ui.liEditionLayer, 'vector', ['spatialite', 'postgres'])
            # Fill the layer list for the login filtered layers tool
            self.populateLayerCombobox(self.dlg.ui.liLoginFilteredLayerLayers, 'vector')            

            # Get config file data and set the Ftp Configuration input fields
            self.getConfig()

            self.layerList = {}

            # Fill the layer tree
            self.populateLayerTree()

            self.isok = 1

            result = self.dlg.exec_()
            # See if OK was pressed
            if result == 1:
                QMessageBox.warning(self.dlg, "Debug", ("Quit !"), QMessageBox.Ok)
