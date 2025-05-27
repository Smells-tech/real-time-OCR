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
from error_correction import OCRMerger
from lib import *

def multithread(args):
    """Multithread"""
    # Create a queue to store screen captures
    screen_capture_queue = Queue()

    # Define the screen capture thread
    def screen_capture_thread(screen_rect, fps) -> None:
        """Continuous screen capture thread"""

        # Forever loop
        while True:
            image = screengrab(screen_rect)
            screen_capture_queue.put(image)
            time.sleep(1 / fps)  # adjust the FPS here

    # Define the OCR processing thread
    def ocr_processing_thread(max_errors, verbose=False, final_text=False, title='output') -> None:
        """OCR processing thread"""
        store = ""
        while True:
            image = screen_capture_queue.get()
            text = pytesseract.image_to_string(image)
            # process the text here
            screen_capture_queue.task_done()
            # Create and start the threads

            # Strip
            text = text.strip()

            # Match and align to store
            if max_errors>0:
                errors = int(max_errors*len(text))
                reduced = fuzzymerge_overlapping_strings(store, text, max_errors=errors)
            else:
                reduced = merge_overlapping_strings(store, text)
            
            # Merge with store
            store+=reduced

            # Save to .txt file
            save_text(store, f"{title}.txt")

            # Print to console
            if verbose:
                split = text.split()
                print(" ".join(split[:10]))
                print(" ".join(split[-10:]))

            if final_text:
                if fuzzy_contains(text, final_text, max_errors=max_errors):
                    close()

    ### Loop forever, monitoring the user-specified rectangle of the screen
    screen_capture_thread = threading.Thread(
        target=screen_capture_thread,
        args=(
            args.screen_rect,
            args.fps,
            )
        )
    ocr_processing_thread = threading.Thread(
        target=ocr_processing_thread,
        kwargs={
            'verbose': args.verbose,
            'max_errors': args.max_errors,
            'final_text': args.final_text,
            'title':args.title
            }
        )

    # Start the threads
    try:
        screen_capture_thread.start()
        ocr_processing_thread.start()
    except Exception as e:
        print(e)
        sys.exit(1)


def sequential(args):
    """Sequential bookreader"""

    # Conditional loop
    store = ""
    finished = False
    while finished is False:

        # Grab screen
        image = screengrab(args.screen_rect, notchpixels=args.notchpixels)

        # Extract text
        text = pytesseract.image_to_string(image)

        # Strip
        text = text.strip()

        # Match and align to store
        if args.max_errors>0:
            reduced = fuzzymerge_overlapping_strings(
                store,
                text,
                max_errors=int(args.max_errors*len(text))
                )
        else:
            reduced = merge_overlapping_strings(
                store,
                text
                )
        store+=reduced

        # Save to .txt file
        save_text(store, f"{args.title}.txt")

        # Print to console
        if args.verbose:
            print(" ".join(text.split()[-15:]))

        # Assert condition
        if args.final_text:
            finished = fuzzy_contains(
                text,
                args.final_text,
                max_errors=int(args.max_errors*len(args.final_text))
                )

    # Close off
    close()

def grablast(args):
    """
    Take a screenshot of the final page,
    extract all text and store for use in asserting final state
    """
    if args.verbose:
        print('Scrolling down to extract final text')

    x, y, width, height = args.screen_rect
    xs, ys = random.randint(x, width), random.randint(y, height)

    # PageDown
    if args.homekeys:
        press_end_key()
    else:
        for _ in range(50):
            scroll(xs, ys, dwData=int(-2**30))
            time.sleep(.05*random.random())

    time.sleep(.5+random.random())

    # Grab screen
    image = screengrab(args.screen_rect, dwData=0)

    # Extract text
    text = pytesseract.image_to_string(image)

    # Strip
    text = text.strip()

    if args.verbose:
        print(f'Extracted final text:\n{text}\n')
        print('Scrolling up')

    # PageUp
    if args.homekeys:
        press_home_key()
    else:
        for _ in range(50):
            scroll(xs, ys, dwData=int(2**30))
            time.sleep(.05+random.random())

    time.sleep(.5+random.random())

    return text

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
    parser.add_argument(
        "--fps",
        help="Set FPS value for multithreading, default is False",
        default=False,
        type=int
        )
    parser.add_argument(
        "--notchpixels",
        help="Set scroll negative offset relative to a full screen scroll, default is .1",
        default=55,
        type=float
        )
    parser.add_argument(
        "--verbose",
        help="Verbose output",
        action='store_true'
        )
    parser.add_argument(
        "--max_errors",
        help="Errors allowed for matching text as a fraction of smallest text length, default is .1",
        default=.05,
        type=float
        )
    parser.add_argument(
        "--final_text",
        help="The last line you're expecting to read. Script will finish when a match is found. Default is False: script starts by extracting final text",
        type=str,
        default=False
        )
    parser.add_argument(
        "--title",
        help="Title of the document to read.",
        type=str
        )
    parser.add_argument(
        "--homekeys",
        help="The home and end keys work; they reach the bodem and top of the document.",
        action='store_false'
        )
    parser.add_argument(
        "--pages",
        help="Number of pages to scroll to the bottom, default is 100",
        type=int,
        default=10
        )
    parser.add_argument(
        "screen_rect",
        help="x y w h coördinates of the bounding box to screen grab",
        nargs ="*",
        type=int,
        default=[0, 0, screen_width, screen_height]
        )
    args=parser.parse_args()

    print('Homekeys as Parsed: ', args.homekeys)

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

    # Area of screen to monitor
    print( EXE + ": watching " + str( args.screen_rect ) )
    print( "Verbose: " + str( args.verbose ) )
    print( "Negative scroll offset relative to a full screen scroll: " + str( args.notchpixels ) )
    print( "Maximum errors in fuzzy string matching: " + str( args.max_errors ) )

    # Countdown
    downfrom = 5
    for i in range(downfrom, 0, -1):
        print(f"Starting in {i} seconds...", flush=True, end="\r")
        time.sleep(1)
    print()

    if not args.final_text:
        args.final_text = grablast(args)

    if args.fps is not False:
        multithread(args)
    else:
        sequential(args)

if __name__ == "__main__":
    main()
