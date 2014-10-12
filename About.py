#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# About.py
#   Last modified: 2014-10-11 (also update ProgVersion below)
#
# Main program for Biblelator Bible display/editing
#
# Copyright (C) 2014 Robert Hunt
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
Program to allow editing of USFM Bibles using Python3 and Tkinter.
"""

ShortProgName = "About"
ProgName = "About Box"
ProgVersion = "0.16"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = True


import sys #, os.path, configparser, logging
#from gettext import gettext as _

from tkinter import Toplevel #, Text
from tkinter import YES, END, DISABLED
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Button
#from tkinter import tix

sourceFolder = "../BibleOrgSys/"
sys.path.append( sourceFolder )
import Globals

#from ApplicationSettings import ApplicationSettings


def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if Globals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



class AboutBox( Toplevel ):
    def __init__( self, parent=None, progName=None, text=None ):
        #if Globals.debugFlag: print( "AboutBox.__init__( {} )".format( parent ) )
        Toplevel.__init__( self, parent )
        #self.minimumXSize, self.minimumYSize = MINIMUM_X_SIZE, MINIMUM_Y_SIZE
        self.title( 'About '+progName )
        self.textBox = ScrolledText( self ) #, state=DISABLED )
        self.textBox['wrap'] = 'word'
        self.textBox.pack( expand=YES )
        self.textBox.insert( END, text )
        self.textBox['state'] = DISABLED # Don't allow editing

        self.okButton = Button( self, text='Ok', command=self.destroy )
        self.okButton.pack()

        self.focus_set() # take over input focus,
        self.grab_set() # disable other windows while I'm open,
        self.wait_window() # and wait here until win destroyed
    # end of AboutBox.__init__
# end of class AboutBox


class AboutBox2():
    def __init__( self, parent=None, progName=None, text=None ):
        #if Globals.debugFlag: print( "AboutBox2.__init__( {} )".format( parent ) )
        ab = Toplevel( parent )
        #self.minimumXSize, self.minimumYSize = MINIMUM_X_SIZE, MINIMUM_Y_SIZE
        ab.title( 'About '+progName )
        textBox = ScrolledText( ab ) #, state=DISABLED )
        textBox['wrap'] = 'word'
        textBox.pack( expand=YES )
        textBox.insert( END, text )
        self.textBox['state'] = DISABLED # Don't allow editing

        okButton = Button( ab, text='Ok', command=ab.destroy )
        okButton.pack()

        ab.focus_set() # take over input focus,
        ab.grab_set() # disable other windows while I'm open,
        ab.wait_window() # and wait here until win destroyed
    # end of AboutBox.__init__
# end of class AboutBox


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk

    if Globals.verbosityLevel > 0: print( ProgNameVersion )
    #if Globals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    print( "Running demo..." )

    tkRootWindow = Tk()
    if Globals.debugFlag:
        #print( 'Windowing system is', repr( tkRootWindow.tk.call('tk', 'windowingsystem') ) )
        for name in ('appname', 'inactive', 'scaling', 'useinputmethods', 'windowingsystem' ): # 'busy', 'caret', 'fontchooser',
            print( 'Tkinter {} is {}'.format( name, repr( tkRootWindow.tk.call('tk', name) ) ) )
    tkRootWindow.title( ProgNameVersion )
    ab = AboutBox( tkRootWindow, ProgName, ProgNameVersion )
    ab = AboutBox2( tkRootWindow, ProgName, ProgNameVersion )
    # Calls to the window manager class (wm in Tk)
    #tkRootWindow.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()
# end of main


if __name__ == '__main__':
    import multiprocessing

    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables


    if Globals.debugFlag:
        from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of About.py