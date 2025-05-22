"""Library for screen capture and text processing."""
from PIL import ImageGrab

def screengrab( rect ):
    """ Given a rectangle, return a PIL Image of that part of the screen.
    Handles a Linux installation with and older Pillow by falling-back
    to using XLib """
    x, y, width, height = rect
    img = ImageGrab.grab( bbox=[ x, y, x+width, y+height ] )
    return img

def merge_strings_remove_overlap(str1, str2):
    """Removes any overlap and returns the merged string"""
    min_overlap_len = min(len(str1), len(str2))
    for i in range(min_overlap_len, 0, -1):
        if str1.endswith(str2[:i]):
            return str1 + str2[i:]
    return str1 + str2

def save_text(text, filename):
    """Save the text to a file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
