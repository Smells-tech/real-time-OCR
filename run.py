#! /usr/bin/env python3

import sys
import pytesseract
import PIL
from PIL import Image

def screenGrab( rect ):
    """ Given a rectangle, return a PIL Image of that part of the screen.
        Handles a Linux installation with and older Pillow by falling-back
        to using XLib """
    x, y, width, height = rect
    img = PIL.ImageGrab.grab( bbox=[ x, y, x+width, y+height ] )
    return img

### Do some rudimentary command line argument handling
### So the user can speicify the area of the screen to watch
if __name__ == "__main__":
    EXE = sys.argv[0]
    del sys.argv[0]

    # EDIT: catch zero-args
    if len( sys.argv ) != 4 or sys.argv[0] in ( '--help', '-h', '-?', '/?' ):  # some minor help
        sys.stderr.write( EXE + ": monitors section of screen for text\n" )
        sys.stderr.write( EXE + ": Give x, y, width, height as arguments\n" )
        sys.exit( 1 )

    # TODO add error checking
    x      = int( sys.argv[0] )
    y      = int( sys.argv[1] )
    width  = int( sys.argv[2] )
    height = int( sys.argv[3] )

    # Area of screen to monitor
    screen_rect = [ x, y, width, height ]
    print( EXE + ": watching " + str( screen_rect ) )

    ### Loop forever, monitoring the user-specified rectangle of the screen
    while True:
        image = screenGrab( screen_rect )              # Grab the area of the screen
        text  = pytesseract.image_to_string( image )   # OCR the image

        # IF the OCR found anything, write it to stdout.
        text = text.strip()
        if len( text ) > 0:
            print( text )
