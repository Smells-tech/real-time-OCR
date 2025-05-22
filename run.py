""" Lala """
# default
import sys, argparse
import tkinter as tk
import threading
from queue import Queue
import time
# env
import pytesseract
# local
from lib import screengrab, merge_strings_remove_overlap, save_text

# Create a queue to store screen captures
screen_capture_queue: Queue = Queue()

# Define the screen capture thread
def screen_capture_thread(screen_rect, fps) -> None:
    """Continuous screen capture thread"""
    while True:
        image = screengrab(screen_rect)
        screen_capture_queue.put(image)
        time.sleep(1 / fps)  # adjust the FPS here

# Define the OCR processing thread
def ocr_processing_thread(verbose=False) -> None:
    """OCR processing thread"""
    store = ""
    while True:
        image = screen_capture_queue.get()
        text = pytesseract.image_to_string(image)
        # process the text here
        screen_capture_queue.task_done()
        # Create and start the threads
        text = text.strip()
        store = merge_strings_remove_overlap(text, store)
        save_text(store, "output.txt")
        if verbose:
            split = text.split()
            print(" ".join(split[:10]))
            print(" ".join(split[-10:]))

### Do some rudimentary command line argument handling
### So the user can speicify the area of the screen to watch
if __name__ == "__main__":

    EXE = sys.argv[0]

    # Get the size of the screen
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Parse CL arguments
    parser=argparse.ArgumentParser()
    parser.add_argument("--fps", help="Set FPS value", default=5, type=int)
    parser.add_argument("--verbose", help="Verbose output", action='store_true')
    parser.add_argument("screen_rect", nargs ="*", type=int, default=[0, 0, screen_width, screen_height])
    args=parser.parse_args()

    # Check the arguments
    if len(args.screen_rect) != 4:
        sys.stderr.write(EXE + ": monitors section of screen for text\n")
        sys.stderr.write(EXE + ": Give x, y, width, height as arguments, or leave blanc to monitor the whole screen\n")
        sys.exit(1)

    # Area of screen to monitor
    print( EXE + ": watching " + str( args.screen_rect ) )
    print( "Verbose: " + str( args.verbose ) )

    ### Loop forever, monitoring the user-specified rectangle of the screen
    screen_capture_thread = threading.Thread(target=screen_capture_thread, args=(args.screen_rect, args.fps))
    ocr_processing_thread = threading.Thread(target=ocr_processing_thread, kwargs={'verbose': args.verbose})

    # Start the threads
    try:
        screen_capture_thread.start()
        ocr_processing_thread.start()
    except Exception as e:
        print(e)
        sys.exit(1)
