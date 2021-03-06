#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ModalDialog.py
#
# Framework for modal dialogs for the Biblelator program.
#
# Adapted from: http://effbot.org/tkinterbook/tkinter-dialog-windows.htm
#
# Copyright (C) 2014-2017 Robert Hunt
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
Framework for modal dialogs for the Biblelator program.
"""

from gettext import gettext as _

LastModifiedDate = '2017-04-10' # by RJH
ShortProgName = "ModalDialog"
ProgName = "Modal Dialog"
ProgVersion = '0.40'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import tkinter as tk
from tkinter.ttk import Frame, Button

if __name__ == '__main__': import sys; sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals



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
    return '{}{}'.format( nameBit, errorBit )
# end of exp



class ModalDialog( tk.Toplevel ):
    """
    A Toplevel window that's a modal dialog
        and intended to be subclassed.
    """
    def __init__(self, parent, title=None, okText=None, cancelText=None):

        tk.Toplevel.__init__( self, parent )
        self.transient( parent )

        self.parent = parent
        if title: self.title( title )

        if okText is None: okText = _("Ok")
        self.okText = okText
        if cancelText is None: cancelText = _("Cancel")
        self.cancelText = cancelText

        self.result = None # Used to return an optional result

        body = Frame( self )
        self.initial_focus = self.body( body ) # Create the widgets in the body
        body.pack( padx=5, pady=5 )

        self.buttonBox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol( 'WM_DELETE_WINDOW', self.cancel ) # Ensure that closing the dialog does a cancel

        self.geometry( "+{}+{}".format(parent.winfo_rootx()+50, parent.winfo_rooty()+50) )

        self.parent.parentApp.setStatus( _("Waiting for user input…") )
        self.initial_focus.focus_set()
        self.wait_window( self )
    # end of ModalDialog.__init__


    # construction hooks
    def body( self, master ):
        """
        Create dialog body -- this method must be overridden.

        Returns the widget that should have initial focus.
        """
        if BibleOrgSysGlobals.debugFlag: print( exp("This 'body' method must be overridden!") ); halt
    # end of ModalDialog.body


    def buttonBox( self ):
        """
        Add our standard button box

        Override if you don't want the standard buttons.
        """
        box = Frame( self )

        w = Button( box, text=self.okText, width=10, command=self.ok, default=tk.ACTIVE )
        w.pack( side=tk.LEFT, padx=5, pady=5 )
        w = Button( box, text=self.cancelText, width=10, command=self.cancel )
        w.pack( side=tk.LEFT, padx=5, pady=5 )

        self.bind( '<Return>', self.ok )
        self.bind( '<Escape>', self.cancel )

        box.pack()
    # end of ModalDialog.buttonBox


    #
    # standard button semantics
    def ok( self, event=None ):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()
        self.cancel()
    # end of ModalDialog.ok


    def cancel( self, event=None ):

        # put focus back to the parent window
        self.parent.parentApp.setReadyStatus()
        self.parent.focus_set()
        self.destroy()
    # end of ModalDialog.cancel


    #
    # command hooks
    def validate( self ):
        """
        This method is designed to be overridden
            and is called to check the entered data before the window is destroyed.
        """
        if BibleOrgSysGlobals.debugFlag: print( exp("This 'validate' method can be overridden!") )
        return True # override
    # end of ModalDialog.validate


    def apply( self ):
        """
        This method is designed to be overridden
            and is called to obtain the entered data after the window is destroyed.

        It can optionally put the results into self.result (which otherwise defaults to None).
        """
        if BibleOrgSysGlobals.debugFlag: print( exp("This 'apply' method should be overridden!") )
        self.result = True
    # end of ModalDialog.apply
# end of class ModalDialog



class MyTestDialog( ModalDialog ):

    def body( self, master ):
        """
        Override the empty ModalDialog.body function
            to set up the dialog how we want it.
        """
        from tkinter.ttk import Label, Entry

        Label( master, text="First:" ).grid( row=0 )
        Label( master, text="Second:" ).grid( row=1 )

        self.e1 = BEntry( master )
        self.e2 = BEntry( master )

        self.e1.grid( row=0, column=1 )
        self.e2.grid( row=1, column=1 )
        return self.e1 # initial focus
    # end of MyTestDialog.apply


    def validate( self ):
        """
        Override the empty ModalDialog.validate function
            to check that the results are how we need them.
        """
        try: int( self.e1.get() ) and int( self.e2.get() )
        except ValueError:
            print( "ERROR: We need two valid integers!" )
            return False
        return True
    # end of MyTestDialog.validate


    def apply( self ):
        """
        Override the empty ModalDialog.apply function
            to process the results how we need them.

        Results are left in self.result
        """
        first = int( self.e1.get() )
        second = int( self.e2.get() )
        print( first, second ) # or something
        self.result = (first, second,)
    # end of MyTestDialog.apply
# end of class MyTestDialog



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk

    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    print( "Running demo…" )

    tkRootWindow = Tk()
    tkRootWindow.title( ProgNameVersion )
    tkRootWindow.parentApp = tkRootWindow
    def ss( a ): pass
    tkRootWindow.setStatus = ss
    md = MyTestDialog( tkRootWindow, "Just playing" )
    print( "Result is:", repr(md.result) )

    # Start the program running
    tkRootWindow.mainloop()
# end of main


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables


    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )


    if BibleOrgSysGlobals.debugFlag:
        from tkinter import TclVersion, TkVersion
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of ModalDialog.py
