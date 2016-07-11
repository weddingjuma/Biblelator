#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TextEditWindow.py
#
# The actual edit windows for Biblelator text editing and USFM/ESFM Bible editing
#
# Copyright (C) 2013-2016 Robert Hunt
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
xxx to allow editing of USFM Bibles using Python3 and Tkinter.
"""

from gettext import gettext as _

LastModifiedDate = '2016-07-11' # by RJH
ShortProgName = "TextEditWindow"
ProgName = "Biblelator Text Edit Window"
ProgVersion = '0.37'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True

import os.path, logging, shutil #, re
from datetime import datetime
#from time import time

import tkinter as tk
from tkinter import font
#from tkinter.simpledialog import askstring, askinteger
from tkinter.filedialog import asksaveasfilename
from tkinter.ttk import Button, Label, Entry

# Biblelator imports
from BiblelatorGlobals import APP_NAME, START, DEFAULT
from BiblelatorDialogs import showerror, showinfo, YesNoDialog, OkCancelDialog
from TextBoxes import CustomText
from ChildWindows import ChildWindow #, HTMLWindow
from AutocorrectFunctions import setDefaultAutocorrectEntries # setAutocorrectEntries

# BibleOrgSys imports
#if __name__ == '__main__': import sys; sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals



REFRESH_TITLE_TIME = 500 # msecs
CHECK_DISK_CHANGES_TIME = 33333 # msecs
NO_TYPE_TIME = 6000 # msecs



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



class TextEditWindow( ChildWindow ):
    def __init__( self, parentApp, folderPath=None, filename=None ):
        """
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("TextEditWindow.__init__( {}, {}, {} )").format( parentApp, folderPath, filename ) )

        self.parentApp, self.folderPath, self.filename = parentApp, folderPath, filename
        self.filepath = os.path.join( folderPath, filename ) if folderPath and filename else None

        self.parentApp.logUsage( ProgName, debuggingThisModule, 'TextEditWindow __init__ {} {}'.format( folderPath, filename ) )

        # Set some dummy values required soon (esp. by refreshTitle)
        self.editMode = DEFAULT
        ChildWindow.__init__( self, self.parentApp, 'TextEditor' ) # calls refreshTitle
        self.moduleID = None
        self.windowType = 'PlainTextEditWindow'
        self.protocol( 'WM_DELETE_WINDOW', self.doClose ) # Catch when window is closed

        self.loading = True
        self.onTextNoChangeID = None

        # Make our own custom textBox which allows a callback function
        #   Delete these four lines and the callback line if you don't need either autocorrect or autocomplete
        self.textBox.destroy() # from the ChildWindow default
        self.myKeyboardBindingsList = []
        if BibleOrgSysGlobals.debugFlag: self.myKeyboardShortcutsList = []

        self.customFont = tk.font.Font( family="sans-serif", size=12 )
        self.textBox = CustomText( self, yscrollcommand=self.vScrollbar.set, wrap='word', font=self.customFont )

        self.defaultBackgroundColour = 'gold2'
        self.textBox.config( background=self.defaultBackgroundColour )
        self.textBox.config( selectbackground='blue' )
        self.textBox.config( highlightbackground='orange' )
        self.textBox.config( inactiveselectbackground='green' )
        self.textBox.config( wrap='word', undo=True, autoseparators=True )
        self.textBox.pack( side=tk.TOP, fill=tk.BOTH, expand=tk.YES )
        self.vScrollbar.config( command=self.textBox.yview ) # link the scrollbar to the text box
        self.textBox.setTextChangeCallback( self.onTextChange )
        #self.createStandardKeyboardBindings()
        self.createEditorKeyboardBindings()

        self.lastFiletime = self.lastFilesize = None
        self.clearText()

        self.autocorrectEntries = []
        # Temporarily include some default autocorrect values
        setDefaultAutocorrectEntries( self )
        #setAutocorrectEntries( self, ourAutocorrectEntries )

        self.autocompleteBox, self.autocompleteWords, self.existingAutocompleteWordText = None, {}, ''
        self.autocompleteWordChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
        # Note: I guess we could have used non-word chars instead (to stop the backwards word search)
        self.autocompleteMinLength = 2 # Show the window after this many characters have been typed
        self.autocompleteMaxLength = 15 # Remove window after this many characters have been typed
        self.autocompleteMode = None # None or Dictionary1 or Dictionary2 (or Bible or BibleBook)

        self.invalidCombinations = [] # characters or character combinations that shouldn't occur
        # Temporarily include some default invalid values
        self.invalidCombinations = [',,',' ,',] # characters or character combinations that shouldn't occur

        self.saveChangesAutomatically = False # different from AutoSave (which is in different files)
        self.autosaveTime = 2*60*1000 # msecs (zero is no autosaves)
        self.autosaveScheduled = False

        self.after( CHECK_DISK_CHANGES_TIME, self.checkForDiskChanges )
        #self.after( REFRESH_TITLE_TIME, self.refreshTitle )
        self.loading = self.hadTextWarning = False
        #self.lastTextChangeTime = time()

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.__init__ finished.") )
    # end of TextEditWindow.__init__


    #def __str__(self): return "TextEditWindow"
    #def __repr__(self): return "TextEditWindow"


    def createEditorKeyboardBindings( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.createEditorKeyboardBindings()") )

        for name,command in ( ('Paste',self.doPaste), ('Cut',self.doCut),
                             ('Undo',self.doUndo), ('Redo',self.doRedo),
                             ('Save',self.doSave), ):
            assert (name,self.parentApp.keyBindingDict[name][0],) not in self.myKeyboardBindingsList
            if name in self.parentApp.keyBindingDict:
                for keyCode in self.parentApp.keyBindingDict[name][1:]:
                    #print( "Bind {} for {}".format( repr(keyCode), repr(name) ) )
                    self.textBox.bind( keyCode, command )
                    if BibleOrgSysGlobals.debugFlag:
                        assert keyCode not in self.myKeyboardShortcutsList
                        self.myKeyboardShortcutsList.append( keyCode )
                self.myKeyboardBindingsList.append( (name,self.parentApp.keyBindingDict[name][0],) )
            else: logging.critical( 'No key binding available for {}'.format( repr(name) ) )
    # end of TextEditWindow.createEditorKeyboardBindings()


    def createMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.createMenuBar()") )

        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.config( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        fileMenu.add_command( label=_('Save'), underline=0, command=self.doSave, accelerator=self.parentApp.keyBindingDict[_('Save')][0] )
        fileMenu.add_command( label=_('Save as…'), underline=5, command=self.doSaveAs )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu, tearoff=False )
        #subfileMenuImport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Import'), underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu, tearoff=False )
        #subfileMenuExport.add_command( label=_('USX'), underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label=_('HTML'), underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label=_('Export'), underline=0, menu=subfileMenuExport )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict[_('Info')][0] )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Close'), underline=0, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] )

        editMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        editMenu.add_command( label=_('Undo'), underline=0, command=self.doUndo, accelerator=self.parentApp.keyBindingDict[_('Undo')][0] )
        editMenu.add_command( label=_('Redo'), underline=0, command=self.doRedo, accelerator=self.parentApp.keyBindingDict[_('Redo')][0] )
        editMenu.add_separator()
        editMenu.add_command( label=_('Cut'), underline=2, command=self.doCut, accelerator=self.parentApp.keyBindingDict[_('Cut')][0] )
        editMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        editMenu.add_command( label=_('Paste'), underline=0, command=self.doPaste, accelerator=self.parentApp.keyBindingDict[_('Paste')][0] )
        editMenu.add_separator()
        editMenu.add_command( label=_('Delete'), underline=0, command=self.doDelete )
        editMenu.add_command( label=_('Select all'), underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label=_('Search'), underline=0 )
        searchMenu.add_command( label=_('Goto line…'), underline=0, command=self.doGotoWindowLine, accelerator=self.parentApp.keyBindingDict[_('Line')][0] )
        searchMenu.add_separator()
        searchMenu.add_command( label=_('Find…'), underline=0, command=self.doWindowFind, accelerator=self.parentApp.keyBindingDict[_('Find')][0] )
        searchMenu.add_command( label=_('Find again'), underline=5, command=self.doWindowRefind, accelerator=self.parentApp.keyBindingDict[_('Refind')][0] )
        searchMenu.add_command( label=_('Replace…'), underline=0, command=self.doWindowFindReplace )
        #searchMenu.add_separator()
        #searchMenu.add_command( label=_('Grep…'), underline=0, command=self.onGrep )

##        gotoMenu = tk.Menu( self.menubar )
##        self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
##        gotoMenu.add_command( label=_('Previous book'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Next book'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Previous chapter'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Next chapter'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Previous verse'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Next verse'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label=_('Forward'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Backward'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label=_('Previous list item'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label=_('Next list item'), underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label=_('Book'), underline=0, command=self.notWrittenYet )

        viewMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=viewMenu, label=_('View'), underline=0 )
        viewMenu.add_command( label=_('Larger text'), underline=0, command=self.OnFontBigger )
        viewMenu.add_command( label=_('Smaller text'), underline=1, command=self.OnFontSmaller )
        viewMenu.add_separator()
        viewMenu.add_checkbutton( label=_('Status bar'), underline=9, variable=self._showStatusBarVar, command=self.doToggleStatusBar )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        toolsMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        windowMenu.add_command( label=_('Bring in'), underline=0, command=self.notWrittenYet )
        windowMenu.add_separator()
        windowMenu.add_command( label=_('Show main window'), underline=0, command=self.doShowMainWindow, accelerator=self.parentApp.keyBindingDict[_('ShowMain')][0] )

        if BibleOrgSysGlobals.debugFlag:
            debugMenu = tk.Menu( self.menubar, tearoff=False )
            self.menubar.add_cascade( menu=debugMenu, label=_('Debug'), underline=0 )
            #debugMenu.add_command( label=_('View settings…'), underline=5, command=self.doViewSettings )
            #debugMenu.add_separator()
            debugMenu.add_command( label=_('View log…'), underline=5, command=self.doViewLog )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, label=_('Help'), underline=0 )
        helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict[_('Help')][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict[_('About')][0] )
    # end of TextEditWindow.createMenuBar


    def createContextMenu( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.createContextMenu()") )

        self.contextMenu = tk.Menu( self, tearoff=False )
        self.contextMenu.add_command( label=_('Cut'), underline=2, command=self.doCut, accelerator=self.parentApp.keyBindingDict[_('Cut')][0] )
        self.contextMenu.add_command( label=_('Copy'), underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict[_('Copy')][0] )
        self.contextMenu.add_command( label=_('Paste'), underline=0, command=self.doPaste, accelerator=self.parentApp.keyBindingDict[_('Paste')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Select all'), underline=7, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict[_('SelectAll')][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label=_('Close'), underline=1, command=self.doClose, accelerator=self.parentApp.keyBindingDict[_('Close')][0] )

        self.bind( '<Button-3>', self.showContextMenu ) # right-click
    # end of TextEditWindow.createContextMenu


    #def showContextMenu( self, e):
        #self.contextMenu.post( e.x_root, e.y_root )
    ## end of TextEditWindow.showContextMenu


    #def createToolBar( self ):
        #toolbar = Frame( self, cursor='hand2', relief=tk.SUNKEN ) # bd=2
        #toolbar.pack( side=tk.BOTTOM, fill=tk.X )
        #Button( toolbar, text='Halt',  command=self.quit ).pack( side=tk.RIGHT )
        #Button( toolbar, text='Hide Resources', command=self.hideResources ).pack(side=tk.LEFT )
        #Button( toolbar, text='Hide All', command=self.hideAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Show All', command=self.showAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Bring All', command=self.bringAll ).pack( side=tk.LEFT )
    ## end of TextEditWindow.createToolBar


    def refreshTitle( self ):
        """
        Refresh the title of the text edit window,
            put an asterisk if it's modified.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.refreshTitle()") )

        self.title( "{}[{}] {} ({}) Editable".format( '*' if self.modified() else '',
                                            _("Text"), self.filename, self.folderPath ) )
        self.refreshTitleContinue()
    # end if TextEditWindow.refreshTitle

    def refreshTitleContinue( self ):
        """
        Check if an autosave is needed,
            and schedule the next refresh.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.refreshTitleContinue()") )

        self.after( REFRESH_TITLE_TIME, self.refreshTitle ) # Redo it so we can put up the asterisk if the text is changed
        try:
            if self.autosaveTime and self.modified() and not self.autosaveScheduled:
                self.after( self.autosaveTime, self.doAutosave ) # Redo it so we can put up the asterisk if the text is changed
                self.autosaveScheduled = True
        except AttributeError:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "Autosave not set-up properly yet" )
    # end if TextEditWindow.refreshTitleContinue


    def OnFontBigger( self ):
        """
        Make the font one point bigger
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.OnFontBigger()") )

        size = self.customFont['size']
        self.customFont.configure( size=size+1 )
    # end if TextEditWindow.OnFontBigger

    def OnFontSmaller( self ):
        """
        Make the font one point smaller
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.OnFontSmaller()") )

        size = self.customFont['size']
        self.customFont.configure( size=size-1 )
    # end if TextEditWindow.OnFontSmaller


    def OnAutocompleteChar( self, event ):
        """
        Used by autocomplete routines in onTextChange.

        Handles key presses entered into the pop-up word selection (list) box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.OnAutocompleteChar( {!r}, {!r} )").format( event.char, event.keysym ) )
            assert self.autocompleteBox is not None

        #if event.keysym == 'ESC':
        #if event.char==' ' or event.char in self.autocompleteWordChars:
            #self.textBox.insert( tk.INSERT, event.char ) # Causes onTextChange which reassesses
        if event.keysym == 'BackSpace':
            row, column = self.textBox.index(tk.INSERT).split('.')
            column = str( int(column) - 1 )
            self.textBox.delete( row + '.' + column, tk.INSERT ) # parameters are fromPoint, toPoint
        elif event.keysym == 'Delete':
            row, column = self.textBox.index(tk.INSERT).split('.')
            column = str( int(column) + 1 ) # Only works as far as the end of the line (won't delete a \n)
            # Change the call below to a single parameter if you want it to work across lines
            self.textBox.delete( tk.INSERT, row + '.' + column ) # parameters are fromPoint, toPoint
        elif event.keysym == 'Return':
            self.acceptAutocompleteSelection( includeTrailingSpace=False )
        #elif event.keysym in ( 'Up', 'Down', 'Shift_R', 'Shift_L',
                              #'Control_L', 'Control_R', 'Alt_L',
                              #'Alt_R', 'parenleft', 'parenright'):
            #pass
        elif event.keysym == 'Escape':
            self.removeAutocompleteBox()
        #elif event.keysym in ( 'Delete', ): pass # Just ignore these keypresses
        elif event.char:
            #if event.char in '.,': self.acceptAutocompleteSelection( includeTrailingSpace=False )
            self.textBox.insert( tk.INSERT, event.char )
                                    #+ (' ' if event.char in ',' else '') ) # Causes onTextChange which reassesses
    # end of TextEditWindow.OnAutocompleteChar


    def doAcceptAutocompleteSelection( self, event=None ):
        """
        Used by autocomplete routines in onTextChange.

        Gets the chosen word and inserts the end of it into the text.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.doAcceptAutocompleteSelection({} )").format( event ) )
            assert self.autocompleteBox is not None

        self.acceptAutocompleteSelection( includeTrailingSpace=False )
    # end of TextEditWindow.doAcceptAutocompleteSelection


    def acceptAutocompleteSelection( self, includeTrailingSpace=False ):
        """
        Used by autocomplete routines in onTextChange.

        Gets the chosen word and inserts the end of it into the text.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.acceptAutocompleteSelection( {} )").format( includeTrailingSpace ) )
            assert self.autocompleteBox is not None

        currentWord = self.autocompleteBox.get( tk.ACTIVE )
        #print( '  autocompleteBox currentWord', currentWord )
        self.removeAutocompleteBox()

        # Autocomplete by inserting the rest of the selected word plus a space
        # NOTE: The user has to backspace over the space if they don't want it (e.g., to put a period)
        # NOTE: The box reappears with the current code if we don't append the space -- would need to add a flag
        self.textBox.insert( tk.INSERT, currentWord[len(self.existingAutocompleteWordText):] \
                                        + (' ' if includeTrailingSpace else '') )

        # Put this word at the beginning of the list so it comes up on top next time
        firstLetter, remainder = currentWord[0], currentWord[1:]
        self.autocompleteWords[firstLetter].remove( remainder )
        self.autocompleteWords[firstLetter].insert( 0, remainder )
    # end of TextEditWindow.acceptAutocompleteSelection


    def removeAutocompleteBox( self, event=None ):
        """
        Remove the pop-up Listbox (in a Frame in a Toplevel) when it's no longer required.
        Used by autocomplete routines in onTextChange.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.removeAutocompleteBox( {} )").format( event ) )
            assert self.autocompleteBox is not None

        self.textBox.focus()
        self.autocompleteBox.master.master.destroy() # master is Frame, master.master is Toplevel
        self.autocompleteBox = None
    # end of TextEditWindow.removeAutocompleteBox


    def onTextChange( self, result, *args ):
        """
        Called whenever the text box cursor changes either with a mouse click or arrow keys.

        Checks to see if they have moved to a new chapter/verse,
            and if so, informs the parent app.
        """
        if self.onTextNoChangeID:
            self.after_cancel( self.onTextNoChangeID ) # Cancel any delayed checks which are scheduled
            self.onTextNoChangeID = None
        if self.loading: return # So we don't get called a million times for nothing
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.onTextChange( {}, {} )").format( repr(result), args ) )

        #if 0: # Get line and column info
            #lineColumn = self.textBox.index( tk.INSERT )
            #print( "lc", repr(lineColumn) )
            #line, column = lineColumn.split( '.', 1 )
            #print( "l,c", repr(line), repr(column) )

        #if 0: # get formatting tag info
            #tagNames = self.textBox.tag_names( tk.INSERT )
            #tagNames2 = self.textBox.tag_names( lineColumn )
            #tagNames3 = self.textBox.tag_names( tk.INSERT + ' linestart' )
            #tagNames4 = self.textBox.tag_names( lineColumn + ' linestart' )
            #tagNames5 = self.textBox.tag_names( tk.INSERT + ' linestart+1c' )
            #tagNames6 = self.textBox.tag_names( lineColumn + ' linestart+1c' )
            #print( "tN", tagNames )
            #if tagNames2!=tagNames or tagNames3!=tagNames or tagNames4!=tagNames or tagNames5!=tagNames or tagNames6!=tagNames:
                #print( "tN2", tagNames2 )
                #print( "tN3", tagNames3 )
                #print( "tN4", tagNames4 )
                #print( "tN5", tagNames5 )
                #print( "tN6", tagNames6 )
                #halt

        #if 0: # show various mark strategies
            #mark1 = self.textBox.mark_previous( tk.INSERT )
            #mark2 = self.textBox.mark_previous( lineColumn )
            #mark3 = self.textBox.mark_previous( tk.INSERT + ' linestart' )
            #mark4 = self.textBox.mark_previous( lineColumn + ' linestart' )
            #mark5 = self.textBox.mark_previous( tk.INSERT + ' linestart+1c' )
            #mark6 = self.textBox.mark_previous( lineColumn + ' linestart+1c' )
            #print( "mark1", mark1 )
            #if mark2!=mark1:
                #print( "mark2", mark1 )
            #if mark3!=mark1 or mark4!=mark1 or mark5!=mark1 or mark6!=mark1:
                #print( "mark3", mark3 )
                #if mark4!=mark3:
                    #print( "mark4", mark4 )
                #print( "mark5", mark5 )
                #if mark6!=mark5:
                    #print( "mark6", mark6 )


        if self.textBox.edit_modified():
            # Handle auto-correct
            if self.autocorrectEntries and args[0]=='insert' and args[1]=='insert':
                #print( "Handle autocorrect" )
                previousText = self.getCharactersBeforeCursor( self.maxAutocorrectLength )
                #print( "previousText", repr(previousText) )
                for inChars,outChars in self.autocorrectEntries:
                    if previousText.endswith( inChars ):
                        #print( "Going to replace {!r} with {!r}".format( inChars, outChars ) )
                        # Delete the typed character(s) and replace with the new one(s)
                        self.textBox.delete( tk.INSERT+'-{}c'.format( len(inChars) ), tk.INSERT )
                        self.textBox.insert( tk.INSERT, outChars )
            # end of auto-correct section


            # Handle auto-complete
            #print( 'args[0]', repr(args[0]) )
            if self.autocompleteMode is not None and self.autocompleteWords and args[0] in ('insert','delete',):
                #print( "Handle autocomplete1" )
                lastAutocompleteWordText = self.existingAutocompleteWordText
                self.existingAutocompleteWordText = self.getWordCharactersBeforeCursor( self.autocompleteMaxLength )
                if self.existingAutocompleteWordText != lastAutocompleteWordText:
                    # we've had an actual change in the entered text
                    if len(self.existingAutocompleteWordText) >= self.autocompleteMinLength:
                        firstLetter, remainder = self.existingAutocompleteWordText[0], self.existingAutocompleteWordText[1:]
                        try: possibleWords = [firstLetter+thisBit for thisBit in self.autocompleteWords[firstLetter] \
                                                                if thisBit.startswith(remainder) and thisBit != remainder]
                        except KeyError: possibleWords = None
                        #print( 'possibleWords', possibleWords )
                        if possibleWords:
                            #print( "Handle autocomplete2" )
                            if self.autocompleteBox is None:
                                #print( 'create listbox' )
                                x, y, cx, cy = self.textBox.bbox( tk.INSERT )
                                topLevel = tk.Toplevel( self.textBox.master )
                                topLevel.wm_overrideredirect(1) # Don't display window decorations (close button, etc.)
                                topLevel.wm_geometry( '+{}+{}' \
                                    .format( x + self.textBox.winfo_rootx() + 2, y + cy + self.textBox.winfo_rooty() ) )
                                frame = tk.Frame( topLevel, highlightthickness=1, highlightcolor='darkgreen' )
                                frame.pack( fill=tk.BOTH, expand=tk.YES )
                                autocompleteScrollbar = tk.Scrollbar( frame, highlightthickness=0 )
                                autocompleteScrollbar.pack( side=tk.RIGHT, fill=tk.Y )
                                self.autocompleteBox = tk.Listbox( frame, highlightthickness=0,
                                                            relief="flat",
                                                            yscrollcommand=autocompleteScrollbar.set,
                                                            width=20, height=6 )
                                autocompleteScrollbar.config( command=self.autocompleteBox.yview )
                                self.autocompleteBox.pack( side=tk.LEFT, fill=tk.BOTH )
                                #self.autocompleteBox.select_set( '0' )
                                #self.autocompleteBox.focus()
                                self.autocompleteBox.bind( '<Key>', self.OnAutocompleteChar )
                                self.autocompleteBox.bind( '<Double-1>', self.doAcceptAutocompleteSelection )
                                self.autocompleteBox.bind( '<FocusOut>', self.removeAutocompleteBox )
                            else: # the Listbox is already made -- just empty it
                                #print( 'empty listbox' )
                                self.autocompleteBox.delete( 0, tk.END ) # clear the listbox completely
                            # Now fill the Listbox
                            #print( 'fill listbox' )
                            for word in possibleWords:
                                if BibleOrgSysGlobals.debugFlag: assert possibleWords.count( word ) == 1
                                self.autocompleteBox.insert( tk.END, word )
                            # Do a bit more set-up
                            #self.autocompleteBox.pack( side=tk.LEFT, fill=tk.BOTH )
                            self.autocompleteBox.select_set( '0' )
                            self.autocompleteBox.focus()

                        elif self.autocompleteBox is not None:
                            #print( 'destroy1 autocomplete listbox -- no possible words' )
                            self.removeAutocompleteBox()
                    elif self.autocompleteBox is not None:
                        #print( 'destroy2 autocomplete listbox -- not enough typed yet' )
                        self.removeAutocompleteBox()
            elif self.autocompleteBox is not None:
                #print( 'destroy3 autocomplete listbox -- autocomplete is not enabled/appropriate' )
                self.removeAutocompleteBox()
            # end of auto-complete section

        #self.lastTextChangeTime = time()
        try: self.onTextNoChangeID = self.after( NO_TYPE_TIME, self.onTextNoChange ) # Reschedule myself so we keep checking
        except KeyboardInterrupt:
            print( "TextEditWindow: Got keyboard interrupt-- saving my file" )
            self.doSave() # Sometimes the above seems to lock up
    # end of TextEditWindow.onTextChange


    def onTextNoChange( self ):
        """
        Called whenever the text box HASN'T CHANGED for NO_TYPE_TIME msecs.

        Checks for some types of formatting errors.
        """
        #print( "TextEditWindow.onTextNoChange" )
        pass
    # end of TextEditWindow.onTextNoChange


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog giving text statistics and cursor location;
        caveat (2.1): Tk insert position column counts a tab as one
        character: translate to next multiple of 8 to match visual?
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doShowInfo( {} )").format( event ) )

        text  = self.getEntireText()
        numChars = len( text )
        numLines = len( text.split( '\n' ) )
        numWords = len( text.split() )
        index = self.textBox.index( tk.INSERT )
        atLine, atColumn = index.split('.')

        infoString = 'Current location:\n' \
            + '  Line, Column:\t{}, {}\n'.format( atLine, atColumn ) \
            + '\nFile text statistics:\n' \
            + '  Chars:\t{:,}\n  Lines:\t{:,}\n  Words:\t{:,}\n'.format( numChars, numLines, numWords ) \
            + '\nFile info:\n' \
            + '  Name:\t{}\n'.format( self.filename ) \
            + '  Folder:\t{}\n'.format( self.folderPath ) \
            + '\nSettings:\n' \
            + '  Autocorrect entries:\t{:,}\n  Autocomplete:\t{}\n  Autosave time:\t{} secs\n  Save changes automatically:\t{}'.format( len(self.autocorrectEntries), self.autocompleteMode, round(self.autosaveTime/1000), self.saveChangesAutomatically )

        showinfo( self, _("Window Information"), infoString )
    # end of TextEditWindow.doShowInfo


    def doUndo( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doUndo( {} )").format( event ) )

        try: self.textBox.edit_undo()
        except tk.TclError: showinfo( self, APP_NAME, _("Nothing to undo") )
        self.textBox.update() # force refresh
    # end of TextEditWindow.doUndo


    def doRedo( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doRedo( {} )").format( event ) )

        try: self.textBox.edit_redo()
        except tk.TclError: showinfo( self, APP_NAME, _("Nothing to redo") )
        self.textBox.update() # force refresh
    # end of TextEditWindow.doRedo


    def doDelete( self, event=None ):                         # delete selected text, no save
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doDelete( {} )").format( event ) )

        if not self.textBox.tag_ranges( tk.SEL ):
            showerror( self, APP_NAME, _("No text selected") )
        else:
            self.textBox.delete( tk.SEL_FIRST, tk.SEL_LAST )
    # end of TextEditWindow.doDelete


    def doCut( self, event=None ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doCut( {} )").format( event ) )

        if not self.textBox.tag_ranges( tk.SEL ):
            showerror( self, APP_NAME, _("No text selected") )
        else:
            self.doCopy()                       # save and delete selected text
            self.doDelete()
    # end of TextEditWindow.doCut


    def doPaste( self, event=None ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doPaste( {} )").format( event ) )

        try:
            text = self.selection_get( selection='CLIPBOARD')
        except tk.TclError:
            showerror( self, APP_NAME, _("Nothing to paste") )
            return
        self.textBox.insert( tk.INSERT, text)          # add at current insert cursor
        self.textBox.tag_remove( tk.SEL, START, tk.END )
        self.textBox.tag_add( tk.SEL, tk.INSERT+'-{}c'.format( len(text) ), tk.INSERT )
        self.textBox.see( tk.INSERT )                   # select it, so it can be cut
    # end of TextEditWindow.doPaste


    def getCharactersBeforeCursor( self, charCount=1 ):
        """
        Needed for auto-correct functions.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.getCharactersBeforeCursor( {} )").format( charCount ) )

        previousText = self.textBox.get( tk.INSERT+'-{}c'.format( charCount ), tk.INSERT )
        #print( 'previousText', repr(previousText) )
        return previousText
    # end of TextEditWindow.getCharactersBeforeCursor


    def getWordCharactersBeforeCursor( self, maxCount=4 ):
        """
        Needed for auto-complete functions.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.getWordCharactersBeforeCursor( {} )").format( maxCount ) )

        previousText = self.textBox.get( tk.INSERT+'-{}c'.format( maxCount ), tk.INSERT )
        #print( "previousText", repr(previousText) )
        wordText = ''
        for previousChar in reversed( previousText ):
            if previousChar in self.autocompleteWordChars:
                wordText = previousChar + wordText
            else: break
        #print( 'wordText', repr(wordText) )
        return wordText
    # end of TextEditWindow.getWordCharactersBeforeCursor


    ############################################################################
    # Search menu commands
    ############################################################################

    #def xxxdoGotoWindowLine( self, forceline=None):
        #line = forceline or askinteger( APP_NAME, _("Enter line number") )
        #self.textBox.update()
        #self.textBox.focus()
        #if line is not None:
            #maxindex = self.textBox.index( tk.END+'-1c' )
            #maxline  = int( maxindex.split('.')[0] )
            #if line > 0 and line <= maxline:
                #self.textBox.mark_set( tk.INSERT, '{}.0'.format(line) ) # goto line
                #self.textBox.tag_remove( tk.SEL, START, tk.END )          # delete selects
                #self.textBox.tag_add( tk.SEL, tk.INSERT, 'insert + 1l' )  # select line
                #self.textBox.see( tk.INSERT )                          # scroll to line
            #else:
                #showerror( self, APP_NAME, _("No such line number") )
    ## end of TextEditWindow.doGotoWindowLine


    #def xxxdoWindowFind( self, lastkey=None):
        #key = lastkey or askstring( APP_NAME, _("Enter search string") )
        #self.textBox.update()
        #self.textBox.focus()
        #self.lastfind = key
        #if key:
            #nocase = self.optionsDict['caseinsens']
            #where = self.textBox.search( key, tk.INSERT, tk.END, nocase=nocase )
            #if not where:                                          # don't wrap
                #showerror( self, APP_NAME, _("String not found") )
            #else:
                #pastkey = where + '+%dc' % len(key)           # index past key
                #self.textBox.tag_remove( tk.SEL, START, tk.END )         # remove any sel
                #self.textBox.tag_add( tk.SEL, where, pastkey )        # select key
                #self.textBox.mark_set( tk.INSERT, pastkey )           # for next find
                #self.textBox.see( where )                          # scroll display
    ## end of TextEditWindow.doWindowFind


    #def xxxdoWindowRefind( self ):
        #self.doWindowFind( self.lastfind)
    ## end of TextEditWindow.doWindowRefind


    def doWindowFindReplace( self ):
        """
        Non-modal find/change dialog
        2.1: pass per-dialog inputs to callbacks, may be > 1 change dialog open
        """
        newPopupWindow = tk.Toplevel( self )
        newPopupWindow.title( '{} - change'.format( APP_NAME ) )
        Label( newPopupWindow, text='Find text?', relief=tk.RIDGE, width=15).grid( row=0, column=0 )
        Label( newPopupWindow, text='Change to?', relief=tk.RIDGE, width=15).grid( row=1, column=0 )
        entry1 = Entry( newPopupWindow )
        entry2 = Entry( newPopupWindow )
        entry1.grid( row=0, column=1, sticky=tk.EW )
        entry2.grid( row=1, column=1, sticky=tk.EW )

        def doWindowFind():                         # use my entry in enclosing scope
            self.doWindowFind( entry1.get() )         # runs normal find dialog callback

        def onApply():
            self.onDoChange( entry1.get(), entry2.get() )

        Button( newPopupWindow, text='Find',  command=doWindowFind ).grid(row=0, column=2, sticky=tk.EW )
        Button( newPopupWindow, text='Apply', command=onApply).grid(row=1, column=2, sticky=tk.EW )
        newPopupWindow.columnconfigure( 1, weight=1 )      # expandable entries
    # end of TextEditWindow.doWindowFindReplace


    def onDoChange( self, findtext, changeto):
        """
        on Apply in change dialog: change and refind
        """
        if self.textBox.tag_ranges( tk.SEL ):                      # must find first
            self.textBox.delete( tk.SEL_FIRST, tk.SEL_LAST)
            self.textBox.insert( tk.INSERT, changeto)             # deletes if empty
            self.textBox.see( tk.INSERT )
            self.doWindowFind( findtext )                          # goto next appear
            self.textBox.update() # force refresh
    # end of TextEditWindow.onDoChange


    ############################################################################
    # Utilities, useful outside this class
    ############################################################################

    def setFolderPath( self, newFolderPath ):
        """
        Store the folder path for where our files will be.

        We're still waiting for the filename.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.setFolderPath( {} )").format( repr(newFolderPath) ) )
            assert self.filename is None
            assert self.filepath is None

        self.folderPath = newFolderPath
    # end of TextEditWindow.setFolderPath

    def setFilename( self, filename, createFile=False ):
        """
        Store the filepath to our file.

        A complement to the above function.

        Also gets the file size and last edit time so we can detect if it's changed later.

        Returns True/False success flag.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.setFilename( {} )").format( repr(filename) ) )
            assert self.folderPath

        self.filename = filename
        self.filepath = os.path.join( self.folderPath, self.filename )
        if createFile: # Create a blank file
            with open( self.filepath, mode='wt', encoding='utf-8' ) as theBlankFile: pass # write nothing
        return self._checkFilepath()
    # end of TextEditWindow.setFilename

    def setPathAndFile( self, folderPath, filename ):
        """
        Store the filepath to our file.

        A more specific alternative to the above two functions. (The other alternative function is below.)

        Also gets the file size and last edit time so we can detect if it's changed later.

        Returns True/False success flag.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.setPathAndFile( {}, {} )").format( repr(folderPath), repr(filename) ) )

        self.folderPath, self.filename = folderPath, filename
        self.filepath = os.path.join( self.folderPath, self.filename )
        return self._checkFilepath()
    # end of TextEditWindow.setPathAndFile

    def setFilepath( self, newFilePath ):
        """
        Store the filepath to our file. (An alternative to the above function.)

        Also gets the file size and last edit time so we can detect if it's changed later.

        Returns True/False success flag.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.setFilepath( {!r} )").format( newFilePath ) )

        self.filepath = newFilePath
        self.folderPath, self.filename = os.path.split( newFilePath )
        return self._checkFilepath()
    # end of TextEditWindow.setFilepath

    def _checkFilepath( self ):
        """
        Checks to make sure that the file can be found and opened.

        Also gets the file size and last edit time so we can detect if it's changed later.

        Returns True/False success flag.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow._checkFilepath()") )

        if not os.path.isfile( self.filepath ):
            showerror( self, APP_NAME, _("No such file path: {!r}").format( self.filepath ) )
            return False
        if not os.access( self.filepath, os.R_OK ):
            showerror( self, APP_NAME, _("No permission to read {!r} in {!r}").format( self.filename, self.folderPath ) )
            return False
        if not os.access( self.filepath, os.W_OK ):
            showerror( self, APP_NAME, _("No permission to write {!r} in {!r}").format( self.filename, self.folderPath ) )
            return False

        self.rememberFileTimeAndSize()

        self.refreshTitle()
        return True
    # end of TextEditWindow._checkFilepath


    def rememberFileTimeAndSize( self ):
        """
        Just record the file modification time and size in bytes
            so that we can check later if it's changed on-disk.
        """
        self.lastFiletime = os.stat( self.filepath ).st_mtime
        self.lastFilesize = os.stat( self.filepath ).st_size
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( " rememberFileTimeAndSize: {} {}".format( self.lastFiletime, self.lastFilesize ) )
    # end of TextEditWindow.rememberFileTimeAndSize


    def loadText( self ):
        """
        Opens the file, reads all the data, and sets it into the text box.

        Can also be used to RELOAD the text (e.g., if it has changed on the disk).

        Returns True/False success flag.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.loadText()") )

        self.loading = True
        text = open( self.filepath, 'rt', encoding='utf-8' ).read()
        if text == None:
            showerror( self, APP_NAME, 'Could not decode and open file ' + self.filepath )
            return False
        else:
            self.setAllText( text )
            self.loading = False
            return True
    # end of TextEditWindow.loadText


    def getEntireText( self ):
        """
        This function can be overloaded in super classes
            (where the edit window might not display the entire text).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.getEntireText()") )

        return self.getAllText()
    # end of TextEditWindow.getEntireText


    def checkForDiskChanges( self, autoloadText=False ):
        """
        Check if the file has changed on disk.

        If it has, and the user hasn't yet made any changes, offer to reload.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.checkForDiskChanges()") )

        if self.filepath and os.path.isfile( self.filepath ) \
        and ( ( self.lastFiletime and os.stat( self.filepath ).st_mtime != self.lastFiletime ) \
          or ( self.lastFilesize and os.stat( self.filepath ).st_size != self.lastFilesize ) ):
            if self.modified():
                showerror( self, APP_NAME, _("File {} has also changed on disk").format( repr(self.filename) ) )
            else: # We haven't modified the file since loading it
                yndResult = False
                if autoloadText: yndResult = True
                else: # ask the user
                    ynd = YesNoDialog( self, _("File {} has changed on disk. Reload?").format( repr(self.filename) ), title=_('Reload?') )
                    #print( "yndResult", repr(ynd.result) )
                    if ynd.result == True: yndResult = True # Yes was chosen
                if yndResult:
                    self.loadText() # reload
            self.rememberFileTimeAndSize()
        self.after( CHECK_DISK_CHANGES_TIME, self.checkForDiskChanges ) # Redo it so we keep checking
    # end if TextEditWindow.checkForDiskChanges


    def doSaveAs( self, event=None ):
        """
        Called if the user requests a saveAs from the GUI.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doSaveAs( {} )").format( event ) )

        if self.modified():
            saveAsFilepath = asksaveasfilename( parent=self )
            #print( "saveAsFilepath", repr(saveAsFilepath) )
            if saveAsFilepath:
                if self.setFilepath( saveAsFilepath ):
                    self.doSave()
    # end of TextEditWindow.doSaveAs

    def doSave( self, event=None ):
        """
        Called if the user requests a save from the GUI.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doSave( {} )").format( event ) )

        if self.modified():
            if self.folderPath and self.filename:
                filepath = os.path.join( self.folderPath, self.filename )
                allText = self.getEntireText() # from the displayed edit window
                with open( filepath, mode='wt', encoding='utf-8' ) as theFile:
                    theFile.write( allText )
                self.rememberFileTimeAndSize()
                self.textBox.edit_modified( tk.FALSE ) # clear Tkinter modified flag
                #self.bookTextModified = False
                self.refreshTitle()
            else: self.doSaveAs()
    # end of TextEditWindow.doSave


    def doAutosave( self ):
        """
        Called on a timer to save a copy of the file in a separate location
            if it's been modified.

        Also saves a daily copy of the file into a sub-folder.

        Schedules another call.

        Doesn't use a hidden folder for the autosave files so the user can find them:
            If a save has been done, an AutoSave folder is created in the save folder,
            if not, the AutoSave folder is created in the home folder.
                (Yes, this can result in old AutoSave files in the home folder.)
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.doAutosave()") )

        if self.modified():
            partialAutosaveFolderPath = self.folderPath if self.folderPath else self.parentApp.homeFolderPath
            # NOTE: Don't use a hidden folder coz user might not be able to find it
            autosaveFolderPath = os.path.join( partialAutosaveFolderPath, 'AutoSave/' ) \
                                    if APP_NAME in partialAutosaveFolderPath \
                                    else os.path.join( partialAutosaveFolderPath, APP_NAME+'/', 'AutoSave/' )
            if not os.path.exists( autosaveFolderPath ): os.makedirs( autosaveFolderPath )
            lastDayFolderPath = os.path.join( autosaveFolderPath, 'LastDay/' )
            if not os.path.exists( lastDayFolderPath ): os.mkdir( lastDayFolderPath )

            autosaveFilename = self.filename if self.filename else 'Autosave.txt'
            #print( 'autosaveFolderPath', repr(autosaveFolderPath), 'autosaveFilename', repr(autosaveFilename) )
            autosaveFilepath = os.path.join( autosaveFolderPath, autosaveFilename )
            lastDayFilepath = os.path.join( lastDayFolderPath, autosaveFilename )

            # Check if we need a daily save
            if os.path.isfile( autosaveFilepath ) \
            and ( not os.path.isfile( lastDayFilepath ) \
            or datetime.fromtimestamp( os.stat( lastDayFilepath ).st_mtime ).date() != datetime.today().date() ):
            #or not self.filepath \
                print( "doAutosave: saving daily file", lastDayFilepath )
                shutil.copyfile( autosaveFilepath, lastDayFilepath ) # We save a copy of the PREVIOUS autosaved file

            # Now save this updated file
            allText = self.getEntireText() # from the displayed edit window and/or elsewhere
            with open( autosaveFilepath, mode='wt', encoding='utf-8' ) as theFile:
                theFile.write( allText )
            self.after( self.autosaveTime, self.doAutosave )
        else:
            self.autosaveScheduled = False # Will be set again by refreshTitle
    # end of TextEditWindow.doAutosave


    def doViewSettings( self ):
        """
        Open a pop-up text window with the current settings displayed.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doViewSettings()") )
            self.parentApp.setDebugText( "doViewSettings…" )
        tEW = TextEditWindow( self.parentApp )
        #if windowGeometry: tEW.geometry( windowGeometry )
        if not tEW.setFilepath( self.settings.settingsFilepath ) \
        or not tEW.loadText():
            tEW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open settings file") )
            if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Failed doViewSettings" )
        else:
            self.parentApp.childWindows.append( tEW )
            if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Finished doViewSettings" )
        self.parentApp.setReadyStatus()
    # end of TextEditWindow.doViewSettings


    def doViewLog( self ):
        """
        Open a pop-up text window with the current log displayed.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule: print( exp("doViewLog()") )
            self.parentApp.setDebugText( "doViewLog…" )

        filename = ProgName.replace('/','-').replace(':','_').replace('\\','_') + '_log.txt'
        tEW = TextEditWindow( self.parentApp )
        #if windowGeometry: tEW.geometry( windowGeometry )
        if not tEW.setPathAndFile( self.parentApp.loggingFolderPath, filename ) \
        or not tEW.loadText():
            tEW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open log file") )
            if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Failed doViewLog" )
        else:
            self.parentApp.childWindows.append( tEW )
            #if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished doViewLog" ) # Don't do this -- adds to the log immediately
        self.parentApp.setReadyStatus()
    # end of TextEditWindow.doViewLog


    #def doCloseEditor( self, event=None ):
        #"""
        #Called if the user requests a close from the GUI.
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("TextEditWindow.doCloseEditor( {} )").format( event ) )

        #self.onCloseEditor()
    ## end of TextEditWindow.closeEditor

    def doClose( self, event=None ):
        """
        Called if the window is about to be destroyed.

        Determines if we want/need to save any changes.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("TextEditWindow.doClose( {} )").format( event ) )

        if self.modified():
            saveWork = False
            if self.saveChangesAutomatically and self.folderPath and self.filename:
                #self.doSave( 'Auto from win close' )
                #self.closeChildWindow()
                saveWork = True
            else:
                #if self.folderPath and self.filename:
                    #self.doSave()
                    #self.closeChildWindow()
                #else: # we need to ask where to save it
                place = 'in {}'.format( self.filename) if self.folderPath and self.filename else ''
                ocd = OkCancelDialog( self, _('Do you want to save your work{}?').format( place ), title=_('Save work?') )
                #print( "ocdResult", repr(ocd.result) )
                if ocd.result == True: # Yes was chosen
                    saveWork = True
                else:
                    place = 'to {}'.format( self.filename) if self.folderPath and self.filename else ''
                    ynd = YesNoDialog( self, _('Are you sure you want to lose your changes?').format( place ), title=_('Lose changes?') )
                    #print( "yndResult", repr(ynd.result) )
                    if ynd.result == True: # Yes was chosen
                        self.textBox.edit_modified( tk.FALSE ) # clear Tkinter modified flag
                        self.bookTextModified = False
                    #else: saveWork = True
            if saveWork:
                self.doSave()
                if self.folderPath and self.filename: # assume we saved it
                    ChildWindow.doClose( self )
                    return

        if not self.modified():
            #print( "HEREEEEEEEEE" )
            ChildWindow.doClose( self )
    # end of TextEditWindow.doClose
# end of TextEditWindow class



def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( exp("Running demo…") )

    tkRootWindow = tk.Tk()
    tkRootWindow.title( ProgNameVersion )
    tkRootWindow.textBox = tk.Text( tkRootWindow )

    tEW = TextEditWindow( tkRootWindow )

    # Start the program running
    tkRootWindow.mainloop()
# end of TextEditWindow.demo


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        #from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", tk.TclVersion )
        print( "TkVersion is", tk.TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of TextEditWindow.py