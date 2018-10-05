import struct
import collections
import re
import json
import subprocess
from binascii import hexlify

'''
    Takes a recording of accesses that are from running the hexbox recording
    binary and converts it to a asm file.  The ASM file is compiled into
    the final binary and contains the emulators white list
'''

class ObjdumpSymbol(object):
    def __init__(self, addr, size=0, name=None):
        self.name = name
        self.addr = addr
        self.size = size

    def get_bounds(self):
        return (self.addr, self.addr + self.size)

    def addr_in_symbol(self, addr):
        if addr >= self.addr and addr < (self.addr + self.size):
            return True
        else:
            return False

    def __repr__(self):
        return "Name: %s, Addr:0x%08x, Size: %i" % \
               (str(self.name), self.addr, self.size)

    def is_adjacent(self,sym):
        '''
            Checks if addr in symbols is adjacent to this one
        '''
        start_addr, end_addr = sym.get_bounds()
        this_end = self.addr + self.size
        if (self.addr_in_symbol(start_addr) or
            self.addr_in_symbol(end_addr) or
            self.addr == (end_addr) or
            (this_end) == (start_addr)):
           return True
        else:
           return False

    def merge(self, sym):
        if self.is_adjacent(sym):
            start_addr = min([self.addr, sym.addr])
            end_addr = max([(self.addr + self.size), (sym.addr + sym.size)])
            if not self.name is None:
                this_name = self.name
            else:
                this_name = "0x%08x" % self.addr
            if not (sym.name is None):
                sym_name = sym.name
            else:
                sym_name = "0x%08x" % sym.addr
            name = this_name + "_" + sym_name
            return ObjdumpSymbol(start_addr, end_addr-start_addr, name)
        else:
            return None


def gen_symbol_file(elf_file):
    cmd = ['arm-none-eabi-objdump', '-t', elf_file]
    symbol_file = subprocess.check_output(cmd)
    return symbol_file


def write_comp_access_list(outfile, n, acl):
    '''
        Writes the access control list for the compartment

        outfile : file descriptor that is opened ('rt')
        n :       Compartment number
        acl:      Access Controll list, list of ObjdumpSymbols this comp can
                  access
    '''
    name = "__hexbox_comp%i_acl" % n
    declare_str = '''.global %s
.type  %s, %%object
%s:
  .word 0x%x\n''' % (name, name, name, len(acl))
    outfile.write(declare_str)
    #print acl
    for a in sorted(acl, key=lambda x: x.size, reverse=True):
        start_addr, end_addr = a.get_bounds()
        outfile.write("  .word 0x%08x /* %s */\n" % (start_addr, str(a)))
        outfile.write("  .word 0x%08x\n" % end_addr)

    outfile.write("  .size  %s, .-%s\n\n" % (name, name))
    return name


def write_acls_lut(outfile, acls, num_comps):
    '''
        Writes the access control list for the compartment

        outfile : file descriptor that is opened ('rt')
        acls:   list of names for the access control lists of each compartment.
    '''

    name = "__hexbox_acl_lut"
    declare_str = '''.global %s
.type  %s, %%object
%s:\n''' % (name, name, name)
    outfile.write(declare_str)
    for i in xrange(num_comps):
        if i in acls:
            outfile.write("  .word %s\n" % str(acls[i]))
        else:
            outfile.write("  .word 0\n")
    outfile.write("  .size  %s, .-%s\n\n" % (name, name))
    return name


def write_acls_file(accesses, out_filename, num_comps):
    '''
        Writes an assembly file that encodes all the access controls for each
        compartment and a look up table (lut) for them
        accesses : a dictionary of lists of accessed symbols or addresses
        out_filename: filename of where output should be written to
        num_comps: Maximum number of compartments to supported
    '''

    with open(out_filename, 'wt') as outfile:
        outfile.write('.section  .rodata.HexboxAccessList\n\n')
        acls_names = {}
        for comp, acl in accesses.items():
            #print "Comp:", comp, " ACL:", acl
            num = re.search("[0-9]+", comp[1])
            i = int(num.group())
            name = write_comp_access_list(outfile, i, acl)
            acls_names[comp[0]] = name
        write_acls_lut(outfile, acls_names, num_comps)


def find_symbol_for_addr(objdump_list, addr):
    '''
        Finds a matching symbol that contains the address if it exists in
        objdump_list and returns it.

        Otherwise returns None
    '''
    for sym in objdump_list:
        if sym.addr_in_symbol(addr) == True:
            return sym

    return None


