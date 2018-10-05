import os
import sys

#  Add this directory to the path in GDB so import will work
path, filename = os.path.split(__file__)
if not path in sys.path:
    sys.path.append(path)
import gdb
import gdb_helpers as gdbh
import hexbox_app_support
import re

STACK_REGION_NAME = '.stack'
HEAP_REGION_NAME = '._user_heap_stack'
BLOCK_SIZE = 128
MARK_VALUE = 0xFEEDABCD
MARK_ARRAY = "{"+",".join([str(MARK_VALUE)]*BLOCK_SIZE)+"}"

HEXBOX_EMULATOR_STACK = '__hexbox_emulator_stack'
EMULATOR_STACK_SIZE = 200
HEXBOX_COMPARTMENT_STACK = 'hexbox_comp_stack'
COMP_STACK_SIZE = 16 # number of uint32_t thes address is





def check_var_usage(var_name, length, element_size, compare_value=0):
    '''
        Checks how much of the variable is used, starts at the end
        and moves toward beginning returns amount remaining
    '''
    offsets = range(length)
    offsets.reverse()
    for idx, offset in enumerate(offsets):
        v = gdbh.get_value_at_symbol(var_name+"+%i" % offset)
        if v != compare_value:
            return (len(offsets) - idx) * element_size
    return 0

def fill_section(section_name):
    start, end = gdbh.get_section_start_and_end(section_name)
    for block_addr in xrange(start, end, BLOCK_SIZE*4):
        gdb.execute("set {unsigned int[%s]}%s = %s" %
                    (BLOCK_SIZE,block_addr,MARK_ARRAY))


def check_section(section_name, reverse=False):
    '''
        Goes through section to determine where the mark value ends
        If reverse is true goes from highest address to lowest
        Else goes from lowest value to highest
    '''
    start, end = gdbh.get_section_start_and_end(section_name)
    addrs = range(start, end, 4)
    if reverse:
        addrs.reverse()
    for idx, addr  in enumerate(addrs):
        value = gdbh.get_mem(addr)
        if value != MARK_VALUE:
            size = (len(addrs)-idx) * 4
            return size
    return 0

def measure_stacks(hexbox=True):
    '''
        Determines how much of stack was used by looking for
        area not filled with predetermined ValueError

        Use setup_stacks_for_measuring() to init stacks for measuring their
        size
    '''
    stack_size = check_section(STACK_REGION_NAME)
    heap_size  = check_section(HEAP_REGION_NAME, True)
    print ("Stack Size: %s, Heap_Size %s" % (stack_size, heap_size))
    if hexbox:
        emulator_stack = check_var_usage(HEXBOX_EMULATOR_STACK,
                                         EMULATOR_STACK_SIZE, 4)
        compartment_stack = check_var_usage(HEXBOX_COMPARTMENT_STACK,
                                            COMP_STACK_SIZE, 16)
        print ("Compartment Size: %s, Emulator_Size %s" %
               (compartment_stack, emulator_stack))
        return (stack_size, heap_size, emulator_stack, compartment_stack)

    return (stack_size, heap_size)


def setup_stacks_for_measuring(hexbox=True):
    '''
        Setups stacks for measuring by filling with specific values
    '''
    fill_section(STACK_REGION_NAME)
    fill_section(HEAP_REGION_NAME)
    if hexbox:
        gdb.execute('set %s = {0}' % HEXBOX_EMULATOR_STACK)
        gdb.execute('set %s = {{0}}' % HEXBOX_COMPARTMENT_STACK)


# class MeasureBreakpoint(gdb.Breakpoint):
#     def stop(self):
#         measure_stacks()
#         return True  # Won't execute
#
#
# brkpt = hexbox_app_support.get_breakpoint()
#
# MeasureBreakpoint(brkpt, type=gdb.BP_BREAKPOINT)
# setup_stacks_for_measuring()
# gdbh.c()
