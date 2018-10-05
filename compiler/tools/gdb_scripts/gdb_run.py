import os
import sys

#  Add this directory to the path in GDB so import will work
path, filename = os.path.split(__file__)
if not path in sys.path:
    sys.path.append(path)
import gdb
import gdb_helpers
import gdb_measure_stacks as stack_measure
import hexbox_app_support

RESULTS_DIR = "timing_results"
filename_w_ext = gdb_helpers.get_filename()
filename, ext = os.path.splitext(filename_w_ext)

r_file = os.path.join(RESULTS_DIR, filename + '--timing.csv')
summary_file = os.path.join(RESULTS_DIR, filename + '--timing_summary.csv')
if not os.path.exists(RESULTS_DIR):
    os.mkdir(RESULTS_DIR)

brkpt = hexbox_app_support.get_breakpoint()

gdb_helpers.cl()
hexbox = 'hexbox' in filename
stack_measure.setup_stacks_for_measuring(hexbox)
bp = gdb_helpers.EndBreakpoint(brkpt, type=gdb.BP_BREAKPOINT)
bp.set_params(r_file, summary_file, stack_measure.measure_stacks, limit=3)
print "BP Set, Running"
gdb.execute('c')
