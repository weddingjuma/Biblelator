#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleResourceWindows.py
#
# Bible resource windows for Biblelator Bible display/editing
#
# Copyright (C) 2013-2017 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Windows and frames to allow display and manipulation of
    (non-editable) Bible resource windows.

class BibleResourceWindow( BibleWindow )
    __init__( self, parentApp, windowType, moduleID )
    createMenuBar( self )
    changeBibleContextView( self )
    changeBibleGroupCode( self )
    doGotoPreviousBook( self, gotoEnd=False )
    doGotoNextBook( self )
    doGotoPreviousChapter( self, gotoEnd=False )
    doGotoNextChapter( self )
    doGotoPreviousSection( self, gotoEnd=False )
    doGotoNextSection( self )
    doGotoPreviousVerse( self )
    doGotoNextVerse( self )
    doGoForward( self )
    doGoBackward( self )
    doGotoPreviousListItem( self )
    doGotoNextListItem( self )
    doGotoBook( self )
    gotoBCV( self, BBB, C, V )
    getSwordVerseKey( self, verseKey )
    getCachedVerseData( self, verseKey )
    setCurrentVerseKey( self, newVerseKey )
    updateShownBCV( self, newReferenceVerseKey, originator=None )
    doShowInfo( self, event=None )

class SwordBibleResourceWindow( BibleResourceWindow )
    __init__( self, parentApp, moduleAbbreviation )
    refreshTitle( self )
    getContextVerseData( self, verseKey )

class DBPBibleResourceWindow( BibleResourceWindow )
    __init__( self, parentApp, moduleAbbreviation )
    refreshTitle( self )
    getContextVerseData( self, verseKey )

class InternalBibleResourceWindow( BibleResourceWindow )
    __init__( self, parentApp, modulePath, optionalWindowType=None )
    refreshTitle( self )
    getContextVerseData( self, verseKey )
    doShowInfo( self, event=None )
    _prepareInternalBible( self )
    _prepareForExports( self )
    doMostExports( self )
    doPhotoBibleExport( self )
    doODFsExport( self )
    doPDFsExport( self )
    doAllExports( self )
    _doneExports( self )
    doCheckProject( self )

