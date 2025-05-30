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

datafolder = './data/'

def mouseto(x, y, sleep=.05):
    # Move cursor to (x, y)
    win32api.SetCursorPos((x, y))
    time.sleep(sleep*random.random())  # slight delay to ensure cursor position is updated

def mouseclick(x, y, sleep=.05):
    # Simulate left mouse button click
    mouseto(x, y)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(sleep*random.random())  # slight delay to ensure click is registered

def scroll( x, y, dwData=-30, dwExtraInfo=0 ):
    """Scroll in the given position"""
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, x, y, dwData, dwExtraInfo)

def press_end_key(sleep=1):
    win32api.keybd_event(win32con.VK_END, 0, 0, 0)  # Key down
    time.sleep(0.05*random.random())
    win32api.keybd_event(win32con.VK_END, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
    time.sleep(sleep*random.random())

def press_home_key(sleep=1):
    win32api.keybd_event(win32con.VK_HOME, 0, 0, 0)  # Key down
    time.sleep(0.05*random.random())
    win32api.keybd_event(win32con.VK_HOME, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
    time.sleep(sleep*random.random())

def press_pagedown(sleep=1):
    # Press the PageDown key
    win32api.keybd_event(win32con.VK_NEXT, 0, 0, 0)        # Key down
    time.sleep(0.05*random.random())                                       # Short delay
    win32api.keybd_event(win32con.VK_NEXT, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
    time.sleep(sleep*random.random())

def press_pageup( sleep=1 ):
    # Press the PageUp key
    win32api.keybd_event(win32con.VK_PRIOR, 0, 0, 0)       # Key down
    time.sleep(0.05*random.random())                                       # Short delay
    win32api.keybd_event(win32con.VK_PRIOR, 0, win32con.KEYEVENTF_KEYUP, 0) # Key up
    time.sleep(sleep*random.random())

def screenscroll( rect, notches, sleep=.05 ):
    x, y, width, height = rect
    xs, ys = random.randint(x, width), random.randint(y, height)
    # Scroll down
    mouseclick(xs, ys)  # Focus screen
    for _ in range(notches):
        xs, ys = random.randint(x, width), random.randint(y, height)
        scroll(xs, ys)
        time.sleep(sleep*random.random())

def screengrab( rect ):
    """ Given a rectangle, return a PIL Image of that part of the screen.
    Handles a Linux installation with and older Pillow by falling-back
    to using XLib """

    # Grab bbox
    x, y, width, height = rect
    img = ImageGrab.grab( bbox=[ x, y, x+width, y+height ] )

    return img

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

def save_txt(text, filename):
    """Save the text to a .txt file"""
    with open(f"{datafolder}{filename}.txt", 'w', encoding='utf-8') as f:
        f.write(text)

def load_txt(filename):
    """Load text from a .txt file"""
    with open(f"{datafolder}{filename}.txt", 'r', encoding='utf-8') as f:
        text = f.read()
    return text