def map_to_symbols(accessed_addrs, objdump_symbols):
    '''
        Maps Accessed addrs to objdump_symbols if they are
        access to objdump_symbols
    '''
    accessed_comps = {}

    for comp, access_list in accessed_addrs.items():
        comp_sym = find_symbol_for_addr(objdump_symbols, comp[1])
        if comp_sym:
            key = (comp[0],comp_sym.name)
        else:
            key =comp
        accessed_comps[key] = set()
        for access in access_list:
            found_sym = find_symbol_for_addr(objdump_symbols, access.addr)
            if found_sym:
                accessed_comps[key].add(found_sym)
            else:
                accessed_comps[key].add(access)

    return accessed_comps


def merge_adjacent_symbols(access_list):
    '''
        Goes through list of access/symbols and merges them if contigous
        This reduces the size of the white-lists
        Uses a fixed point algorithm where it goes
    '''
    merged_comps = {}
    for comp, access_list in access_list.items():
        worklist = list(access_list)
        accesses = set()
        while len(worklist) > 0:
            sym = worklist.pop()
            was_merged = False
            for item in worklist:
                merged = sym.merge(item)
                if not merged is None:
                    was_merged = True
                    worklist.remove(item)
                    worklist.append(merged)
                    break
            if not was_merged:
                accesses.add(sym)

        merged_comps[comp] = accesses
    return merged_comps


def parse_memory_recording(memory_filename, buffer_size):
    '''
        Parses raw memory dump of the buffers from hexbox record.
        Get it using GDB after measuring binaries using
        (gdb) dump binary memory <file> 0x10000000 0x1000E000'

        memory_filename: Filename of file from gdb dump
        buffer_size: Size of each compartment buffer used in recording
        returns -> recordings = {(id,compartment_addr):[addr0, addr1],...}}
    '''
    recordings = collections.defaultdict(list)
    with open(memory_filename, 'rb') as infile:
        i = -1
        while True:
            buf = infile.read(buffer_size)
            if (len(buf) != buffer_size):
                break
            i += 1
            if (i * buffer_size) > (62 * 1024):  # Only 62KB is available for recording
                break
            comp_addr = struct.unpack_from("<I", buf)[0]
            
            if comp_addr == 0:
                continue
            
            for s in xrange(4, buffer_size, 8):
                start_addr, end_addr = struct.unpack_from("<II", buf, s)
                
                if start_addr == 0:
                    break
                length = end_addr - start_addr
                sym = ObjdumpSymbol(start_addr, length, "recording")
                recordings[(i, comp_addr)].append(sym)

    return recordings


def parse_symbol_table(binary_filename):
    '''
        Parses the symbol table output by
        arm-none-eabi-objdump -t

        symbol_filename: filename of file output from arm-none-eabi-objdump -t
        returns:  dict mapping addr to symbol name
    '''
    start_found = False
    objdump_symbols = []
    lines = gen_symbol_file(binary_filename)
    for line in lines.split('\n'):
        if not start_found:
            if line == 'SYMBOL TABLE:':
                start_found = True
            continue
        split = line.split(" ")
        try:
            addr = int(split[0].strip(), 16)
            size = int(split[-2].split("\t")[-1].strip(), 16)
            symbol_name = split[-1].strip()

            sym = ObjdumpSymbol(addr, size, symbol_name)
            objdump_symbols.append(sym)
        except ValueError:
            pass  # Catches empty newline at end of file, skips bad lines
    
    return objdump_symbols

def get_access_control_list(binary, memory_file, buffer_size):
    objdump_symbols = parse_symbol_table(binary)
    accessed_addrs = parse_memory_recording(memory_file, buffer_size)
    
    access_list = map_to_symbols(accessed_addrs, objdump_symbols)

    merged_list = merge_adjacent_symbols(access_list)
    return merged_list

if __name__ == "__main__":
    import argparse
    import pprint
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--memory_file', dest='memory', required=True,
                        help='Dump of memory from hexbox record binary, use ' +
                        'dump_mem("<file_name>") in gdb_helpers.py')
    parser.add_argument('-b', '--binary', dest='binary', required=True,
                        help='Binary File (*.elf) ')
    parser.add_argument('-d', '--desc', dest='comp_description', required=True,
                        help='Compartment Description Policy')
    parser.add_argument('-n', '--buffer_size', dest="buffer_size", default=1024,
                        type=int,
                        help='Size of record buffer from each compartment ' +
                             'defined in hexbox-rt.c as RECODE_REGION_SIZE')
    parser.add_argument('-f', '--filename', dest="filename",
                        default='mem_accesses.s',
                        help='Filename to write access controls list to.')
    args = parser.parse_args()

    with open(args.comp_description, 'rb') as desc_file:
        desc = json.load(desc_file)
        num_comps = len(desc['Compartments'].keys())
    merged_list = get_access_control_list(args.binary, args.memory,
                                          args.buffer_size)
    pprint.pprint(merged_list)

    write_acls_file(merged_list, args.filename, num_comps)
