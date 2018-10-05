import os
import sys

#  Add this directory to the path in GDB so import will work
path, filename = os.path.split(__file__)
if not path in sys.path:
    sys.path.append(path)
import gdb
import gdb_helpers
import hexbox_app_support


class RecordBreakpoint(gdb.Breakpoint):
    def stop(self):
        print "Wrote Mem Data"
        gdb_helpers.record_memory()
        gdb.execute('quit')
        return True  # Won't execute


brkpt = hexbox_app_support.get_breakpoint()

RecordBreakpoint(brkpt, type=gdb.BP_BREAKPOINT)

gdb_helpers.cl()
gdb.execute('c')
