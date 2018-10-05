import sys
import os
path, filename = os.path.split(__file__)
if not path in sys.path:
    sys.path.append(path)
import gdb_helpers

'''
    Address in here must be updated if any of the the
    files listed are changed
'''

HEXBOX_BREAKPOINT = 'hexbox-rt.c:220'

def get_breakpoint():
    filename_w_ext = gdb_helpers.get_filename()
    filename, ext = os.path.splitext(filename_w_ext)
    app_name = filename.split("--")[0]
    if app_name == "PinLock":
        if 'baseline' in filename:
            brkpt = 'stm32f4xx_it.c:134'
        else:
            brkpt = HEXBOX_BREAKPOINT
    elif app_name == "FatFs-uSD":
        if 'baseline' in filename:
            brkpt = 'stm32f4xx_it.c:130'
        else:
            brkpt = HEXBOX_BREAKPOINT
    elif app_name == "TCP-Echo":
            if 'baseline' in filename:
                brkpt = 'stm32f4xx_it.c:70'
            else:
                brkpt = HEXBOX_BREAKPOINT
    elif app_name == "LCD-uSD":
            if 'baseline' in filename:
                brkpt = 'stm32f4xx_it.c:130'
            else:
                brkpt = HEXBOX_BREAKPOINT
    elif app_name == "Animation":
            if 'baseline' in filename:
                brkpt = 'stm32f4xx_it.c:138'
            else:
                brkpt = HEXBOX_BREAKPOINT
    else:
        print "*" * 80
        print "No File: %s" % app_name
        print "*" * 80
        raise NotImplementedError("Application Not Implemented: %s" % app_name)

    return brkpt
