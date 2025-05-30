""" Lala """
# default
import sys
import argparse
import tkinter as tk
import threading
from queue import Queue
import time
import random
# env
import pytesseract
# local
from error_correction import *
from controls import *
from timer import tracker

Merger = OCRMerger()

def sequential(args):
    """Sequential bookreader"""

    # Position
    x, y, width, height = args.screen_rect
    # Mouse wheel 'notches' till full screen
    rad = height-y
    notches = math.floor(rad/args.notchpixels)

    # Conditional loop
    store = ""
    finished = False
    prevtail = ""
    while finished is False:

        tracker.start('Loop')
        tracker.start('From screengrab to string')

        # Grab screen
        image = screengrab(args.screen_rect)

        # Extract text
        ocr = pytesseract.image_to_string(image)

        tracker.stop('From screengrab to string')

        # Split into words
        ocr = ocr.strip()

        # Store window to use as input to the alignment process
        window = int(len(ocr) * args.window)

        # Match and align to store
        if len(store)>0:

            tracker.start('align_sequences')

            amalgamation = Merger.align_sequences(store[-window:], ocr)
            store = store[:-window] + amalgamation

            tracker.stop('align_sequences')

        else:
            store = ocr

        tracker.start('Save up')

        # Save to .txt file
        save_txt(store, args.title)

        # Scroll down
        screenscroll(args.screen_rect, notches)
        
        # Correct last 10% of OCR text
        ocrtail = Merger.correction( ocr[int( -.1 * len(ocr) ):] )

        # Compare ocr tail to previous tail
        finished = fuzzy_contains(
            prevtail,
            ocrtail,
            max_error=int(args.max_error*len(args.final_text))
        )

        prevtail = ocrtail

        tracker.stop('Save up')
        tracker.stop('Loop')

        tracker.boxplot()

    # Close off
    close()

def main():
    """
    Do some rudimentary command line argument handling
    so the user can speicify the area of the screen to watch
    """
    EXE = sys.argv[0]

    # Get the size of the screen
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Parse CL arguments
    parser=argparse.ArgumentParser()

    # Verbose output
    parser.add_argument(
        "--verbose",
        help="Verbose output",
        action='store_true'
        )

    # Document title
    parser.add_argument(
        "--title",
        help="Title of the .txt output file. Default is 'output'",
        default="output",
        type=str
        )

    # Scroll distance
    notchpixels=45
    parser.add_argument(
        "--notchpixels",
        help=f"Amount of pixels that correspond to a single 'click' of the scrollwheel. Default = {notchpixels}",
        default=notchpixels,
        type=float
        )

    # Alignment window
    window = 1.05
    parser.add_argument(
        "--window",
        help=f"The 'window' for aligning new sequences to the currect store, as a fraction of the new sequence length, default is {window}",
        default=window,
        type=float
        )

    # Bounding box
    parser.add_argument(
        "screen_rect",
        help="x y w h coördinates of the bounding box to screen grab",
        nargs ="*",
        type=int,
        default=[0, 0, screen_width, screen_height]
        )
    args=parser.parse_args()

    # Check the arguments
    if len(args.screen_rect) != 4:
        sys.stderr.write(
            EXE +
            ": monitors section of screen for text\n"
            )
        sys.stderr.write(
            EXE +
            ": Give x, y, width, height as arguments, or leave blanc to monitor the whole screen\n"
            )
        sys.exit(1)

    # Countdown
    downfrom = 5
    if args.verbose:
        print(f'Verbose is {args.verbose}')
    for i in range(downfrom, 0, -1):
        print(f"Starting in {i} seconds...", flush=True, end="\r")
        time.sleep(1)
    print()

    sequential(args)

if __name__ == "__main__":
    main()