demo()
"""

from gettext import gettext as _

LastModifiedDate = '2017-11-09' # by RJH
ShortProgName = "BibleResourceWindows"
ProgName = "Biblelator Bible Resource Windows"
ProgVersion = '0.40'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, sys, logging
from collections import OrderedDict
import tkinter as tk

# Biblelator imports
from BiblelatorGlobals import APP_NAME, DEFAULT, tkBREAK, MAX_PSEUDOVERSES, errorBeep, \
                            BIBLE_GROUP_CODES, BIBLE_CONTEXT_VIEW_MODES, BIBLE_FORMAT_VIEW_MODES
from ChildWindows import BibleWindowFunctions, BibleWindow, HTMLWindow
#from TextBoxes import BibleBox
from BiblelatorHelpers import findCurrentSection, handleInternalBibles
from BiblelatorSimpleDialogs import showInfo, showError
from BiblelatorDialogs import GetBibleBookRangeDialog

# BibleOrgSys imports
#if __name__ == '__main__': import sys; sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals
from Bible import Bible
from VerseReferences import SimpleVerseKey
from SwordResources import SwordType
from DigitalBiblePlatform import DBPBible
from UnknownBible import UnknownBible
from BibleOrganizationalSystems import BibleOrganizationalSystem
from InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry
from BibleWriter import setDefaultControlFolder


MAX_CACHED_VERSES = 300 # Per Bible resource window



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



class BibleResourceWindowFunctions():
    """
    The superclass must provide a getContextVerseData function.
    """
    def __init__( self, parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.__init__( {}, wt={}, m={}, dCVM={}, dFVM={} )") \
                            .format( parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode ) )
        self.parentApp, self.windowType, self.moduleID, self.defaultContextViewMode, self.defaultFormatViewMode = parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode

        # Set some dummy values required soon (esp. by refreshTitle)
        #self._contextViewRadioVar, self._formatViewRadioVar, self._groupRadioVar = tk.IntVar(), tk.IntVar(), tk.StringVar()
        #self._groupCode = BIBLE_GROUP_CODES[0] # Put into first/default BCV group
        self.BCVUpdateType = DEFAULT
        self.currentVerseKey = SimpleVerseKey( 'UNK','1','1' ) # Unknown book
        #self.defaultContextViewMode = BIBLE_CONTEXT_VIEW_MODES[0] # BeforeAndAfter
        #self.defaultFormatViewMode = BIBLE_FORMAT_VIEW_MODES[0] # Formatted
        #self.parentApp.viewVersesBefore, self.parentApp.viewVersesAfter = 2, 6
        #BibleWindow.__init__( self, self.parentApp, 'BibleResource' )
        #if self._contextViewMode == DEFAULT:
            #self._contextViewRadioVar.set( 1 )
            #self.changeBibleContextView()
        #if self._formatViewMode == DEFAULT:
            #self._formatViewRadioVar.set( 1 )
            #self.changeBibleFormatView()

        ## Set-up our standard Bible styles
        ## TODO: Why do we need this for a window
        #for USFMKey, styleDict in self.parentApp.stylesheet.getTKStyles().items():
            #self.textBox.tag_configure( USFMKey, **styleDict ) # Create the style
        ## Add our extra specialised styles
        #self.textBox.tag_configure( 'contextHeader', background='pink', font='helvetica 6 bold' )
        #self.textBox.tag_configure( 'context', background='pink', font='helvetica 6' )
        #self.textBox.tag_configure( 'markersHeader', background='yellow3', font='helvetica 6 bold' )
        #self.textBox.tag_configure( 'markers', background='yellow3', font='helvetica 6' )
        ##else:
            ##self.textBox.tag_configure( 'verseNumberFormat', foreground='blue', font='helvetica 8', relief=tk.RAISED, offset='3' )
            ##self.textBox.tag_configure( 'versePreSpaceFormat', background='pink', font='helvetica 8' )
            ##self.textBox.tag_configure( 'versePostSpaceFormat', background='pink', font='helvetica 4' )
            ##self.textBox.tag_configure( 'verseTextFormat', font='sil-doulos 12' )
            ##self.textBox.tag_configure( 'otherVerseTextFormat', font='sil-doulos 9' )
            ###self.textBox.tag_configure( 'verseText', background='yellow', font='helvetica 14 bold', relief=tk.RAISED )
            ###"background", "bgstipple", "borderwidth", "elide", "fgstipple", "font", "foreground", "justify", "lmargin1",
            ###"lmargin2", "offset", "overstrike", "relief", "rmargin", "spacing1", "spacing2", "spacing3",
            ###"tabs", "tabstyle", "underline", and "wrap".

        # Set-up our Bible system and our callables
        self.BibleOrganisationalSystem = BibleOrganizationalSystem( 'GENERIC-KJV-81-ENG' ) # temp
        self.getNumChapters = self.BibleOrganisationalSystem.getNumChapters
        self.getNumVerses = lambda b,c: MAX_PSEUDOVERSES if b=='UNK' or c=='0' or c==0 \
                                        else self.BibleOrganisationalSystem.getNumVerses( b, c )
        self.isValidBCVRef = self.BibleOrganisationalSystem.isValidBCVRef
        self.getFirstBookCode = self.BibleOrganisationalSystem.getFirstBookCode
        self.getPreviousBookCode = self.BibleOrganisationalSystem.getPreviousBookCode
        self.getNextBookCode = self.BibleOrganisationalSystem.getNextBookCode
        self.getBBBFromText = self.BibleOrganisationalSystem.getBBBFromText
        self.getBookName = self.BibleOrganisationalSystem.getBookName
        self.getBookList = self.BibleOrganisationalSystem.getBookList
        self.maxChaptersThisBook, self.maxVersesThisChapter = 150, 150 # temp

        self.BibleFindOptionsDict, self.BibleReplaceOptionsDict = {}, {}
        self.verseCache = OrderedDict()

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.__init__ finished.") )
    # end of BibleResourceWindowFunctions.__init__


    def createMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("BibleResourceWindowFunctions.createMenuBar()") )
        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.configure( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        #fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_command( label=_('Open…'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu )
        #subfileMenuImport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Import'), underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu )
        #subfileMenuExport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label=_('HTML'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Export'), underline=0, menu=subfileMenuExport )
        #fileMenu.add_separator()
        fileMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict[_('Info')][0] )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Close'), underline=0, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] ) # close this window

        editMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        editMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        editMenu.add_separator()
        editMenu.add_command( label=_('Select all'), underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )

        #searchMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        #searchMenu.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        #searchMenu.add_separator()
        #searchMenu.add_command( label=_('Find…'), underline=0, command=self.doBoxFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #searchMenu.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind, accelerator=self.parentApp.keyBindingDict[_('Refind')][0] )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        searchMenu.add_command( label=_('Bible Find…'), underline=6, command=self.doBibleFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #subsearchMenuBible.add_command( label=_('Find again'), underline=5, command=self.notWrittenYet )
        searchMenu.add_separator()
        subSearchMenuWindow = tk.Menu( searchMenu, tearoff=False )
        subSearchMenuWindow.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        subSearchMenuWindow.add_separator()
        subSearchMenuWindow.add_command( label=_('Find in window…'), underline=8, command=self.doBoxFind )
        subSearchMenuWindow.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind )
        searchMenu.add_cascade( label=_('Window'), underline=0, menu=subSearchMenuWindow )

        gotoMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.doGotoPreviousSection )
        gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.doGotoNextSection )
        gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        gotoMenu.add_separator()
        self._groupRadioVar.set( self._groupCode )
        gotoMenu.add_radiobutton( label=_('Group A'), underline=6, value='A', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group B'), underline=6, value='B', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group C'), underline=6, value='C', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group D'), underline=6, value='D', variable=self._groupRadioVar, command=self.changeBibleGroupCode )

        self.viewMenu = tk.Menu( self.menubar, tearoff=False ) # Save this reference so we can disable entries later
        self.menubar.add_cascade( menu=self.viewMenu, label=_('View'), underline=0 )
        self.viewMenu.add_radiobutton( label=_('Before and after…'), underline=7, value=1, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('One section'), underline=4, value=2, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Single verse'), underline=7, value=3, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Whole book'), underline=6, value=4, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Whole chapter'), underline=6, value=5, variable=self._contextViewRadioVar, command=self.changeBibleContextView )

        self.viewMenu.add_separator()
        self.viewMenu.add_radiobutton( label=_('Formatted'), underline=0, value=1, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )
        self.viewMenu.add_radiobutton( label=_('Unformatted'), underline=0, value=2, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )

        if 'DBP' in self.windowType: # disable excessive online use
            self.viewMenu.entryconfigure( 'Whole book', state=tk.DISABLED )
            self.viewMenu.entryconfigure( 'Whole chapter', state=tk.DISABLED )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        toolsMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        windowMenu.add_command( label=_('Bring in'), underline=0, command=self.notWrittenYet )
        windowMenu.add_separator()
        windowMenu.add_command( label=_('Show main window'), underline=0, command=self.doShowMainWindow, accelerator=self.parentApp.keyBindingDict[_('ShowMain')][0] )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, underline=0, label=_('Help') )
        helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict[_('Help')][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict[_('About')][0] )
    # end of BibleResourceWindowFunctions.createMenuBar


    def changeBibleContextView( self ):
        """
        Called when  a Bible context view is changed from the menus/GUI.
        """
        currentViewNumber = self._contextViewRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("BibleResourceWindowFunctions.changeBibleContextView( {!r} ) from {!r}").format( currentViewNumber, self._contextViewMode ) )
            assert currentViewNumber in range( 1, len(BIBLE_CONTEXT_VIEW_MODES)+1 )

        if 'Editor' in self.genericWindowType and self.saveChangesAutomatically and self.modified():
            self.doSave( 'Auto from change contextView' )

        previousContextViewMode = self._contextViewMode
        if 'Bible' in self.genericWindowType:
            if currentViewNumber == 1: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[0] ) # 'BeforeAndAfter'
            elif currentViewNumber == 2: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[1] ) # 'BySection'
            elif currentViewNumber == 3: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[2] ) # 'ByVerse'
            elif currentViewNumber == 4: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[3] ) # 'ByBook'
            elif currentViewNumber == 5: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[4] ) # 'ByChapter'
            else: halt # unknown Bible view mode
        else: halt # window type view mode not handled yet
        if self._contextViewMode != previousContextViewMode: # we need to update our view
            self.updateShownBCV( self.currentVerseKey )
    # end of BibleResourceWindowFunctions.changeBibleContextView


    def changeBibleFormatView( self ):
        """
        Called when  a Bible format view is changed from the menus/GUI.
        """
        currentViewNumber = self._formatViewRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("BibleResourceWindowFunctions.changeBibleFormatView( {!r} ) from {!r}").format( currentViewNumber, self._formatViewMode ) )
            assert currentViewNumber in range( 1, len(BIBLE_FORMAT_VIEW_MODES)+1 )

        if 'Editor' in self.genericWindowType and self.saveChangesAutomatically and self.modified():
            self.doSave( 'Auto from change formatView' )

        previousFormatViewMode = self._formatViewMode
        if 'Bible' in self.genericWindowType:
            if currentViewNumber == 1: self.setFormatViewMode( BIBLE_FORMAT_VIEW_MODES[0] ) # 'Formatted'
            elif currentViewNumber == 2: self.setFormatViewMode( BIBLE_FORMAT_VIEW_MODES[1] ) # 'Unformatted'
            else: halt # unknown Bible view mode
        else: halt # window type view mode not handled yet
        if self._formatViewMode != previousFormatViewMode: # we need to update our view
            self.updateShownBCV( self.currentVerseKey )
    # end of BibleResourceWindowFunctions.changeBibleFormatView


    def changeBibleGroupCode( self ):
        """
        Called when  a Bible group code is changed from the menus/GUI.
        """
        previousGroupCode = self._groupCode
        newGroupCode = self._groupRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("changeBibleGroupCode( {!r} ) from {!r}").format( newGroupCode, previousGroupCode ) )
            assert newGroupCode in BIBLE_GROUP_CODES
            assert 'Bible' in self.genericWindowType

        if 'Bible' in self.genericWindowType: # do we really need this test?
            self.setWindowGroup( newGroupCode )
        else: halt # window type view mode not handled yet
        if self._groupCode != previousGroupCode: # we need to update our view
            if   self._groupCode == 'A': windowVerseKey = self.parentApp.GroupA_VerseKey
            elif self._groupCode == 'B': windowVerseKey = self.parentApp.GroupB_VerseKey
            elif self._groupCode == 'C': windowVerseKey = self.parentApp.GroupC_VerseKey
            elif self._groupCode == 'D': windowVerseKey = self.parentApp.GroupD_VerseKey
            self.updateShownBCV( windowVerseKey )
    # end of BibleResourceWindowFunctions.changeBibleGroupCode


    def doGotoPreviousBook( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoPreviousBook()").format( gotoEnd ) )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousBook( {} ) from {} {}:{}").format( gotoEnd, BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousBook…" )
        newBBB = self.getPreviousBookCode( BBB )
        if newBBB is None: self.gotoBCV( BBB, '0', '0' )
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, self.maxChaptersThisBook )
            if gotoEnd: self.gotoBCV( newBBB, self.maxChaptersThisBook, self.maxVersesThisChapter )
            else: self.gotoBCV( newBBB, '0', '0' ) # go to the beginning
    # end of BibleResourceWindowFunctions.doGotoPreviousBook


    def doGotoNextBook( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoNextBook()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextBook() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextBook…" )
        newBBB = self.getNextBookCode( BBB )
        if newBBB is None: pass # stay just where we are
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, '0' )
            self.gotoBCV( newBBB, '0', '0' ) # go to the beginning of the book
    # end of BibleResourceWindowFunctions.doGotoNextBook


    def doGotoPreviousChapter( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoPreviousChapter()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousChapter() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousChapter…" )
        intC, intV = int( C ), int( V )
        if intC > 0: self.gotoBCV( BBB, intC-1, self.getNumVerses( BBB, intC-1 ) if gotoEnd else '0' )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of BibleResourceWindowFunctions.doGotoPreviousChapter


    def doGotoNextChapter( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoNextChapter()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextChapter() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextChapter…" )
        intC = int( C )
        if intC < self.maxChaptersThisBook: self.gotoBCV( BBB, intC+1, '0' )
        else: self.doGotoNextBook()
    # end of BibleResourceWindowFunctions.doGotoNextChapter


    def doGotoPreviousSection( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoPreviousSection()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousSection() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousSection…" )
        # First the start of the current section
        sectionStart1, sectionEnd1 = findCurrentSection( self.currentVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section1 Start/End", sectionStart1, sectionEnd1 )
        intC1, intV1 = sectionStart1.getChapterNumberInt(), sectionStart1.getVerseNumberInt()
        # Go back one verse from the start of the current section
        if intV1 == 0:
            if intC1 == 0:
                self.doGotoPreviousBook( gotoEnd=True )
                return
            else:
                intC1 -= 1
                intV1 = self.getNumVerses( BBB, intC1)
        else: intV1 -= 1
        # Now find the start of this previous section
        sectionStart2, sectionEnd2 = findCurrentSection( SimpleVerseKey( BBB, intC1, intV1), self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section2 Start/End", sectionStart2, sectionEnd2 )
        BBB2, C2, V2 = sectionStart2.getBCV()
        self.gotoBCV( BBB2, C2, V2 )
    # end of BibleResourceWindowFunctions.doGotoPreviousSection


    def doGotoNextSection( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindowFunctions.doGotoNextSection()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextSection() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextSection…" )
        # Find the end of the current section (which is the first verse of the next section)
        sectionStart, sectionEnd = findCurrentSection( self.currentVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section Start/End", sectionStart, sectionEnd )
        intC2, intV2 = sectionEnd.getChapterNumberInt(), sectionEnd.getVerseNumberInt()
        if intC2 < self.maxChaptersThisBook \
        or (intC2==self.maxChaptersThisBook and intV2< self.getNumVerses( BBB, intC2) ):
            self.gotoBCV( BBB, intC2, intV2 )
        else: self.doGotoNextBook()
    # end of BibleResourceWindowFunctions.doGotoNextSection


    def doGotoPreviousVerse( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousVerse() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousVerse…" )
        intC, intV = int( C ), int( V )
        if intV > 0: self.gotoBCV( BBB, C, intV-1 )
        elif intC > 0: self.doGotoPreviousChapter( gotoEnd=True )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of BibleResourceWindowFunctions.doGotoPreviousVerse


    def doGotoNextVerse( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextVerse() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextVerse…" )
        intV = int( V )
        if intV < self.maxVersesThisChapter: self.gotoBCV( BBB, C, intV+1 )
        else: self.doGotoNextChapter()
    # end of BibleResourceWindowFunctions.doGotoNextVerse


    def doGoForward( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGoForward() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGoForward…" )
        self.notWrittenYet()
    # end of BibleResourceWindowFunctions.doGoForward


    def doGoBackward( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGoBackward() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGoBackward…" )
        self.notWrittenYet()
    # end of BibleResourceWindowFunctions.doGoBackward


    def doGotoPreviousListItem( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousListItem() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousListItem…" )
        self.notWrittenYet()
    # end of BibleResourceWindowFunctions.doGotoPreviousListItem


    def doGotoNextListItem( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextListItem() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextListItem…" )
        self.notWrittenYet()
    # end of BibleResourceWindowFunctions.doGotoNextListItem


    def doGotoBook( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoBook() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoBook…" )
        self.notWrittenYet()
    # end of BibleResourceWindowFunctions.doGotoBook


    def gotoBCV( self, BBB, C, V ):
        """

        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("gotoBCV( {} {}:{} from {} )").format( BBB, C, V, self.currentVerseKey ) )
        # We really need to convert versification systems here
        adjBBB, adjC, adjV, adjS = self.BibleOrganisationalSystem.convertToReferenceVersification( BBB, C, V )
        self.parentApp.gotoGroupBCV( self._groupCode, adjBBB, adjC, adjV ) # then the App will update me by calling updateShownBCV
    # end of BibleResourceWindowFunctions.gotoBCV


    def getSwordVerseKey( self, verseKey ):
        """
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("getSwordVerseKey( {} )").format( verseKey ) )

        BBB, C, V = verseKey.getBCV()
        return self.parentApp.SwordInterface.makeKey( BBB, C, V )
    # end of BibleResourceWindowFunctions.getSwordVerseKey


    def getCachedVerseData( self, verseKey ):
        """
        Checks to see if the requested verse is in our cache,
            otherwise calls getContextVerseData (from the superclass) to fetch it.

        The cache keeps the newest or most recently used entries at the end.
        When it gets too large, it drops the first entry.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("getCachedVerseData( {} )").format( verseKey ) )

        verseKeyHash = verseKey.makeHash()
        if verseKeyHash in self.verseCache:
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  " + exp("Retrieved from BibleResourceWindowFunctions cache") )
            self.verseCache.move_to_end( verseKeyHash )
            return self.verseCache[verseKeyHash]
        verseData = self.getContextVerseData( verseKey )
        self.verseCache[verseKeyHash] = verseData
        if len(self.verseCache) > MAX_CACHED_VERSES:
            #print( "Removing oldest cached entry", len(self.verseCache) )
            self.verseCache.popitem( last=False )
        return verseData
    # end of BibleResourceWindowFunctions.getCachedVerseData


    def setCurrentVerseKey( self, newVerseKey ):
        """
        Called to set the current verse key.

        Note that newVerseKey can be None.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setCurrentVerseKey( {} )").format( newVerseKey ) )
            self.parentApp.setDebugText( "BRW setCurrentVerseKey…" )

        if newVerseKey is None:
            self.currentVerseKey = None
            self.maxChaptersThisBook = self.maxVersesThisChapter = 0
            return

        # If we get this far, it must be a real verse key
        assert isinstance( newVerseKey, SimpleVerseKey )
        self.currentVerseKey = newVerseKey

        BBB = self.currentVerseKey.getBBB()
        self.maxChaptersThisBook = self.getNumChapters( BBB )
        self.maxVersesThisChapter = self.getNumVerses( BBB, self.currentVerseKey.getChapterNumber() )
    # end of BibleResourceWindowFunctions.setCurrentVerseKey


    def updateShownBCV( self, newReferenceVerseKey, originator=None ):
        """
        Updates self.textBox in various ways depending on the contextViewMode held by the enclosing window.

        The new verse key is in the reference versification system.

        Leaves the textbox in the disabled state.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleResourceWindowFunctions.updateShownBCV( {}, {} ) for".format( newReferenceVerseKey, originator ), self.moduleID )
            #print( "contextViewMode", self._contextViewMode )
            assert isinstance( newReferenceVerseKey, SimpleVerseKey )

        refBBB, refC, refV, refS = newReferenceVerseKey.getBCVS()
        BBB, C, V, S = self.BibleOrganisationalSystem.convertFromReferenceVersification( refBBB, refC, refV, refS )
        newVerseKey = SimpleVerseKey( BBB, C, V, S )

        self.setCurrentVerseKey( newVerseKey )
        self.clearText() # Leaves the text box enabled
        startingFlag = True

        # Safety-check in case they edited the settings file
        if 'DBP' in self.windowType and self._contextViewMode in ('ByBook','ByChapter',):
            print( exp("updateShownBCV: Safety-check converted {!r} contextViewMode for DBP").format( self._contextViewMode ) )
            self._contextViewRadioVar.set( 3 ) # ByVerse
            self.changeBibleContextView()

        if self._contextViewMode == 'BeforeAndAfter':
            bibleData = self.getBeforeAndAfterBibleData( newVerseKey )
            if bibleData:
                verseData, previousVerses, nextVerses = bibleData
                for verseKey,previousVerseData in previousVerses:
                    self.displayAppendVerse( startingFlag, verseKey, previousVerseData )
                    startingFlag = False
                self.displayAppendVerse( startingFlag, newVerseKey, verseData, currentVerse=True )
                for verseKey,nextVerseData in nextVerses:
                    self.displayAppendVerse( False, verseKey, nextVerseData )

        elif self._contextViewMode == 'ByVerse':
            cachedVerseData = self.getCachedVerseData( newVerseKey )
            #print( "cVD for", self.moduleID, newVerseKey, cachedVerseData )
            if cachedVerseData is None: # We might have a missing or bridged verse
                intV = int( V )
                while intV > 1:
                    intV -= 1 # Go back looking for bridged verses to display
                    cachedVerseData = self.getCachedVerseData( SimpleVerseKey( BBB, C, intV, S ) )
                    #print( "  cVD for", self.moduleID, intV, cachedVerseData )
                    if cachedVerseData is not None: # it seems to have worked
                        break # Might have been nice to check/confirm that it was actually a bridged verse???
            self.displayAppendVerse( True, newVerseKey, cachedVerseData, currentVerse=True )

        elif self._contextViewMode == 'BySection':
            BBB, intC, intV = newVerseKey.getBBB(), newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()
            sectionStart, sectionEnd = findCurrentSection( newVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
            intC1, intV1 = sectionStart.getChapterNumberInt(), sectionStart.getVerseNumberInt()
            intC2, intV2 = sectionEnd.getChapterNumberInt(), sectionEnd.getVerseNumberInt()
            for thisC in range( intC1, intC2+1 ):
                try: numVerses = self.getNumVerses( BBB, thisC )
                except KeyError: numVerses = 0
                startV, endV = 0, numVerses
                if thisC == intC1: startV = intV1
                if thisC == intC2: endV = intV2
                for thisV in range( startV, endV+1 ):
                    thisVerseKey = SimpleVerseKey( BBB, thisC, thisV )
                    thisVerseData = self.getCachedVerseData( thisVerseKey )
                    self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData,
                                            currentVerse=thisC==intC and thisV==intV )
                    startingFlag = False

        elif self._contextViewMode == 'ByBook':
            BBB, C, V = newVerseKey.getBCV()
            intC, intV = newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()
            for thisC in range( 0, self.getNumChapters( BBB ) + 1 ):
                try: numVerses = self.getNumVerses( BBB, thisC )
                except KeyError: numVerses = 0
                for thisV in range( 0, numVerses ):
                    thisVerseKey = SimpleVerseKey( BBB, thisC, thisV )
                    thisVerseData = self.getCachedVerseData( thisVerseKey )
                    self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData,
                                            currentVerse=thisC==intC and thisV==intV )
                    startingFlag = False

        elif self._contextViewMode == 'ByChapter':
            BBB, C, V = newVerseKey.getBCV()
            intV = newVerseKey.getVerseNumberInt()
            try: numVerses = self.getNumVerses( BBB, C )
            except KeyError: numVerses = 0
            for thisV in range( 0, numVerses + 1 ):
                thisVerseKey = SimpleVerseKey( BBB, C, thisV )
                thisVerseData = self.getCachedVerseData( thisVerseKey )
                self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData, currentVerse=thisV==intV )
                startingFlag = False

        else:
            logging.critical( exp("BibleResourceWindowFunctions.updateShownBCV: Bad context view mode {}").format( self._contextViewMode ) )
            if BibleOrgSysGlobals.debugFlag: halt # Unknown context view mode

        self.textBox.configure( state=tk.DISABLED ) # Don't allow editing

        # Make sure we can see what we're supposed to be looking at
        desiredMark = 'C{}V{}'.format( newVerseKey.getChapterNumber(), newVerseKey.getVerseNumber() )
        try: self.textBox.see( desiredMark )
        except tk.TclError: print( exp("BibleResourceWindowFunctions.updateShownBCV couldn't find {!r}").format( desiredMark ) )
        self.lastCVMark = desiredMark

        self.refreshTitle()
    # end of BibleResourceWindowFunctions.updateShownBCV
