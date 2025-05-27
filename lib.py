"""Library for screen capture and text processing."""
import time
import re
import sys
import random
import math

from PIL import ImageGrab
import regex
import pyautogui
import win32api
import win32con

def scroll( x, y, dwData=-60, dwExtraInfo=0 ):
    """Scroll in the given position"""
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, x, y, dwData, dwExtraInfo)

def press_end_key(sleep=1):
    win32api.keybd_event(win32con.VK_END, 0, 0, 0)  # Key down
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_END, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
    time.sleep(sleep)

def press_home_key(sleep=1):
    win32api.keybd_event(win32con.VK_HOME, 0, 0, 0)  # Key down
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_HOME, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
    time.sleep(sleep)

def press_pagedown():
    # Press the PageDown key
    win32api.keybd_event(win32con.VK_NEXT, 0, 0, 0)        # Key down
    time.sleep(0.05)                                       # Short delay
    win32api.keybd_event(win32con.VK_NEXT, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up

def press_pageup():
    # Press the PageUp key
    win32api.keybd_event(win32con.VK_PRIOR, 0, 0, 0)       # Key down
    time.sleep(0.05)                                       # Short delay
    win32api.keybd_event(win32con.VK_PRIOR, 0, win32con.KEYEVENTF_KEYUP, 0) # Key up

def screengrab( rect, notchpixels=55, sleep=.05, dwData=-60, dwExtraInfo=0):
    """ Given a rectangle, return a PIL Image of that part of the screen.
    Handles a Linux installation with and older Pillow by falling-back
    to using XLib """

    # Grab bbox
    x, y, width, height = rect
    img = ImageGrab.grab( bbox=[ x, y, x+width, y+height ] )

    # Early return if False or zero
    if not dwData:
        return img

    # Position
    x, y, width, height = rect
    xs, ys = random.randint(x, width), random.randint(y, height)
    # Mouse wheel 'notches' till full screen
    rad = height-y
    notches = math.floor(rad/notchpixels)

    # Scroll down
    for _ in range(notches):
        scroll(xs, ys, dwData, dwExtraInfo)
        time.sleep(sleep*random.random())

    return img

def merge_overlapping_strings(str1, str2):
    """Removes any overlap and returns the merged string"""
    min_overlap_len = min(len(str1), len(str2))
    for i in range(min_overlap_len, 0, -1):
        if str1.endswith(str2[:i]):
            return str2[i:]
    return str2

def fuzzymerge_overlapping_strings(str1, str2, max_errors=1):
    """
    Removes overlap between str1 and str2 allowing up to max_errors
    (insertions, deletions, substitutions) in the overlapping part,
    then merges and returns the combined string.
    """
    min_len = min(len(str1), len(str2))

    # Try from longest possible overlap to shortest
    for overlap_len in range(min_len, 0, -1):
        # Extract the candidate overlap parts
        suffix = str1[-overlap_len:]
        prefix = str2[:overlap_len]

        # Build fuzzy regex pattern for prefix allowing max_errors
        # (?e) enables fuzzy matching, {e<=max_errors} limits errors
        pattern = f'(?e)^{regex.escape(prefix)}{{e<={max_errors}}}$'

        # Check if suffix matches prefix fuzzily within allowed errors
        if regex.match(pattern, suffix):
            # Merge by removing the overlapping part from str2
            return str2[overlap_len:]

    # No fuzzy overlap found, return concatenation
    return str2

def fuzzy_contains(body, target, max_errors=1):
    """
    Returns True if str2 is found within str1 allowing up to max_errors
    (insertions, deletions, substitutions) in the match, else False.
    """
    # Build a fuzzy regex pattern for str2 allowing up to max_errors
    # (?e) enables fuzzy matching, {e<=max_errors} limits errors

    body, target = ''.join(body.split()), ''.join(target.split())

    pattern = f'(?e){regex.escape(target)}{{e<={max_errors}}}'

    # Search for fuzzy match anywhere in str1
    match = regex.search(pattern, body)
    return match is not None

def alttab():
    """Press alt-tab"""
    pyautogui.keyDown('alt')
    time.sleep(.2)
    pyautogui.press('tab')
    time.sleep(.2)
    pyautogui.keyUp('alt')

def close():
    """Close off"""
    alttab()
    sys.exit(1)

def save_text(text, filename):
    """Save the text to a file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