# end of BibleResourceWindowFunctions class



class BibleResourceWindow( BibleWindow ):
    """
    The superclass must provide a getContextVerseData function.
    """
    def __init__( self, parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.__init__( {}, wt={}, m={}, dCVM={}, dFVM={} )") \
                            .format( parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode ) )
        self.parentApp, self.windowType, self.moduleID, self.defaultContextViewMode, self.defaultFormatViewMode = parentApp, windowType, moduleID, defaultContextViewMode, defaultFormatViewMode

        # Set some dummy values required soon (esp. by refreshTitle)
        #self._contextViewRadioVar, self._formatViewRadioVar, self._groupRadioVar = tk.IntVar(), tk.IntVar(), tk.StringVar()
        #self._groupCode = BIBLE_GROUP_CODES[0] # Put into first/default BCV group
        self.BCVUpdateType = DEFAULT
        self.currentVerseKey = SimpleVerseKey( 'UNK','1','1' ) # Unknown book
        #self.defaultContextViewMode = BIBLE_CONTEXT_VIEW_MODES[0] # BeforeAndAfter
        #self.defaultFormatViewMode = BIBLE_FORMAT_VIEW_MODES[0] # Formatted
        #self.parentApp.viewVersesBefore, self.parentApp.viewVersesAfter = 2, 6
        BibleWindow.__init__( self, self.parentApp, 'BibleResource' )
        #if self._contextViewMode == DEFAULT:
            #self._contextViewRadioVar.set( 1 )
            #self.changeBibleContextView()
        #if self._formatViewMode == DEFAULT:
            #self._formatViewRadioVar.set( 1 )
            #self.changeBibleFormatView()

        # Set-up our standard Bible styles
        # TODO: Why do we need this for a window
        for USFMKey, styleDict in self.parentApp.stylesheet.getTKStyles().items():
            self.textBox.tag_configure( USFMKey, **styleDict ) # Create the style
        # Add our extra specialised styles
        self.textBox.tag_configure( 'contextHeader', background='pink', font='helvetica 6 bold' )
        self.textBox.tag_configure( 'context', background='pink', font='helvetica 6' )
        self.textBox.tag_configure( 'markersHeader', background='yellow3', font='helvetica 6 bold' )
        self.textBox.tag_configure( 'markers', background='yellow3', font='helvetica 6' )
        #else:
            #self.textBox.tag_configure( 'verseNumberFormat', foreground='blue', font='helvetica 8', relief=tk.RAISED, offset='3' )
            #self.textBox.tag_configure( 'versePreSpaceFormat', background='pink', font='helvetica 8' )
            #self.textBox.tag_configure( 'versePostSpaceFormat', background='pink', font='helvetica 4' )
            #self.textBox.tag_configure( 'verseTextFormat', font='sil-doulos 12' )
            #self.textBox.tag_configure( 'otherVerseTextFormat', font='sil-doulos 9' )
            ##self.textBox.tag_configure( 'verseText', background='yellow', font='helvetica 14 bold', relief=tk.RAISED )
            ##"background", "bgstipple", "borderwidth", "elide", "fgstipple", "font", "foreground", "justify", "lmargin1",
            ##"lmargin2", "offset", "overstrike", "relief", "rmargin", "spacing1", "spacing2", "spacing3",
            ##"tabs", "tabstyle", "underline", and "wrap".

        # Set-up our Bible system and our callables
        self.BibleOrganisationalSystem = BibleOrganizationalSystem( 'GENERIC-KJV-81-ENG' ) # temp
        self.getNumChapters = self.BibleOrganisationalSystem.getNumChapters
        self.getNumVerses = lambda b,c: MAX_PSEUDOVERSES if b=='UNK' or c=='0' or c==0 \
                                        else self.BibleOrganisationalSystem.getNumVerses( b, c )
        self.isValidBCVRef = self.BibleOrganisationalSystem.isValidBCVRef
        self.getFirstBookCode = self.BibleOrganisationalSystem.getFirstBookCode
        self.getPreviousBookCode = self.BibleOrganisationalSystem.getPreviousBookCode
        self.getNextBookCode = self.BibleOrganisationalSystem.getNextBookCode
        self.getBBBFromText = self.BibleOrganisationalSystem.getBBBFromText
        self.getBookName = self.BibleOrganisationalSystem.getBookName
        self.getBookList = self.BibleOrganisationalSystem.getBookList
        self.maxChaptersThisBook, self.maxVersesThisChapter = 150, 150 # temp

        self.BibleFindOptionsDict, self.BibleReplaceOptionsDict = {}, {}
        self.verseCache = OrderedDict()

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.__init__ finished.") )
    # end of BibleResourceWindow.__init__


    def createMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("BibleResourceWindow.createMenuBar()") )
        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.configure( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        #fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_command( label=_('Open…'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu )
        #subfileMenuImport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Import'), underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu )
        #subfileMenuExport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label=_('HTML'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Export'), underline=0, menu=subfileMenuExport )
        #fileMenu.add_separator()
        fileMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict[_('Info')][0] )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Close'), underline=0, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] ) # close this window

        editMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        editMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        editMenu.add_separator()
        editMenu.add_command( label=_('Select all'), underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )

        #searchMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        #searchMenu.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        #searchMenu.add_separator()
        #searchMenu.add_command( label=_('Find…'), underline=0, command=self.doBoxFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #searchMenu.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind, accelerator=self.parentApp.keyBindingDict[_('Refind')][0] )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        searchMenu.add_command( label=_('Bible Find…'), underline=6, command=self.doBibleFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #subsearchMenuBible.add_command( label=_('Find again'), underline=5, command=self.notWrittenYet )
        searchMenu.add_separator()
        subSearchMenuWindow = tk.Menu( searchMenu, tearoff=False )
        subSearchMenuWindow.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        subSearchMenuWindow.add_separator()
        subSearchMenuWindow.add_command( label=_('Find in window…'), underline=8, command=self.doBoxFind )
        subSearchMenuWindow.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind )
        searchMenu.add_cascade( label=_('Window'), underline=0, menu=subSearchMenuWindow )

        gotoMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.doGotoPreviousSection )
        gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.doGotoNextSection )
        gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        gotoMenu.add_separator()
        self._groupRadioVar.set( self._groupCode )
        gotoMenu.add_radiobutton( label=_('Group A'), underline=6, value='A', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group B'), underline=6, value='B', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group C'), underline=6, value='C', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label=_('Group D'), underline=6, value='D', variable=self._groupRadioVar, command=self.changeBibleGroupCode )

        self.viewMenu = tk.Menu( self.menubar, tearoff=False ) # Save this reference so we can disable entries later
        self.menubar.add_cascade( menu=self.viewMenu, label=_('View'), underline=0 )
        self.viewMenu.add_radiobutton( label=_('Before and after…'), underline=7, value=1, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('One section'), underline=4, value=2, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Single verse'), underline=7, value=3, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Whole book'), underline=6, value=4, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        self.viewMenu.add_radiobutton( label=_('Whole chapter'), underline=6, value=5, variable=self._contextViewRadioVar, command=self.changeBibleContextView )

        self.viewMenu.add_separator()
        self.viewMenu.add_radiobutton( label=_('Formatted'), underline=0, value=1, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )
        self.viewMenu.add_radiobutton( label=_('Unformatted'), underline=0, value=2, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )

        if 'DBP' in self.windowType: # disable excessive online use
            self.viewMenu.entryconfigure( 'Whole book', state=tk.DISABLED )
            self.viewMenu.entryconfigure( 'Whole chapter', state=tk.DISABLED )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        toolsMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        windowMenu.add_command( label=_('Bring in'), underline=0, command=self.notWrittenYet )
        windowMenu.add_separator()
        windowMenu.add_command( label=_('Show main window'), underline=0, command=self.doShowMainWindow, accelerator=self.parentApp.keyBindingDict[_('ShowMain')][0] )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, underline=0, label=_('Help') )
        helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict[_('Help')][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict[_('About')][0] )
    # end of BibleResourceWindow.createMenuBar


    def changeBibleContextView( self ):
        """
        Called when  a Bible context view is changed from the menus/GUI.
        """
        currentViewNumber = self._contextViewRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("BibleResourceWindow.changeBibleContextView( {!r} ) from {!r}").format( currentViewNumber, self._contextViewMode ) )
            assert currentViewNumber in range( 1, len(BIBLE_CONTEXT_VIEW_MODES)+1 )

        if 'Editor' in self.genericWindowType and self.saveChangesAutomatically and self.modified():
            self.doSave( 'Auto from change contextView' )

        previousContextViewMode = self._contextViewMode
        if 'Bible' in self.genericWindowType:
            if currentViewNumber == 1: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[0] ) # 'BeforeAndAfter'
            elif currentViewNumber == 2: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[1] ) # 'BySection'
            elif currentViewNumber == 3: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[2] ) # 'ByVerse'
            elif currentViewNumber == 4: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[3] ) # 'ByBook'
            elif currentViewNumber == 5: self.setContextViewMode( BIBLE_CONTEXT_VIEW_MODES[4] ) # 'ByChapter'
            else: halt # unknown Bible view mode
        else: halt # window type view mode not handled yet
        if self._contextViewMode != previousContextViewMode: # we need to update our view
            self.updateShownBCV( self.currentVerseKey )
    # end of BibleResourceWindow.changeBibleContextView


    def changeBibleFormatView( self ):
        """
        Called when  a Bible format view is changed from the menus/GUI.
        """
        currentViewNumber = self._formatViewRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("BibleResourceWindow.changeBibleFormatView( {!r} ) from {!r}").format( currentViewNumber, self._formatViewMode ) )
            assert currentViewNumber in range( 1, len(BIBLE_FORMAT_VIEW_MODES)+1 )

        if 'Editor' in self.genericWindowType and self.saveChangesAutomatically and self.modified():
            self.doSave( 'Auto from change formatView' )

        previousFormatViewMode = self._formatViewMode
        if 'Bible' in self.genericWindowType:
            if currentViewNumber == 1: self.setFormatViewMode( BIBLE_FORMAT_VIEW_MODES[0] ) # 'Formatted'
            elif currentViewNumber == 2: self.setFormatViewMode( BIBLE_FORMAT_VIEW_MODES[1] ) # 'Unformatted'
            else: halt # unknown Bible view mode
        else: halt # window type view mode not handled yet
        if self._formatViewMode != previousFormatViewMode: # we need to update our view
            self.updateShownBCV( self.currentVerseKey )
    # end of BibleResourceWindow.changeBibleFormatView


    def changeBibleGroupCode( self ):
        """
        Called when  a Bible group code is changed from the menus/GUI.
        """
        previousGroupCode = self._groupCode
        newGroupCode = self._groupRadioVar.get()

        if BibleOrgSysGlobals.debugFlag:
            print( exp("changeBibleGroupCode( {!r} ) from {!r}").format( newGroupCode, previousGroupCode ) )
            assert newGroupCode in BIBLE_GROUP_CODES
            assert 'Bible' in self.genericWindowType

        if 'Bible' in self.genericWindowType: # do we really need this test?
            self.setWindowGroup( newGroupCode )
        else: halt # window type view mode not handled yet
        if self._groupCode != previousGroupCode: # we need to update our view
            if   self._groupCode == 'A': windowVerseKey = self.parentApp.GroupA_VerseKey
            elif self._groupCode == 'B': windowVerseKey = self.parentApp.GroupB_VerseKey
            elif self._groupCode == 'C': windowVerseKey = self.parentApp.GroupC_VerseKey
            elif self._groupCode == 'D': windowVerseKey = self.parentApp.GroupD_VerseKey
            self.updateShownBCV( windowVerseKey )
    # end of BibleResourceWindow.changeBibleGroupCode


    def doGotoPreviousBook( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoPreviousBook()").format( gotoEnd ) )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousBook( {} ) from {} {}:{}").format( gotoEnd, BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousBook…" )
        newBBB = self.getPreviousBookCode( BBB )
        if newBBB is None: self.gotoBCV( BBB, '0', '0' )
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, self.maxChaptersThisBook )
            if gotoEnd: self.gotoBCV( newBBB, self.maxChaptersThisBook, self.maxVersesThisChapter )
            else: self.gotoBCV( newBBB, '0', '0' ) # go to the beginning
    # end of BibleResourceWindow.doGotoPreviousBook


    def doGotoNextBook( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoNextBook()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextBook() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextBook…" )
        newBBB = self.getNextBookCode( BBB )
        if newBBB is None: pass # stay just where we are
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, '0' )
            self.gotoBCV( newBBB, '0', '0' ) # go to the beginning of the book
    # end of BibleResourceWindow.doGotoNextBook


    def doGotoPreviousChapter( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoPreviousChapter()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousChapter() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousChapter…" )
        intC, intV = int( C ), int( V )
        if intC > 0: self.gotoBCV( BBB, intC-1, self.getNumVerses( BBB, intC-1 ) if gotoEnd else '0' )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of BibleResourceWindow.doGotoPreviousChapter


    def doGotoNextChapter( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoNextChapter()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextChapter() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextChapter…" )
        intC = int( C )
        if intC < self.maxChaptersThisBook: self.gotoBCV( BBB, intC+1, '0' )
        else: self.doGotoNextBook()
    # end of BibleResourceWindow.doGotoNextChapter


    def doGotoPreviousSection( self, gotoEnd=False ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoPreviousSection()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousSection() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousSection…" )
        # First the start of the current section
        sectionStart1, sectionEnd1 = findCurrentSection( self.currentVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section1 Start/End", sectionStart1, sectionEnd1 )
        intC1, intV1 = sectionStart1.getChapterNumberInt(), sectionStart1.getVerseNumberInt()
        # Go back one verse from the start of the current section
        if intV1 == 0:
            if intC1 == 0:
                self.doGotoPreviousBook( gotoEnd=True )
                return
            else:
                intC1 -= 1
                intV1 = self.getNumVerses( BBB, intC1)
        else: intV1 -= 1
        # Now find the start of this previous section
        sectionStart2, sectionEnd2 = findCurrentSection( SimpleVerseKey( BBB, intC1, intV1), self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section2 Start/End", sectionStart2, sectionEnd2 )
        BBB2, C2, V2 = sectionStart2.getBCV()
        self.gotoBCV( BBB2, C2, V2 )
    # end of BibleResourceWindow.doGotoPreviousSection


    def doGotoNextSection( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("BibleResourceWindow.doGotoNextSection()") )

        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextSection() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextSection…" )
        # Find the end of the current section (which is the first verse of the next section)
        sectionStart, sectionEnd = findCurrentSection( self.currentVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
        print( "section Start/End", sectionStart, sectionEnd )
        intC2, intV2 = sectionEnd.getChapterNumberInt(), sectionEnd.getVerseNumberInt()
        if intC2 < self.maxChaptersThisBook \
        or (intC2==self.maxChaptersThisBook and intV2< self.getNumVerses( BBB, intC2) ):
            self.gotoBCV( BBB, intC2, intV2 )
        else: self.doGotoNextBook()
    # end of BibleResourceWindow.doGotoNextSection


    def doGotoPreviousVerse( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousVerse() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousVerse…" )
        intC, intV = int( C ), int( V )
        if intV > 0: self.gotoBCV( BBB, C, intV-1 )
        elif intC > 0: self.doGotoPreviousChapter( gotoEnd=True )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of BibleResourceWindow.doGotoPreviousVerse


    def doGotoNextVerse( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextVerse() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextVerse…" )
        intV = int( V )
        if intV < self.maxVersesThisChapter: self.gotoBCV( BBB, C, intV+1 )
        else: self.doGotoNextChapter()
    # end of BibleResourceWindow.doGotoNextVerse


    def doGoForward( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGoForward() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGoForward…" )
        self.notWrittenYet()
    # end of BibleResourceWindow.doGoForward


    def doGoBackward( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGoBackward() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGoBackward…" )
        self.notWrittenYet()
    # end of BibleResourceWindow.doGoBackward


    def doGotoPreviousListItem( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousListItem() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoPreviousListItem…" )
        self.notWrittenYet()
    # end of BibleResourceWindow.doGotoPreviousListItem


    def doGotoNextListItem( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextListItem() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoNextListItem…" )
        self.notWrittenYet()
    # end of BibleResourceWindow.doGotoNextListItem


    def doGotoBook( self ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoBook() from {} {}:{}").format( BBB, C, V ) )
            self.parentApp.setDebugText( "BRW doGotoBook…" )
        self.notWrittenYet()
    # end of BibleResourceWindow.doGotoBook


    def gotoBCV( self, BBB, C, V ):
        """

        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("gotoBCV( {} {}:{} from {} )").format( BBB, C, V, self.currentVerseKey ) )
        # We really need to convert versification systems here
        adjBBB, adjC, adjV, adjS = self.BibleOrganisationalSystem.convertToReferenceVersification( BBB, C, V )
        self.parentApp.gotoGroupBCV( self._groupCode, adjBBB, adjC, adjV ) # then the App will update me by calling updateShownBCV
    # end of BibleResourceWindow.gotoBCV


    def getSwordVerseKey( self, verseKey ):
        """
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("getSwordVerseKey( {} )").format( verseKey ) )

        BBB, C, V = verseKey.getBCV()
        return self.parentApp.SwordInterface.makeKey( BBB, C, V )
    # end of BibleResourceWindow.getSwordVerseKey


    def getCachedVerseData( self, verseKey ):
        """
        Checks to see if the requested verse is in our cache,
            otherwise calls getContextVerseData (from the superclass) to fetch it.

        The cache keeps the newest or most recently used entries at the end.
        When it gets too large, it drops the first entry.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("getCachedVerseData( {} )").format( verseKey ) )

        verseKeyHash = verseKey.makeHash()
        if verseKeyHash in self.verseCache:
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  " + exp("Retrieved from BibleResourceWindow cache") )
            self.verseCache.move_to_end( verseKeyHash )
            return self.verseCache[verseKeyHash]
        verseData = self.getContextVerseData( verseKey )
        self.verseCache[verseKeyHash] = verseData
        if len(self.verseCache) > MAX_CACHED_VERSES:
            #print( "Removing oldest cached entry", len(self.verseCache) )
            self.verseCache.popitem( last=False )
        return verseData
    # end of BibleResourceWindow.getCachedVerseData


    def setCurrentVerseKey( self, newVerseKey ):
        """
        Called to set the current verse key.

        Note that newVerseKey can be None.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setCurrentVerseKey( {} )").format( newVerseKey ) )
            self.parentApp.setDebugText( "BRW setCurrentVerseKey…" )

        if newVerseKey is None:
            self.currentVerseKey = None
            self.maxChaptersThisBook = self.maxVersesThisChapter = 0
            return

        # If we get this far, it must be a real verse key
        assert isinstance( newVerseKey, SimpleVerseKey )
        self.currentVerseKey = newVerseKey

        BBB = self.currentVerseKey.getBBB()
        self.maxChaptersThisBook = self.getNumChapters( BBB )
        self.maxVersesThisChapter = self.getNumVerses( BBB, self.currentVerseKey.getChapterNumber() )
    # end of BibleResourceWindow.setCurrentVerseKey


    def updateShownBCV( self, newReferenceVerseKey, originator=None ):
        """
        Updates self.textBox in various ways depending on the contextViewMode held by the enclosing window.

        The new verse key is in the reference versification system.

        Leaves the textbox in the disabled state.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "BibleResourceWindow.updateShownBCV( {}, {} ) for".format( newReferenceVerseKey, originator ), self.moduleID )
            #print( "contextViewMode", self._contextViewMode )
            assert isinstance( newReferenceVerseKey, SimpleVerseKey )

        refBBB, refC, refV, refS = newReferenceVerseKey.getBCVS()
        BBB, C, V, S = self.BibleOrganisationalSystem.convertFromReferenceVersification( refBBB, refC, refV, refS )
        newVerseKey = SimpleVerseKey( BBB, C, V, S )

        self.setCurrentVerseKey( newVerseKey )
        self.clearText() # Leaves the text box enabled
        startingFlag = True

        # Safety-check in case they edited the settings file
        if 'DBP' in self.windowType and self._contextViewMode in ('ByBook','ByChapter',):
            print( exp("updateShownBCV: Safety-check converted {!r} contextViewMode for DBP").format( self._contextViewMode ) )
            self._contextViewRadioVar.set( 3 ) # ByVerse
            self.changeBibleContextView()

        if self._contextViewMode == 'BeforeAndAfter':
            bibleData = self.getBeforeAndAfterBibleData( newVerseKey )
            if bibleData:
                verseData, previousVerses, nextVerses = bibleData
                for verseKey,previousVerseData in previousVerses:
                    self.displayAppendVerse( startingFlag, verseKey, previousVerseData )
                    startingFlag = False
                self.displayAppendVerse( startingFlag, newVerseKey, verseData, currentVerse=True )
                for verseKey,nextVerseData in nextVerses:
                    self.displayAppendVerse( False, verseKey, nextVerseData )

        elif self._contextViewMode == 'ByVerse':
            cachedVerseData = self.getCachedVerseData( newVerseKey )
            #print( "cVD for", self.moduleID, newVerseKey, cachedVerseData )
            if cachedVerseData is None: # We might have a missing or bridged verse
                intV = int( V )
                while intV > 1:
                    intV -= 1 # Go back looking for bridged verses to display
                    cachedVerseData = self.getCachedVerseData( SimpleVerseKey( BBB, C, intV, S ) )
                    #print( "  cVD for", self.moduleID, intV, cachedVerseData )
                    if cachedVerseData is not None: # it seems to have worked
                        break # Might have been nice to check/confirm that it was actually a bridged verse???
            self.displayAppendVerse( True, newVerseKey, cachedVerseData, currentVerse=True )

        elif self._contextViewMode == 'BySection':
            BBB, intC, intV = newVerseKey.getBBB(), newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()
            sectionStart, sectionEnd = findCurrentSection( newVerseKey, self.getNumChapters, self.getNumVerses, self.getCachedVerseData )
            intC1, intV1 = sectionStart.getChapterNumberInt(), sectionStart.getVerseNumberInt()
            intC2, intV2 = sectionEnd.getChapterNumberInt(), sectionEnd.getVerseNumberInt()
            for thisC in range( intC1, intC2+1 ):
                try: numVerses = self.getNumVerses( BBB, thisC )
                except KeyError: numVerses = 0
                startV, endV = 0, numVerses
                if thisC == intC1: startV = intV1
                if thisC == intC2: endV = intV2
                for thisV in range( startV, endV+1 ):
                    thisVerseKey = SimpleVerseKey( BBB, thisC, thisV )
                    thisVerseData = self.getCachedVerseData( thisVerseKey )
                    self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData,
                                            currentVerse=thisC==intC and thisV==intV )
                    startingFlag = False

        elif self._contextViewMode == 'ByBook':
            BBB, C, V = newVerseKey.getBCV()
            intC, intV = newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()
            for thisC in range( 0, self.getNumChapters( BBB ) + 1 ):
                try: numVerses = self.getNumVerses( BBB, thisC )
                except KeyError: numVerses = 0
                for thisV in range( 0, numVerses ):
                    thisVerseKey = SimpleVerseKey( BBB, thisC, thisV )
                    thisVerseData = self.getCachedVerseData( thisVerseKey )
                    self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData,
                                            currentVerse=thisC==intC and thisV==intV )
                    startingFlag = False

        elif self._contextViewMode == 'ByChapter':
            BBB, C, V = newVerseKey.getBCV()
            intV = newVerseKey.getVerseNumberInt()
            try: numVerses = self.getNumVerses( BBB, C )
            except KeyError: numVerses = 0
            for thisV in range( 0, numVerses + 1 ):
                thisVerseKey = SimpleVerseKey( BBB, C, thisV )
                thisVerseData = self.getCachedVerseData( thisVerseKey )
                self.displayAppendVerse( startingFlag, thisVerseKey, thisVerseData, currentVerse=thisV==intV )
                startingFlag = False

        else:
            logging.critical( exp("BibleResourceWindow.updateShownBCV: Bad context view mode {}").format( self._contextViewMode ) )
            if BibleOrgSysGlobals.debugFlag: halt # Unknown context view mode

        self.textBox.configure( state=tk.DISABLED ) # Don't allow editing

        # Make sure we can see what we're supposed to be looking at
        desiredMark = 'C{}V{}'.format( newVerseKey.getChapterNumber(), newVerseKey.getVerseNumber() )
        try: self.textBox.see( desiredMark )
        except tk.TclError: print( exp("BibleResourceWindow.updateShownBCV couldn't find {!r}").format( desiredMark ) )
        self.lastCVMark = desiredMark

        self.refreshTitle()
    # end of BibleResourceWindow.updateShownBCV
# end of BibleResourceWindow class



class SwordBibleResourceWindow( BibleResourceWindow ):
    """
    """
    def __init__( self, parentApp, moduleAbbreviation, defaultContextViewMode=BIBLE_CONTEXT_VIEW_MODES[0], defaultFormatViewMode=BIBLE_FORMAT_VIEW_MODES[0] ):
        """
        """
        if BibleOrgSysGlobals.debugFlag: print( "SwordBibleResourceWindow.__init__( {}, {} )".format( parentApp, moduleAbbreviation ) )
        self.parentApp, self.moduleAbbreviation = parentApp, moduleAbbreviation
        BibleResourceWindow.__init__( self, self.parentApp, 'SwordBibleResourceWindow', self.moduleAbbreviation, defaultContextViewMode, defaultFormatViewMode )
        #self.windowType = 'SwordBibleResourceWindow'
        self.createContextMenu() # Enable right-click menu

        #self.SwordModule = None # Loaded later in self.getBeforeAndAfterBibleData()
        try:
            self.SwordModule = self.parentApp.SwordInterface.getModule( self.moduleAbbreviation )
        except KeyError:
            self.doClose() # Don't leave an empty window hanging there
            raise KeyError
        if self.SwordModule is None:
            logging.error( exp("SwordBibleResourceWindow.__init__ Unable to open Sword module: {}").format( self.moduleAbbreviation ) )
            self.SwordModule = None
        elif isinstance( self.SwordModule, Bible ):
            #print( "Handle internalBible for SwordModuleRW" )
            handleInternalBibles( self.parentApp, self.SwordModule, self )
        else: print( "SwordModule using {} is {}".format( SwordType, self.SwordModule ) )

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordBibleResourceWindow.__init__ finished.") )
    # end of SwordBibleResourceWindow.__init__


    def refreshTitle( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordBibleResourceWindow.refreshTitle()") )

        self.title( "[{}] {} ({}) {} {}:{} [{}]".format( self._groupCode,
                                    self.moduleAbbreviation, 'Sw' if SwordType=="CrosswireLibrary" else 'SwM',
                                    self.currentVerseKey.getBBB(), self.currentVerseKey.getChapterNumber(), self.currentVerseKey.getVerseNumber(),
                                    self._contextViewMode ) )
    # end if SwordBibleResourceWindow.refreshTitle


    def getContextVerseData( self, verseKey ):
        """
        Fetches and returns the internal Bible data for the given reference.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("SwordBibleResourceWindow.getContextVerseData( {} )").format( verseKey ) )
        if self.SwordModule is not None:
            if verseKey.getChapterNumber()!='0' and verseKey.getVerseNumber()!='0': # not sure how to get introductions, etc.
                SwordKey = self.getSwordVerseKey( verseKey )
                rawInternalBibleContextData = self.parentApp.SwordInterface.getContextVerseData( self.SwordModule, SwordKey )
                if rawInternalBibleContextData is None: return '', ''
                rawInternalBibleData, context = rawInternalBibleContextData
                # Clean up the data -- not sure that it should be done here! … XXXXXXXXXXXXXXXXXXX
                #from InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry
                import re
                adjustedInternalBibleData = InternalBibleEntryList()
                for existingInternalBibleEntry in rawInternalBibleData:
                    #print( 'eIBE', existingInternalBibleEntry )
                    cleanText = existingInternalBibleEntry.getCleanText()
                    cleanText = cleanText.replace( '</w>', '' )
                    cleanText = re.sub( '<w .+?>', '', cleanText )
                    newInternalBibleEntry = InternalBibleEntry( existingInternalBibleEntry[0], existingInternalBibleEntry[1], existingInternalBibleEntry[2],
                        cleanText, existingInternalBibleEntry[4], existingInternalBibleEntry[5] )
                    #print( 'nIBE', newInternalBibleEntry )
                    adjustedInternalBibleData.append( newInternalBibleEntry )
                return adjustedInternalBibleData, context
    # end of SwordBibleResourceWindow.getContextVerseData


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("SwordBibleResourceWindow.doShowInfo( {} )").format( event ) )

        infoString = 'SwordBibleResourceWindow:\n' \
                 + '  Module:\t\t{}\n'.format( self.moduleAbbreviation ) \
                 + '  Type:\t\t{}\n'.format( '' if self.SwordModule is None else self.SwordModule.getType() ) \
                 + '  Format:\t\t{}\n'.format( '' if self.SwordModule is None else self.SwordModule.getMarkup() ) \
                 + '  Encoding:\t{}'.format( '' if self.SwordModule is None else self.SwordModule.getEncoding() )
        showInfo( self, 'Window Information', infoString )
    # end of SwordBibleResourceWindow.doShowInfo
# end of SwordBibleResourceWindow class



class DBPBibleResourceWindow( BibleResourceWindow ):
    """
    """
    def __init__( self, parentApp, moduleAbbreviation, defaultContextViewMode=BIBLE_CONTEXT_VIEW_MODES[0], defaultFormatViewMode=BIBLE_FORMAT_VIEW_MODES[0] ):
        """
        """
        if BibleOrgSysGlobals.debugFlag:
            print( "DBPBibleResourceWindow.__init__( {}, {} )".format( parentApp, moduleAbbreviation ) )
            assert moduleAbbreviation and isinstance( moduleAbbreviation, str ) and len(moduleAbbreviation)==6
        self.parentApp, self.moduleAbbreviation = parentApp, moduleAbbreviation

        self.DBPModule = None # (for refreshTitle called from the base class)
        BibleResourceWindow.__init__( self, self.parentApp, 'DBPBibleResourceWindow', self.moduleAbbreviation, defaultContextViewMode, defaultFormatViewMode )
        #self.windowType = 'DBPBibleResourceWindow'
        self.createContextMenu() # Enable right-click menu

        # Disable excessive online use
        self.viewMenu.entryconfigure( 'Whole book', state=tk.DISABLED )
        self.viewMenu.entryconfigure( 'Whole chapter', state=tk.DISABLED )

        try: self.DBPModule = DBPBible( self.moduleAbbreviation )
        except FileNotFoundError:
            logging.error( exp("DBPBibleResourceWindow.__init__ Unable to find a key to connect to Digital Bible Platform") )
            self.DBPModule = None
        except ConnectionError:
            logging.error( exp("DBPBibleResourceWindow.__init__ Unable to connect to Digital Bible Platform") )
            self.DBPModule = None

        if isinstance( self.DBPModule, Bible ):
            #print( "Handle internalBible for DBPModuleRW" )
            handleInternalBibles( self.parentApp, self.DBPModule, self )
        else: print( "DBPModule is", self.DBPModule )

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("DBPBibleResourceWindow.__init__ finished.") )
    # end of DBPBibleResourceWindow.__init__


    def refreshTitle( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("DBPBibleResourceWindow.refreshTitle()") )

        self.title( "[{}] {}.{}{} {} {}:{} [{}]".format( self._groupCode,
                                        self.moduleAbbreviation[:3], self.moduleAbbreviation[3:],
                                        ' (online)' if self.DBPModule else ' (offline)',
                                        self.currentVerseKey.getBBB(), self.currentVerseKey.getChapterNumber(), self.currentVerseKey.getVerseNumber(),
                                        self._contextViewMode ) )
    # end if DBPBibleResourceWindow.refreshTitle


    def getContextVerseData( self, verseKey ):
        """
        Fetches and returns the internal Bible data for the given reference.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("DBPBibleResourceWindow.getContextVerseData( {} )").format( verseKey ) )

        if self.DBPModule is not None:
            if verseKey.getChapterNumber()!='0' and verseKey.getVerseNumber()!='0': # not sure how to get introductions, etc.
                return self.DBPModule.getContextVerseData( verseKey )
    # end of DBPBibleResourceWindow.getContextVerseData


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("DBPBibleResourceWindow.doShowInfo( {} )").format( event ) )

        infoString = 'DBPBibleResourceWindow:\n' \
                 + '  Name:\t{}'.format( self.moduleAbbreviation )
        showInfo( self, 'Window Information', infoString )
    # end of DBPBibleResourceWindow.doShowInfo
# end of DBPBibleResourceWindow class



class InternalBibleResourceWindowFunctions( BibleResourceWindowFunctions, BibleWindowFunctions ):
    """
    A window displaying one internal (on-disk) Bible.
    """
    def __init__( self, parentApp, modulePath, defaultContextViewMode=BIBLE_CONTEXT_VIEW_MODES[0], defaultFormatViewMode=BIBLE_FORMAT_VIEW_MODES[0] ):
        """
        Given a folder, try to open an UnknownBible.
        If successful, set self.internalBible to point to the loaded Bible.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "InternalBibleResourceWindowFunctions.__init__( {}, m={} )".format( parentApp, modulePath ) )
        self.parentApp, self.modulePath = parentApp, modulePath

        self.internalBible = None # (for refreshTitle called from the base class)
        BibleResourceWindowFunctions.__init__( self, self.parentApp, 'InternalBibleResourceWindowFunctions', self.modulePath, defaultContextViewMode, defaultFormatViewMode )
        BibleWindowFunctions.__init__( self, self.parentApp, 'BibleResource' )
        #BibleResourceWindow.__init__( self, self.parentApp, 'InternalBibleResourceWindowFunctions', self.modulePath, defaultContextViewMode, defaultFormatViewMode )
        #self.windowType = 'InternalBibleResourceWindowFunctions'
        #self.createContextMenu() # Enable right-click menu

        if self.modulePath is not None:
            try: self.UnknownBible = UnknownBible( self.modulePath )
            except FileNotFoundError:
                logging.error( exp("InternalBibleResourceWindowFunctions.__init__ Unable to find module path: {!r}").format( self.modulePath ) )
                self.UnknownBible = None
            if self.UnknownBible:
                result = self.UnknownBible.search( autoLoadAlways=True )
                if isinstance( result, str ):
                    print( "Unknown Bible returned: {!r}".format( result ) )
                    self.internalBible = None
                else:
                    #print( "Handle internalBible for internalBibleRW" )
                    self.internalBible = handleInternalBibles( self.parentApp, result, self )
        if self.internalBible is not None: # Define which functions we use by default
            self.getNumVerses = self.internalBible.getNumVerses
            self.getNumChapters = self.internalBible.getNumChapters

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.__init__ finished.") )
    # end of InternalBibleResourceWindowFunctions.__init__


    #def createMenuBar( self ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("InternalBibleResourceWindowFunctions.createMenuBar()") )
        #self.menubar = tk.Menu( self )
        ##self['menu'] = self.menubar
        #self.configure( menu=self.menubar ) # alternative

        #fileMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        ##fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_command( label=_('Open…'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_separator()
        ##subfileMenuImport = tk.Menu( fileMenu )
        ##subfileMenuImport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_cascade( label=_('Import'), underline=0, menu=subfileMenuImport )
        ##subfileMenuExport = tk.Menu( fileMenu )
        ##subfileMenuExport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        ##subfileMenuExport.add_command( label=_('HTML'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_cascade( label=_('Export'), underline=0, menu=subfileMenuExport )
        ##fileMenu.add_separator()
        #fileMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict[_('Info')][0] )
        #fileMenu.add_separator()
        #fileMenu.add_command( label=_('Close'), underline=0, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] ) # close this window

        #editMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        #editMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        #editMenu.add_separator()
        #editMenu.add_command( label=_('Select all'), underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )

        #searchMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        #searchMenu.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        #searchMenu.add_separator()
        #searchMenu.add_command( label=_('Find…'), underline=0, command=self.doBoxFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #searchMenu.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind, accelerator=self.parentApp.keyBindingDict[_('Refind')][0] )

        #gotoMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        #gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        #gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        #gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        #gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        #gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.doGotoPreviousSection )
        #gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.doGotoNextSection )
        #gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        #gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        #gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        #gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        #gotoMenu.add_separator()
        #self._groupRadioVar.set( self._groupCode )
        #gotoMenu.add_radiobutton( label=_('Group A'), underline=6, value='A', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group B'), underline=6, value='B', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group C'), underline=6, value='C', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group D'), underline=6, value='D', variable=self._groupRadioVar, command=self.changeBibleGroupCode )

        #self.viewMenu = tk.Menu( self.menubar, tearoff=False ) # Save this reference so we can disable entries later
        #self.menubar.add_cascade( menu=self.viewMenu, label=_('View'), underline=0 )
        #self.viewMenu.add_radiobutton( label=_('Before and after…'), underline=7, value=1, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('One section'), underline=4, value=2, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Single verse'), underline=7, value=3, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Whole book'), underline=6, value=4, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Whole chapter'), underline=6, value=5, variable=self._contextViewRadioVar, command=self.changeBibleContextView )

        #self.viewMenu.add_separator()
        #self.viewMenu.add_radiobutton( label=_('Formatted'), underline=0, value=1, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )
        #self.viewMenu.add_radiobutton( label=_('Unformatted'), underline=0, value=2, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )

        #if 'DBP' in self.windowType: # disable excessive online use
            #self.viewMenu.entryconfigure( 'Whole book', state=tk.DISABLED )
            #self.viewMenu.entryconfigure( 'Whole chapter', state=tk.DISABLED )

        #toolsMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        #toolsMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        #windowMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        #windowMenu.add_command( label=_('Bring in'), underline=0, command=self.notWrittenYet )
        #windowMenu.add_separator()
        #windowMenu.add_command( label=_('Show main window'), underline=0, command=self.doShowMainWindow, accelerator=self.parentApp.keyBindingDict[_('ShowMain')][0] )

        #helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        #self.menubar.add_cascade( menu=helpMenu, underline=0, label=_('Help') )
        #helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict[_('Help')][0] )
        #helpMenu.add_separator()
        #helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict[_('About')][0] )
    ## end of InternalBibleResourceWindowFunctions.createMenuBar


    def refreshTitle( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.refreshTitle()") )

        self.title( "[{}] {} (InternalBible){} {} {}:{} [{}]".format( self._groupCode,
                        self.modulePath if self.internalBible is None else self.internalBible.getAName(),
                        ' NOT FOUND' if self.internalBible is None else '',
                        self.currentVerseKey.getBBB(), self.currentVerseKey.getChapterNumber(), self.currentVerseKey.getVerseNumber(),
                        self._contextViewMode ) )
    # end if InternalBibleResourceWindowFunctions.refreshTitle


    def createContextMenu( self ):
        """
        Can be overriden if necessary.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.createContextMenu()") )

        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Select all'), underline=7, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Bible Find…'), underline=6, command=self.doBibleFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Find in window…'), underline=8, command=self.doBoxFind )#, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #self.contextMenu.add_separator()
        #self.contextMenu.add_command( label=_('Close window'), underline=1, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] )

        self.bind( '<Button-3>', self.showContextMenu ) # right-click
        #self.pack()

        self.BibleFindOptionsDict, self.BibleReplaceOptionsDict = {}, {}
    # end of InternalBibleResourceWindowFunctions.createContextMenu


    def getContextVerseData( self, verseKey ):
        """
        Fetches and returns the internal Bible data for the given reference.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.getContextVerseData( {} )").format( verseKey ) )

        if self.internalBible is not None:
            try: return self.internalBible.getContextVerseData( verseKey )
            except KeyError: # Could be after a verse-bridge ???
                if verseKey.getChapterNumber() != '0':
                    logging.error( exp("InternalBibleResourceWindowFunctions.getContextVerseData for {} {} got a KeyError") \
                                                                .format( self.windowType, verseKey ) )
    # end of InternalBibleResourceWindowFunctions.getContextVerseData


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doShowInfo( {} )").format( event ) )

        infoString = 'InternalBibleResourceWindowFunctions:\n' \
                 + '  Name:\t{}\n'.format( self.modulePath if self.internalBible is None else self.internalBible.getAName() ) \
                 + '  Type:\t{}\n'.format( self.modulePath if self.internalBible is None else self.internalBible.objectTypeString ) \
                 + '  Path:\t{}'.format( self.modulePath )
        showInfo( self, 'Window Information', infoString )
    # end of InternalBibleResourceWindowFunctions.doShowInfo


    def _prepareForExports( self ):
        """
        Prepare to do some of the exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.prepareForExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.prepareForExports()") )

        self._prepareInternalBible()
        if self.internalBible is not None:
            self.parentApp.setWaitStatus( _("Preparing for export…") )
            if self.exportFolderPathname is None:
                fp = self.folderPath
                if fp and fp[-1] in '/\\': fp = fp[:-1] # Removing trailing slash
                self.exportFolderPathname = fp + 'Export/'
                #print( "eFolder", repr(self.exportFolderPathname) )
                if not os.path.exists( self.exportFolderPathname ):
                    os.mkdir( self.exportFolderPathname )
            setDefaultControlFolder( '../BibleOrgSys/ControlFiles/' )
            self.parentApp.setWaitStatus( _("Export in process…") )
    # end of InternalBibleResourceWindowFunctions._prepareForExports

    def doMostExports( self ):
        """
        Do most of the quicker exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doMostExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doMostExports()") )

        self._prepareForExports()
        self.internalBible.doAllExports( self.exportFolderPathname )
        self._doneExports()
    # end of InternalBibleResourceWindowFunctions.doMostExports

    def doPhotoBibleExport( self ):
        """
        Do the BibleOrgSys PhotoBible export.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doPhotoBibleExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doPhotoBibleExport()") )

        self._prepareForExports()
        self.internalBible.toPhotoBible( os.path.join( self.exportFolderPathname, 'BOS_PhotoBible_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindowFunctions.doPhotoBibleExport

    def doODFsExport( self ):
        """
        Do the BibleOrgSys ODFsExport export.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doODFsExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doODFsExport()") )

        self._prepareForExports()
        self.internalBible.toODF( os.path.join( self.exportFolderPathname, 'BOS_ODF_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindowFunctions.doODFsExport

    def doPDFsExport( self ):
        """
        Do the BibleOrgSys PDFsExport export.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doPDFsExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doPDFsExport()") )

        self._prepareForExports()
        self.internalBible.toTeX( os.path.join( self.exportFolderPathname, 'BOS_PDF(TeX)_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindowFunctions.doPDFsExport

    def doAllExports( self ):
        """
        Do all exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doAllExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doAllExports()") )

        self._prepareForExports()
        self.internalBible.doAllExports( self.exportFolderPathname, wantPhotoBible=True, wantODFs=True, wantPDFs=True )
        self._doneExports()
    # end of InternalBibleResourceWindowFunctions.doAllExports


    def _doneExports( self ):
        """
        """
        self.parentApp.setStatus( _("Waiting for user input…") )
        infoString = _("Results should be in {}").format( self.exportFolderPathname )
        showInfo( self, 'Folder Information', infoString )
        self.parentApp.setReadyStatus()
    # end of InternalBibleResourceWindowFunctions.doAllExports


    def doCheckProject( self ):
        """
        Run the BibleOrgSys checks on the project.
        """
        logging.info( exp("InternalBibleResourceWindowFunctions.doCheckProject()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doCheckProject()") )

        self._prepareInternalBible() # Slow but must be called before the dialog
        currentBBB = self.currentVerseKey.getBBB()
        gBBRD = GetBibleBookRangeDialog( self, self.parentApp, self.internalBible, currentBBB, None, title=_('Books to be checked') )
        #if BibleOrgSysGlobals.debugFlag: print( "gBBRDResult", repr(gBBRD.result) )
        if gBBRD.result:
            if BibleOrgSysGlobals.debugFlag: assert isinstance( gBBRD.result, list )
            #if len(gBBRD.result)==1 and gBBRD.result[0]==currentBBB:
                ## It's just the current book to check
                #if self.modified(): self.doSave()
                #self.internalBible.loadBookIfNecessary( currentBBB )
            #else: # load all books
                #self._prepareInternalBible()
            self.parentApp.setWaitStatus( _("Doing Bible checks…") )
            self.internalBible.check( gBBRD.result )
            displayExternally = False
            if displayExternally: # Call up a browser window
                import webbrowser
                indexFile = self.internalBible.makeErrorHTML( self.folderPath, gBBRD.result )
                webbrowser.open( indexFile )
            else: # display internally in our HTMLWindow
                indexFile = self.internalBible.makeErrorHTML( self.folderPath, gBBRD.result )
                hW = HTMLWindow( self, indexFile )
                self.parentApp.childWindows.append( hW )
                if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Finished openCheckWindow" )
        self.parentApp.setReadyStatus()
    # end of InternalBibleResourceWindowFunctions.doCheckProject


    def doHelp( self, event=None ):
        """
        Display a help box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doHelp( {} )").format( event ) )
        from Help import HelpBox

        helpInfo = ProgNameVersion
        helpInfo += '\n' + _("Help for {}").format( self.windowType )
        helpInfo += '\n  ' + _("Keyboard shortcuts:")
        for name,shortcut in self.myKeyboardBindingsList:
            helpInfo += "\n    {}\t{}".format( name, shortcut )
        hb = HelpBox( self, self.genericWindowType, helpInfo )
        return tkBREAK # so we don't do the main window help also
    # end of InternalBibleResourceWindowFunctions.doHelp


    def doAbout( self, event=None ):
        """
        Display an about box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doAbout( {} )").format( event ) )
        from About import AboutBox

        aboutInfo = ProgNameVersion
        aboutInfo += "\nInformation about {}".format( self.windowType )
        ab = AboutBox( self, self.genericWindowType, aboutInfo )
        return tkBREAK # so we don't do the main window about also
    # end of InternalBibleResourceWindowFunctions.doAbout


    def doClose( self, event=None ):
        """
        Called to finally and irreversibly remove this window from our list and close it.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindowFunctions.doClose( {} ) for {}").format( event, self.genericWindowType ) )

        # Remove ourself from the list of internal Bibles (and their controlling windows)
        #print( 'internalBibles initially', len(self.parentApp.internalBibles), self.parentApp.internalBibles )
        newBibleList = []
        for internalBible,windowList in self.parentApp.internalBibles:
            if internalBible is self.internalBible:
                newWindowList = []
                for controllingWindow in windowList:
                    if controllingWindow is not self: # leave other windows alone
                        newWindowList.append( controllingWindow )
                if newWindowList: newBibleList.append( (internalBible,windowList) )
            else: # leave this one unchanged
                newBibleList.append( (internalBible,windowList) )
        self.parentApp.internalBibles = newBibleList
        #print( 'internalBibles now', len(self.parentApp.internalBibles), self.parentApp.internalBibles )

        BibleResourceWindow.doClose( self, event )
        if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Closed InternalBibleResourceWindowFunctions" )
    # end of InternalBibleResourceWindowFunctions.doClose
# end of InternalBibleResourceWindowFunctions class



class InternalBibleResourceWindow( BibleResourceWindow ):
    """
    A window displaying one internal (on-disk) Bible.
    """
    def __init__( self, parentApp, modulePath, defaultContextViewMode=BIBLE_CONTEXT_VIEW_MODES[0], defaultFormatViewMode=BIBLE_FORMAT_VIEW_MODES[0] ):
        """
        Given a folder, try to open an UnknownBible.
        If successful, set self.internalBible to point to the loaded Bible.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "InternalBibleResourceWindow.__init__( {}, m={} )".format( parentApp, modulePath ) )
        self.parentApp, self.modulePath = parentApp, modulePath

        self.internalBible = None # (for refreshTitle called from the base class)
        BibleResourceWindow.__init__( self, self.parentApp, 'InternalBibleResourceWindow', self.modulePath, defaultContextViewMode, defaultFormatViewMode )
        #self.windowType = 'InternalBibleResourceWindow'
        self.createContextMenu() # Enable right-click menu

        if self.modulePath is not None:
            try: self.UnknownBible = UnknownBible( self.modulePath )
            except FileNotFoundError:
                logging.error( exp("InternalBibleResourceWindow.__init__ Unable to find module path: {!r}").format( self.modulePath ) )
                self.UnknownBible = None
            if self.UnknownBible:
                result = self.UnknownBible.search( autoLoadAlways=True )
                if isinstance( result, str ):
                    print( "Unknown Bible returned: {!r}".format( result ) )
                    self.internalBible = None
                else:
                    #print( "Handle internalBible for internalBibleRW" )
                    self.internalBible = handleInternalBibles( self.parentApp, result, self )
        if self.internalBible is not None: # Define which functions we use by default
            self.getNumVerses = self.internalBible.getNumVerses
            self.getNumChapters = self.internalBible.getNumChapters

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.__init__ finished.") )
    # end of InternalBibleResourceWindow.__init__


    #def createMenuBar( self ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("InternalBibleResourceWindow.createMenuBar()") )
        #self.menubar = tk.Menu( self )
        ##self['menu'] = self.menubar
        #self.configure( menu=self.menubar ) # alternative

        #fileMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        ##fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_command( label=_('Open…'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_separator()
        ##subfileMenuImport = tk.Menu( fileMenu )
        ##subfileMenuImport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_cascade( label=_('Import'), underline=0, menu=subfileMenuImport )
        ##subfileMenuExport = tk.Menu( fileMenu )
        ##subfileMenuExport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        ##subfileMenuExport.add_command( label=_('HTML'), underline=0, command=self.notWrittenYet )
        ##fileMenu.add_cascade( label=_('Export'), underline=0, menu=subfileMenuExport )
        ##fileMenu.add_separator()
        #fileMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict[_('Info')][0] )
        #fileMenu.add_separator()
        #fileMenu.add_command( label=_('Close'), underline=0, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] ) # close this window

        #editMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        #editMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        #editMenu.add_separator()
        #editMenu.add_command( label=_('Select all'), underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )

        #searchMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        #searchMenu.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        #searchMenu.add_separator()
        #searchMenu.add_command( label=_('Find…'), underline=0, command=self.doBoxFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #searchMenu.add_command( label=_('Find again'), underline=5, command=self.doBoxRefind, accelerator=self.parentApp.keyBindingDict[_('Refind')][0] )

        #gotoMenu = tk.Menu( self.menubar )
        #self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        #gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        #gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        #gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        #gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        #gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.doGotoPreviousSection )
        #gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.doGotoNextSection )
        #gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        #gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        #gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        #gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        #gotoMenu.add_separator()
        #gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        #gotoMenu.add_separator()
        #self._groupRadioVar.set( self._groupCode )
        #gotoMenu.add_radiobutton( label=_('Group A'), underline=6, value='A', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group B'), underline=6, value='B', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group C'), underline=6, value='C', variable=self._groupRadioVar, command=self.changeBibleGroupCode )
        #gotoMenu.add_radiobutton( label=_('Group D'), underline=6, value='D', variable=self._groupRadioVar, command=self.changeBibleGroupCode )

        #self.viewMenu = tk.Menu( self.menubar, tearoff=False ) # Save this reference so we can disable entries later
        #self.menubar.add_cascade( menu=self.viewMenu, label=_('View'), underline=0 )
        #self.viewMenu.add_radiobutton( label=_('Before and after…'), underline=7, value=1, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('One section'), underline=4, value=2, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Single verse'), underline=7, value=3, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Whole book'), underline=6, value=4, variable=self._contextViewRadioVar, command=self.changeBibleContextView )
        #self.viewMenu.add_radiobutton( label=_('Whole chapter'), underline=6, value=5, variable=self._contextViewRadioVar, command=self.changeBibleContextView )

        #self.viewMenu.add_separator()
        #self.viewMenu.add_radiobutton( label=_('Formatted'), underline=0, value=1, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )
        #self.viewMenu.add_radiobutton( label=_('Unformatted'), underline=0, value=2, variable=self._formatViewRadioVar, command=self.changeBibleFormatView )

        #if 'DBP' in self.windowType: # disable excessive online use
            #self.viewMenu.entryconfigure( 'Whole book', state=tk.DISABLED )
            #self.viewMenu.entryconfigure( 'Whole chapter', state=tk.DISABLED )

        #toolsMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        #toolsMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        #windowMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        #windowMenu.add_command( label=_('Bring in'), underline=0, command=self.notWrittenYet )
        #windowMenu.add_separator()
        #windowMenu.add_command( label=_('Show main window'), underline=0, command=self.doShowMainWindow, accelerator=self.parentApp.keyBindingDict[_('ShowMain')][0] )

        #helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        #self.menubar.add_cascade( menu=helpMenu, underline=0, label=_('Help') )
        #helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict[_('Help')][0] )
        #helpMenu.add_separator()
        #helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict[_('About')][0] )
    ## end of InternalBibleResourceWindow.createMenuBar


    def refreshTitle( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.refreshTitle()") )

        self.title( "[{}] {} (InternalBible){} {} {}:{} [{}]".format( self._groupCode,
                        self.modulePath if self.internalBible is None else self.internalBible.getAName(),
                        ' NOT FOUND' if self.internalBible is None else '',
                        self.currentVerseKey.getBBB(), self.currentVerseKey.getChapterNumber(), self.currentVerseKey.getVerseNumber(),
                        self._contextViewMode ) )
    # end if InternalBibleResourceWindow.refreshTitle


    def createContextMenu( self ):
        """
        Can be overriden if necessary.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.createContextMenu()") )

        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Select all'), underline=7, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Bible Find…'), underline=6, command=self.doBibleFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Find in window…'), underline=8, command=self.doBoxFind )#, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        #self.contextMenu.add_separator()
        #self.contextMenu.add_command( label=_('Close window'), underline=1, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] )

        self.bind( '<Button-3>', self.showContextMenu ) # right-click
        #self.pack()

        self.BibleFindOptionsDict, self.BibleReplaceOptionsDict = {}, {}
    # end of InternalBibleResourceWindow.createContextMenu


    def getContextVerseData( self, verseKey ):
        """
        Fetches and returns the internal Bible data for the given reference.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.getContextVerseData( {} )").format( verseKey ) )

        if self.internalBible is not None:
            try: return self.internalBible.getContextVerseData( verseKey )
            except KeyError: # Could be after a verse-bridge ???
                if verseKey.getChapterNumber() != '0':
                    logging.error( exp("InternalBibleResourceWindow.getContextVerseData for {} {} got a KeyError") \
                                                                .format( self.windowType, verseKey ) )
    # end of InternalBibleResourceWindow.getContextVerseData


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doShowInfo( {} )").format( event ) )

        infoString = 'InternalBibleResourceWindow:\n' \
                 + '  Name:\t{}\n'.format( self.modulePath if self.internalBible is None else self.internalBible.getAName() ) \
                 + '  Type:\t{}\n'.format( self.modulePath if self.internalBible is None else self.internalBible.objectTypeString ) \
                 + '  Path:\t{}'.format( self.modulePath )
        showInfo( self, 'Window Information', infoString )
    # end of InternalBibleResourceWindow.doShowInfo


    def _prepareForExports( self ):
        """
        Prepare to do some of the exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindow.prepareForExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.prepareForExports()") )

        self._prepareInternalBible()
        if self.internalBible is not None:
            self.parentApp.setWaitStatus( _("Preparing for export…") )
            if self.exportFolderPathname is None:
                fp = self.folderPath
                if fp and fp[-1] in '/\\': fp = fp[:-1] # Removing trailing slash
                self.exportFolderPathname = fp + 'Export/'
                #print( "eFolder", repr(self.exportFolderPathname) )
                if not os.path.exists( self.exportFolderPathname ):
                    os.mkdir( self.exportFolderPathname )
            setDefaultControlFolder( '../BibleOrgSys/ControlFiles/' )
            self.parentApp.setWaitStatus( _("Export in process…") )
    # end of InternalBibleResourceWindow._prepareForExports

    def doMostExports( self ):
        """
        Do most of the quicker exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindow.doMostExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doMostExports()") )

        self._prepareForExports()
        self.internalBible.doAllExports( self.exportFolderPathname )
        self._doneExports()
    # end of InternalBibleResourceWindow.doMostExports

    def doPhotoBibleExport( self ):
        """
        Do the BibleOrgSys PhotoBible export.
        """
        logging.info( exp("InternalBibleResourceWindow.doPhotoBibleExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doPhotoBibleExport()") )

        self._prepareForExports()
        self.internalBible.toPhotoBible( os.path.join( self.exportFolderPathname, 'BOS_PhotoBible_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindow.doPhotoBibleExport

    def doODFsExport( self ):
        """
        Do the BibleOrgSys ODFsExport export.
        """
        logging.info( exp("InternalBibleResourceWindow.doODFsExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doODFsExport()") )

        self._prepareForExports()
        self.internalBible.toODF( os.path.join( self.exportFolderPathname, 'BOS_ODF_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindow.doODFsExport

    def doPDFsExport( self ):
        """
        Do the BibleOrgSys PDFsExport export.
        """
        logging.info( exp("InternalBibleResourceWindow.doPDFsExport()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doPDFsExport()") )

        self._prepareForExports()
        self.internalBible.toTeX( os.path.join( self.exportFolderPathname, 'BOS_PDF(TeX)_Export/' ) )
        self._doneExports()
    # end of InternalBibleResourceWindow.doPDFsExport

    def doAllExports( self ):
        """
        Do all exports available in BibleOrgSysGlobals.
        """
        logging.info( exp("InternalBibleResourceWindow.doAllExports()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doAllExports()") )

        self._prepareForExports()
        self.internalBible.doAllExports( self.exportFolderPathname, wantPhotoBible=True, wantODFs=True, wantPDFs=True )
        self._doneExports()
    # end of InternalBibleResourceWindow.doAllExports


    def _doneExports( self ):
        """
        """
        self.parentApp.setStatus( _("Waiting for user input…") )
        infoString = _("Results should be in {}").format( self.exportFolderPathname )
        showInfo( self, 'Folder Information', infoString )
        self.parentApp.setReadyStatus()
    # end of InternalBibleResourceWindow.doAllExports


    def doCheckProject( self ):
        """
        Run the BibleOrgSys checks on the project.
        """
        logging.info( exp("InternalBibleResourceWindow.doCheckProject()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doCheckProject()") )

        self._prepareInternalBible() # Slow but must be called before the dialog
        currentBBB = self.currentVerseKey.getBBB()
        gBBRD = GetBibleBookRangeDialog( self, self.parentApp, self.internalBible, currentBBB, None, title=_('Books to be checked') )
        #if BibleOrgSysGlobals.debugFlag: print( "gBBRDResult", repr(gBBRD.result) )
        if gBBRD.result:
            if BibleOrgSysGlobals.debugFlag: assert isinstance( gBBRD.result, list )
            #if len(gBBRD.result)==1 and gBBRD.result[0]==currentBBB:
                ## It's just the current book to check
                #if self.modified(): self.doSave()
                #self.internalBible.loadBookIfNecessary( currentBBB )
            #else: # load all books
                #self._prepareInternalBible()
            self.parentApp.setWaitStatus( _("Doing Bible checks…") )
            self.internalBible.check( gBBRD.result )
            displayExternally = False
            if displayExternally: # Call up a browser window
                import webbrowser
                indexFile = self.internalBible.makeErrorHTML( self.folderPath, gBBRD.result )
                webbrowser.open( indexFile )
            else: # display internally in our HTMLWindow
                indexFile = self.internalBible.makeErrorHTML( self.folderPath, gBBRD.result )
                hW = HTMLWindow( self, indexFile )
                self.parentApp.childWindows.append( hW )
                if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Finished openCheckWindow" )
        self.parentApp.setReadyStatus()
    # end of InternalBibleResourceWindow.doCheckProject


    def doHelp( self, event=None ):
        """
        Display a help box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doHelp( {} )").format( event ) )
        from Help import HelpBox

        helpInfo = ProgNameVersion
        helpInfo += '\n' + _("Help for {}").format( self.windowType )
        helpInfo += '\n  ' + _("Keyboard shortcuts:")
        for name,shortcut in self.myKeyboardBindingsList:
            helpInfo += "\n    {}\t{}".format( name, shortcut )
        hb = HelpBox( self, self.genericWindowType, helpInfo )
        return tkBREAK # so we don't do the main window help also
    # end of InternalBibleResourceWindow.doHelp


    def doAbout( self, event=None ):
        """
        Display an about box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doAbout( {} )").format( event ) )
        from About import AboutBox

        aboutInfo = ProgNameVersion
        aboutInfo += "\nInformation about {}".format( self.windowType )
        ab = AboutBox( self, self.genericWindowType, aboutInfo )
        return tkBREAK # so we don't do the main window about also
    # end of InternalBibleResourceWindow.doAbout


    def doClose( self, event=None ):
        """
        Called to finally and irreversibly remove this window from our list and close it.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("InternalBibleResourceWindow.doClose( {} ) for {}").format( event, self.genericWindowType ) )

        # Remove ourself from the list of internal Bibles (and their controlling windows)
        #print( 'internalBibles initially', len(self.parentApp.internalBibles), self.parentApp.internalBibles )
        newBibleList = []
        for internalBible,windowList in self.parentApp.internalBibles:
            if internalBible is self.internalBible:
                newWindowList = []
                for controllingWindow in windowList:
                    if controllingWindow is not self: # leave other windows alone
                        newWindowList.append( controllingWindow )
                if newWindowList: newBibleList.append( (internalBible,windowList) )
            else: # leave this one unchanged
                newBibleList.append( (internalBible,windowList) )
        self.parentApp.internalBibles = newBibleList
        #print( 'internalBibles now', len(self.parentApp.internalBibles), self.parentApp.internalBibles )

        BibleResourceWindow.doClose( self, event )
        if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Closed InternalBibleResourceWindow" )
    # end of InternalBibleResourceWindow.doClose
# end of InternalBibleResourceWindow class



def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( exp("Running demo…") )

    tkRootWindow = Tk()
    tkRootWindow.title( ProgNameVersion )

    #settings = ApplicationSettings( 'BiblelatorData/', 'BiblelatorSettings/', ProgName )
    #settings.load()

    #application = Application( parent=tkRootWindow, settings=settings )
    # Calls to the window manager class (wm in Tk)
    #application.master.title( ProgNameVersion )
    #application.master.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()
# end of BibleResourceWindows.demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        from tkinter import TclVersion, TkVersion
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of BibleResourceWindows.py
