from __future__ import print_function
from argparse import ArgumentParser
import memory_reader
import networkx as nx
import final_linker_gen as ld_gen
import analyzer as graph_an
from key_defs import *
from pprint import pprint
from ld_helpers import next_power_2
import subprocess
import json
from collections import OrderedDict
import numpy
import csv

STORE_INSTRS = ['str', 'push', 'stm', 'stc']


def write_section_memory_data(baseline_info, hexbox_info, fd):
    '''
        Writes the section memory usage to raw data file
    '''
    fd.write('\n\n\n')
    fd.write('Baseline Sizes\n')
    write_section_contents(baseline_info, fd)
    fd.write("RAM Size,%i,%i\n" % get_ram_usage(baseline_info))
    fd.write("FLASH Size,%i,%i,%i\n" % get_flash_usage(baseline_info))
    fd.write('\n\n\n')
    fd.write('Hexbox Sizes\n')
    write_section_contents(hexbox_info, fd)
    fd.write("RAM Size,%i,%i\n" % get_ram_usage(hexbox_info))
    fd.write("FLASH Size,%i,%i,%i\n" % get_flash_usage(hexbox_info))

    return baseline_info, hexbox_info


def get_flash_usage(sections, base_addr=0x08000000):
    size = 0
    frag_loss = 0
    code_size = 0
    for key, value in sections.items():
        if value['addr'] & base_addr != 0:
            if key == '.text' or key == '.rodata' or key == '.isr_vector':
                size += value['size']
            else:
                p2size = next_power_2(value['size'])
                frag_loss += p2size - value['size']
                size += p2size
            if not (key == '.rodata'):
                code_size += value['size']
    return size, frag_loss, code_size


def get_ram_usage(sections, base_addr=0x20000000):
    size = 0
    frag_loss = 0
    for key, value in sections.items():
        if value['addr'] & base_addr != 0:
            if key == '.stack' or key == "._user_heap_stack":
                continue  #  Stack and heap are measured dynamically
            if key.startswith(".DATA_REGION"):
                p2size = next_power_2(value['size'])
                frag_loss += p2size - value['size']
                size += p2size
            else:
                size += value['size']
    return size, frag_loss


def write_section_contents(section, fd):

    for key in sorted(section.keys()):
        value = section[key]
        p2size = next_power_2(value['size'])
        fd.write("%s,0x%08x,%i,%i\n"%(key,value['addr'],value['size'],p2size))


def get_memory_usage(baseline_bin_name, hexbox_bin_name):
    '''
        Gets the memory usage for both the baseline and the hexbox binary
    '''
    baseline_sections = ld_gen.get_section_sizes(baseline_bin_name)
    hexbox_sections = ld_gen.get_section_sizes(hexbox_bin_name)

    return (baseline_sections, hexbox_sections)


def get_sizes_and_num_instrs(bin_file):
    '''
        Uses objdump to get functions, and number bytes each function
        takes.  Ignores hidden functions inserted by comps
    '''
    cmd = ['arm-none-eabi-objdump', '-t', bin_file]
    stdout = subprocess.check_output(cmd)
    functs = {}
    sections = {}
    metadata_size = 0
    for line in stdout.split("\n"):
        if len(line) > 15 and line[15] == 'F':
            size_and_name = line.split('\t')[-1]
            size = int(size_and_name[0:8], 16)
            name = size_and_name[9:].strip()
            if name.startswith('.hidden '):
                name = name[len('.hidden '):]
            section_name = line[17:].split('\t')[0]
            #if not name.startswith('.hidden'):
            functs[name]={'NUM_BYTES':size}
            num_instrs, num_strs = get_num_instructions(name, bin_file)
            functs[name]['NUM_STRS'] = num_strs
            functs[name]['NUM_INSTR'] = num_instrs
            functs[name]["SECTION"] = section_name
            if not sections.has_key(section_name):
                sections[section_name] = {'NUM_BYTES':0,'NUM_INSTR':0}
            sections[section_name]['NUM_BYTES'] += size
            sections[section_name]['NUM_INSTR'] += num_instrs
        if ".rodata" in line and ("__hexbox_md" in line or "_hexbox_comp" in line):
            metadata_size += int(line.split('\t')[1].split()[0], 16)
    return functs, sections, metadata_size


def get_num_instructions(function, bin_file):
    '''
        Uses uses gdb to disassemble each function and then counts number
        of instructions in that function
    '''
    #functs = get_function_names_and_sizes(bin_file)

    cmd = ['arm-none-eabi-gdb', '-batch', '-ex', "file %s" % bin_file,
           "-ex", "disassemble %s" % function]
    stdout = subprocess.check_output(cmd)
    lines = stdout.split('\n')
    sub_count = 2  # First and last line are not instructions
    i = 0
    store_instrs = 0
    while i < len(lines):
        # Remove the embedded metadata ptr from the count of instructions
        if 'svc\t100' in lines[i]:
            addr = int(lines[i].split()[0], 16)
            #  Word may get decoded as 1 or 2 instructions
            if addr + 4 == int(lines[i + 1].split()[0], 16):
                sub_count += 1  # Line after this svc is not an instruction
            else:
                sub_count += 2  # Line after this svc is not an instruction
        else:
            for store_str in STORE_INSTRS:
                if store_str in lines[i].lower():
                    store_instrs += 1
        i += 1
    return (len(lines) - sub_count, store_instrs)


def get_instructions_per_compartment(comp_stats, bin_file):
    '''
        Gets the number of static instructions in each compartment
        Assumes comp_stats was created using build_comp_stats
    '''
    functs, sections, metadata = get_sizes_and_num_instrs(bin_file)
    get_default_comp(comp_stats,functs)
    for comp, stats in comp_stats.items():
        stats["NUM_INSTR"] = 0
        stats["NUM_BYTES"] = 0
        stats["NUM_STRS"] = 0
        for f in stats["FUNCTIONS"]:
            try:
                stats["NUM_INSTR"] += functs[f]['NUM_INSTR']
                stats["NUM_BYTES"] += functs[f]['NUM_BYTES']
                stats["NUM_STRS"] += functs[f]['NUM_STRS']
            except KeyError:
                pass
    return functs, sections, metadata


def get_edges(comp_stats, dep_graph):
    '''
       Gets the in and out edges of each compartment,
       Assumes comp_stats was created using build comp_stats, and dep_graph
       has in and out edges for each function, representing this function
       being a callee(in) and caller(out)

       Adds 'OUT_EDGES': [], 'IN_EDGES': [], 'REQ_GLOBAL':set() to comp_stats
    '''
    node2type = nx.get_node_attributes(dep_graph, TYPE_KEY)
    for c, stats in comp_stats.items():
        #  print("-----------------%s---------------"%str(c))
        comp_stats[c]['OUT_EDGES'] = []
        comp_stats[c]['IN_EDGES'] = []
        comp_stats[c]['REQ_GLOBAL'] = set()
        for f in stats['FUNCTIONS']:
            try:
                for s in dep_graph.successors(f):
                    if node2type[s] == FUNCTION_TYPE and s not in stats['FUNCTIONS']:
                        #  print("Suc: ", s)
                        comp_stats[c]['OUT_EDGES'].append(s)
                    if node2type[s] == GLOBAL_TYPE:
                        #  print("Req: ", s)
                        comp_stats[c]['REQ_GLOBAL'].add(s)

                for p in dep_graph.predecessors(f):
                    if node2type[p] == FUNCTION_TYPE and p not in stats['FUNCTIONS']:
                        #  print("Pre: ", p)
                        comp_stats[c]['IN_EDGES'].append(p)
                    if node2type[p] == GLOBAL_TYPE:
                        #  print("Req: ", p)
                        comp_stats[c]['REQ_GLOBAL'].add(p)
            except nx.exception.NetworkXError:
                pass
    return comp_stats


def build_comp_stats(comp_desc):
    '''
        Gets the functions, peripherals, and globals accessible by this
        compartment.
        Returns:
        comp_stats = {COMP_NAME: {"FUNCTIONS": [], "GLOBALS": [],
                      "PERIPHERALS": [], "Priv": (bool)}, ...}
    '''
    comp_stats = {}

    for comp_name, comp_info in comp_desc[POLICY_KEY_COMPARTMENTS].items():
        stats = {}
        stats["FUNCTIONS"] = []
        for f in comp_desc[POLICY_KEY_REGIONS][comp_name][POLICY_REGION_KEY_OBJECTS]:
            stats["FUNCTIONS"].append(f)
        stats["GLOBALS"] = []
        for r in comp_info["Data"]:
            for g in comp_desc[POLICY_KEY_REGIONS][r][POLICY_REGION_KEY_OBJECTS]:
                stats["GLOBALS"].append(g)
        stats["PERIPHERALS"] = []
        for p in comp_info["Peripherals"]:
            stats["PERIPHERALS"].append(p)

        stats["Priv"] = comp_info["Priv"]
        comp_stats[comp_name] = stats
    return comp_stats


def get_comp_stats(comp_desc, bin_file, dep_graph):
    '''
        Gets the compartment stats for the input data

        Returns:
        comp_stats = {COMP_NAME: {"FUNCTIONS": [], "GLOBALS": [],
                      "PERIPHERALS": [], "Priv":(bool), "NUM_INSTR" : int
                      "NUM_BYTES": int, 'OUT_EDGES': [], 'IN_EDGES': [],
                      'REQ_GLOBAL':set}, ...}
        funct_info =
        section_info =
        metadata =
    '''
    comp_stats = build_comp_stats(comp_desc)
    funct_info, section_info, metadata = \
        get_instructions_per_compartment(comp_stats, bin_file)
    get_edges(comp_stats, dep_graph)

    return comp_stats, funct_info, section_info, metadata


def var_in_whitelist(var, compartment, whitelist):

    for (key, symbols) in whitelist.items():
        wl_comp = key[1]
        if compartment == wl_comp:
            for symbol in symbols:
                if symbol.is_var(var):
                    return True
    return False


def get_global_stats(comp_stats, dep_graph, funct_info, whitelist):
    global_stats = {}
    node2type = nx.get_node_attributes(dep_graph, TYPE_KEY)

    g_vars = filter(lambda (n, d): d[TYPE_KEY] == GLOBAL_TYPE, dep_graph.nodes(data=True))
    for var_tuple in g_vars:
        var = var_tuple[0]
        stats = {}
        stats['REQ_FUNCTIONS'] = set()
        stats['REQ_INSTR'] = 0
        stats["EXPOSED_FUNCTS"] = set()
        stats["EXPOSED_INSTRS"] = 0
        stats["EXPOSED_STRS"] = 0
        for c, c_stats in comp_stats.items():
            if c_stats['Priv'] or var in c_stats['GLOBALS'] or \
               var_in_whitelist(var, c, whitelist):
                stats["EXPOSED_INSTRS"] += c_stats['NUM_INSTR']
                stats["EXPOSED_FUNCTS"].update(c_stats['FUNCTIONS'])
                stats["EXPOSED_STRS"] += c_stats['NUM_STRS']

        # Globals are only connected to functions, and I don't remember the
        # direction so just check both
        for s in dep_graph.successors(var):
            stats['REQ_INSTR'] += funct_info[s]['NUM_INSTR']
            stats['REQ_FUNCTIONS'].add(s)
        for p in dep_graph.predecessors(var):
            stats['REQ_INSTR'] += funct_info[s]['NUM_INSTR']
            stats['REQ_FUNCTIONS'].add(p)

        global_stats[var] = stats

    return global_stats


def compare_functions(comp_functs, baseline_functs):
    return
    print('-------------In Baseline Not in Final-------------------------')
    for f in baseline_functs:
        if f not in comp_functs:
            print(f)

    print('-------------In Final Not in Baseline-------------------------')
    for f in comp_functs:
        if f not in baseline_functs:
            print(f)
    # print(len(comp_functs), len(baseline_functs))


def write_stats(stats, stat_type, fd):
    c_header = ','.join(sorted(stats[stats.keys()[0]].keys()))
    c_header = stat_type + ", " + c_header + "\n"
    fd.write(c_header)
    for c_name in sorted(stats.keys()):
        stat = stats[c_name]
        entries = [str(c_name), ]
        for key in sorted(stat.keys()):
            entry = stat[key]
            if isinstance(entry, (list, set)):
                entry = len(entry)
            entries.append(str(entry))
        row = ",".join(entries)
        fd.write(row)
        fd.write("\n")


def get_hexbox_rt_stats(comp_stats, functions):
    '''
        Gets hexbox rt functions as a compartment
    '''
    rt_functs = []
    for name, f in functions.items():
        if f['SECTION'] == ".hexbox_rt_code":
            rt_functs.append(name)

    comp_stats['.hexbox_rt_code'] = {"FUNCTIONS":rt_functs, "GLOBALS":[],
                              "IN_EDGES": -1,'OUT_EDGES':-1, 'PERIPHERALS':-1,
                              "Priv":0, 'REQ_GLOBAL':-1}


def get_default_comp(comp_stats, functions):
    get_hexbox_rt_stats(comp_stats,functions)
    functions = set(functions.keys())
    comp_functs = set()
    for c, stats in comp_stats.items():
        for f in stats["FUNCTIONS"]:
            comp_functs.add(f)

    default_comp_functs = functions - comp_functs
    comp_stats['.default'] = {"FUNCTIONS":default_comp_functs,"GLOBALS":[],
                              "IN_EDGES": -1,'OUT_EDGES':-1,'PERIPHERALS':-1,
                              "Priv":0, 'REQ_GLOBAL':-1}


def write_comp_summary(comp_stats, fd):
    '''
    Writes compartment summary statitics to file
    Returns
    num_comps
    comp_summary : {'FUNCTIONS': {"Min", "Max", "Ave"}, <Other keys>}
                    <Other Keys> ['GLOBALS', "IN_EDGES", 'NUM_BYTES',
                                 'NUM_INSTR', 'OUT_EDGES', 'PERIPHERALS',
                                 'Priv', 'REQ_GLOBAL ]
    '''
    fd.write("Comparment Summary, %i\n" % (len(comp_stats.keys()) - 2))
    write_stats(comp_stats, "Comps", fd)
    return compute_comp_stats(comp_stats, fd)


def write_global_summary(var_stats, fd):
    '''
        Writed global summary stats,
        return results see compute_global_stats for results format
    '''
    fd.write("Globals Summary, %i\n" % len(var_stats.keys()))
    write_stats(var_stats, "Globals", fd)
    summary_results = compute_globals_stats(var_stats, fd)
    return summary_results


def write_baseline_summary(b_stats, fd):
    fd.write("Baseline, %i\n" % len(b_stats.key()))
    write_stats(b_stats, "Globals", fd)


def write_program_summary(function_info, section_info, program_name, fd):
    code_size = 0
    code_instr = 0
    items = [program_name]
    for key, info in section_info.items():
        code_size += info['NUM_BYTES']
        code_instr += info['NUM_INSTR']
    items.append(str(code_size))
    items.append(str(code_instr))
    items.append(str(len(function_info.keys())))
    fd.write(",".join(items) + "\n")
    return code_size, code_instr, len(function_info.keys())


def write_whitelist_usage(binary, mem_file, fd, size=1024):
    #  TODO get total number of compartments so can calc stats
    comp_list = memory_reader.get_access_control_list(binary, mem_file,
                                          size)
    #  print(compartment_addrs)
    addrs = set()
    size_list = []
    str_size_list = []
    for comp, symbols in comp_list.items():
        for sym in symbols:
            addrs.add(sym.addr)
        str_size_list.append(str(len(symbols)))
    fd.write("\n\nWhite List\n")
    fd.write("Num Unique Addresses, %i\n" % len(addrs))
    #  fd.write("Min List Size, %i\n" % np.min(size_list))
    #  fd.write("Max List Size, %i\n" % np.max(size_list))
    #  fd.write("Median Size, %i\n" % np.median(size_list))
    #  fd.write("Mean List Size, %i\n" % np.mean(size_list))
    fd.write(",".join(str_size_list) + "\n")


def compute_comp_stats(comp_stat, fd):
    """
        Caluculates the min, ave, and max of compartment metrics

        Returns
        num_comps
        comp_summary : {'FUNCTIONS': {"Min", "Max", "Ave"}, <Other keys>}
                        <Other Keys> ['GLOBALS', "IN_EDGES", 'NUM_BYTES',
                                     'NUM_INSTR', 'OUT_EDGES', 'PERIPHERALS',
                                     'Priv', 'REQ_GLOBAL ]
    """
    compute_res = OrderedDict([
        ('FUNCTIONS',[]),
        ('GLOBALS',[]),
        ("IN_EDGES",[]),
        ('NUM_BYTES',[]),
        ('NUM_INSTR',[]),
        ('NUM_STRS',[]),
        ('OUT_EDGES',[]),
        ('PERIPHERALS',[]),
        ('Priv',[]),
        ('REQ_GLOBAL',[])
    ])
    comp_summary = OrderedDict([
        ('FUNCTIONS',   {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('GLOBALS',     {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ("IN_EDGES",    {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('NUM_BYTES',   {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('NUM_INSTR',   {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('NUM_STRS',    {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('OUT_EDGES',   {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('PERIPHERALS', {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('Priv',        {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None}),
        ('REQ_GLOBAL',  {"Min": None, "Max": None, "Ave": None, 'Total':None, 'Median': None})
    ])
    default_reg = OrderedDict()     # contains default region values, so that it will be added separatly
    num_comps = len(comp_stat.keys()) - 2  # Remove default, and hexbox-rt regions
    for key in comp_stats:
        code_reg = comp_stat[key]
        if key == ".hexbox_rt_code":                            # Skip .hexbox_rt_code
            continue

        for cr_key in code_reg:
            if key == ".default":                               # Store default data and skip
                if isinstance(code_reg[cr_key], int):
                    default_reg[cr_key] = code_reg[cr_key]
                else:
                    default_reg[cr_key] = len(code_reg[cr_key])
            else:
                # Here handle the general compartments
                if isinstance(code_reg[cr_key], int):
                    value = code_reg[cr_key]
                else:

                    value = len(code_reg[cr_key])
                compute_res[cr_key].append(value)
    # write MIN
    # print(default_reg)
    fd.write("MIN" + ",")
    for key in compute_res:
        m = numpy.min(compute_res[key]) + default_reg[key]
        comp_summary[key]["Min"] = m
        fd.write(str(m) + ",")
    fd.write("\n")
    # write MAX
    fd.write("MAX" + ",")
    for key in compute_res:
        m = numpy.max(compute_res[key]) + default_reg[key]
        comp_summary[key]["Max"] = m
        fd.write(str(m) + ",")
    fd.write("\n")
    # write Ave
    fd.write("AVE" + ",")
    for key in compute_res:
        m = numpy.average(compute_res[key]) + default_reg[key]
        comp_summary[key]["Ave"] = m
        fd.write(str(m) + ",")
    fd.write("\n")

    fd.write("Total" + ",")
    for key in compute_res:
        m = numpy.sum(compute_res[key]) + default_reg[key]
        comp_summary[key]["Total"] = m
        fd.write(str(m) + ",")
    fd.write("\n")

    fd.write("Median" + ",")
    for key in compute_res:
        m = numpy.median(numpy.array(compute_res[key]) + default_reg[key])
        comp_summary[key]["Median"] = m
        fd.write(str(m) + ",")
    fd.write("\n")
    return num_comps, comp_summary


def compute_globals_stats(glob_stat, fd):
    '''
        Computes the min, ave and max of glob_stat for required globals
        and exposed globals
        Returns:
        results dict = {'EXPOSED_FUNCTS': {"Min": None, "Ave": None,
                                           "Max": None}, ...}
                       Other Keys in results: EXPOSED_INSTRS, REQ_FUNCTIONS,
                       REQ_INSTR
    '''
    compute_res = OrderedDict([
        ('EXPOSED_FUNCTS',[]),
        ('EXPOSED_INSTRS',[]),
        ('EXPOSED_STRS',[]),
        ("REQ_FUNCTIONS",[]),
        ("REQ_INSTR", [])
    ])

    results = OrderedDict([
        ('EXPOSED_FUNCTS', {"Min": None, "Ave": None, "Max": None, "Median": None, 'Total':None}),
        ('EXPOSED_INSTRS', {"Min": None, "Ave": None, "Max": None, "Median": None, 'Total':None}),
        ('EXPOSED_STRS',   {"Min": None, "Ave": None, "Max": None, "Median": None, 'Total':None}),
        ("REQ_FUNCTIONS",  {"Min": None, "Ave": None, "Max": None, "Median": None, 'Total':None}),
        ("REQ_INSTR",      {"Min": None, "Ave": None, "Max": None, "Median": None, 'Total':None})
    ])

    for key in glob_stat:
        glob_var = glob_stat[key]
        for g_key in glob_var:
            if isinstance(glob_var[g_key], int):
                value = glob_var[g_key]
            else:
                value = len(glob_var[g_key])
            compute_res[g_key].append(value)
    # write MIN
    fd.write("MIN"+",")
    for key in compute_res:
        minimum = numpy.min(compute_res[key])
        results[key]["Min"] = minimum
        fd.write(str(minimum) + ",")
    fd.write("\n")
    # write MAX
    fd.write("MAX" + ",")
    for key in compute_res:
        maximum = numpy.max(compute_res[key])
        results[key]["Max"] = maximum
        fd.write(str(maximum) + ",")
    fd.write("\n")
    # write Ave
    fd.write("AVE" + ",")
    for key in compute_res:
        ave = numpy.average(compute_res[key])
        results[key]["Ave"] = ave
        fd.write(str(ave) + ",")
    fd.write("\n")

    fd.write("Med" + ",")
    for key in compute_res:
        med = numpy.median(compute_res[key])
        results[key]["Median"] = med
        fd.write(str(med) + ",")
    fd.write("\n")

    fd.write("Total" + ",")
    for key in compute_res:
        med = numpy.sum(compute_res[key])
        results[key]["Total"] = med
        fd.write(str(med) + ",")
    fd.write("\n")

    return results


def compute_size_summary(base_code, base_instr, base_numfunc, hexbox_code,
                         hexbox_instr, hexbox_numfunc, fd):
    fd.write("OVERHEAD" + ",")
    code_overhead = 100 * (float(hexbox_code - base_code) / base_code)
    instr_overhead = 100 * (float(hexbox_instr - base_instr) / base_instr)
    numfunc_overhead = 100 * (float(hexbox_numfunc - base_numfunc) /
                              base_numfunc)
    overhead_list = [code_overhead, instr_overhead, numfunc_overhead]
    fd.write(",".join(map(str, overhead_list)) + "\n")


def compute_memory_stats(name, policy, base_info, hexbox_info):
    '''
        Gets memory usage by category for all RAM and flash
        Returns
        results:  An OrderdDict, with keys [Policy, App, Flahs_Total,
                     Flash_Baseline, Flash_Fragmentation, Flash_ACES_RT,
                     Flash_Metadata, RAM_Total, RAM_Baseline,
                     RAM_Fragmentation, RAM_ACES_RT]
    '''
    # get flash, ram, and fragmentation values
    base_ram, base_ram_frag = get_ram_usage(base_info)
    hexbox_ram, hexbox_ram_frag = get_ram_usage(hexbox_info)
    base_flash, base_flash_frag, base_code_size = get_flash_usage(base_info)
    hexbox_flash, hexbox_flash_frag, hexbox_code_size = \
        get_flash_usage(hexbox_info)
    base_metadata_size = base_info['.rodata']['size']
    hexbox_metadata_size = hexbox_info['.rodata']['size']

    results = OrderedDict()
    results['Policy'] = policy
    results['App'] = name
    results["Flash_Total"] = hexbox_flash
    results["Flash_Baseline"] = base_flash
    results["Flash_Fragmentation"] = hexbox_flash_frag
    results["Flash_ACES_RT"] = hexbox_info['.hexbox_rt_code']['size']
    results["Flash_Metadata"] = hexbox_metadata_size - base_metadata_size
    results["Flash_Code_Diff"] = hexbox_code_size - base_code_size

    results["RAM_Total"] = hexbox_ram
    results["RAM_Baseline"] = base_ram
    results["RAM_Fragmentation"] = hexbox_ram_frag
    results["RAM_ACES_RT"] = hexbox_info['.hexbox_rt_ram']['size']
    return results


def write_memory_stats(mem_results, fd):
    '''
        Writes the result summary to the raw result file
    '''
    # -------------------------------------------------------------------------
    # Write RAM overhead
    hexbox_ram = mem_results["RAM_Total"]
    base_ram = mem_results["RAM_Baseline"]
    hexbox_ram_frag = mem_results["RAM_Fragmentation"]
    hebox_rtlib_ram_size = mem_results["RAM_ACES_RT"]

    hexbox_flash = mem_results["Flash_Total"]
    base_flash = mem_results["Flash_Baseline"]
    hexbox_flash_frag = mem_results["Flash_Fragmentation"]
    hebox_rtlib_flash_size = mem_results["Flash_ACES_RT"]

    ram_overhead = 100 * (float(hexbox_ram - base_ram) / base_ram)
    flash_overhead = 100 * (float(hexbox_flash - base_flash) / base_flash)
    ram_frag_overhead = 100 * (float(hexbox_ram_frag) /
                               (hexbox_ram - base_ram))
    flash_frag_overhead = 100 * (float(hexbox_flash_frag) /
                                 (hexbox_flash - base_flash))
    rtlib_ram_overhead = 100 * (float(hebox_rtlib_ram_size) /
                                (hexbox_ram - base_ram))
    rtlib_flash_overhead = 100 * (float(hebox_rtlib_flash_size) /
                                  (hexbox_flash - base_flash))
    metadata_size_overhead = mem_results["Flash_Metadata"]
    metadata_overhead = 100 * (float(metadata_size_overhead) /
                               (hexbox_flash - base_flash))

    # Write results to the file
    fd.write("OVERHEAD-RAM" + ",")
    fd.write(str(ram_overhead) + "\n")
    fd.write("OVERHEAD-FLASH" + ",")
    fd.write(str(flash_overhead) + "\n")
    fd.write("OVERHEAD-FRAG-RAM" + ",")
    fd.write(str(ram_frag_overhead) + "\n")
    fd.write("OVERHEAD-FRAG-FLASH" + ",")
    fd.write(str(flash_frag_overhead) + "\n")
    fd.write("OVERHEAD-RTLIB-RAM" + ",")
    fd.write(str(rtlib_ram_overhead) + "\n")
    fd.write("OVERHEAD-RTLIB-FLASH" + ",")
    fd.write(str(rtlib_flash_overhead) + "\n")
    fd.write("METADATA-SIZE" + ",")
    fd.write(str(metadata_size_overhead) + "\n")
    fd.write("OVERHEAD-METADATA" + ",")
    fd.write(str(metadata_overhead) + "\n")


def get_num_data_regions(section_info):
    '''
     Counts the number of data region_sizes
    '''
    data_regions = 0
    # code_regions = 0
    for key in section_info:
        if key.startswith(".DATA_REGION"):
            data_regions += 1
        # elif key.startswith(".CODE_REGION") or key.startswith('IRQ_REGION'):
        #    code_regions += 1
    return data_regions


def get_num_privileged_instructions(comp_stats):
    '''
        Calculates the number of privileged instructions
    '''
    priv_instr = 0
    default_added = False
    for comp, stats in comp_stats.items():
        if comp == ".default":
            continue
        else:
            if stats["Priv"]:
                priv_instr += stats["NUM_INSTR"]
                if ".default" in stats["OUT_EDGES"] and not default_added:
                    print ("Adding default to privileged instruction count")
                    default_added = True
                    priv_instr += comp_stats[".default"]["NUM_INSTR"]
    return priv_instr


def compile_memory_results(name, policy, base_info, hexbox_info):

    base_ram, base_ram_frag = get_ram_usage(base_info)
    hexbox_ram, hexbox_ram_frag = get_ram_usage(hexbox_info)
    base_flash, base_flash_frag, base_code_size = get_flash_usage(base_info)
    hexbox_flash, hexbox_flash_frag,base_code_size = get_flash_usage(hexbox_info)
    hebox_rtlib_ram_size = hexbox_info['.hexbox_rt_ram']['size']
    hebox_rtlib_flash_size = hexbox_info['.hexbox_rt_code']['size']
    metadata_size = base_info['.rodata']['size']
    hexbox_metadata_size = hexbox_info['.rodata']['size']


def compile_static_results(name, policy, hexbox_instr, base_instr, comp_stats,
                           hexbox_numFunc, comp_summary, global_results,
                           elf_sections, num_comps):
    '''
        Compiles static results for paper
    '''
    results = OrderedDict()
    results['Policy'] = policy
    results['App'] = name
    results["#Instr"] = hexbox_instr
    results["%%Instr"] = (hexbox_instr - base_instr) / float(base_instr)
    num_priv_instr = get_num_privileged_instructions(comp_stats)
    results["%%Priv"] = num_priv_instr / float(hexbox_instr)
    results["#Funct"] = hexbox_numFunc
    results["%%Funct"] = (hexbox_numFunc - base_numFunc) / float(base_numFunc)
    results["#Code_Regions"] = num_comps
    results["#Data_Regions"] = get_num_data_regions(elf_sections)
    results["Median_Inst_Comp"] = comp_summary['NUM_INSTR']["Median"]
    results["Max_Inst_Comp"] = comp_summary['NUM_INSTR']["Max"]
    results["Degree_In_Med"] = comp_summary["IN_EDGES"]["Median"]
    results["Degree_Out_Med"] = comp_summary["OUT_EDGES"]["Median"]
    results["Degree_In_Max"] = comp_summary["IN_EDGES"]["Max"]
    results["Degree_Out_Max"] = comp_summary["OUT_EDGES"]["Max"]
    results["Max_Exposure"] = global_results["EXPOSED_INSTRS"]["Max"]
    results["Max_STRS"] = global_results["EXPOSED_STRS"]["Max"]
    results["Median_STRS"] = global_results["EXPOSED_STRS"]["Median"]
    results["Total_STRS"] = comp_summary["NUM_STRS"]["Total"]
    results["#ROP"] = None
    results["%%ROP"] = None
    return results


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-f', '--hexbox_binary', required=True,
                        dest='hexbox_bin', help='Hexbox Final Binary')
    parser.add_argument('-b', '--baseline', required=True, dest='baseline_bin',
                        help='Baseline Binary')
    parser.add_argument('-c', '--comp_description', dest='comp_desc',
                        required=True, help='Final Compartment Description' +
                        ' (hexbox-final-policy--<method>.json)')
    parser.add_argument('-g', '--graph', dest='graph', required=True,
                        help='Dependancy Graph' +
                        ' (hexbox-analysis--<method>.json)')
    parser.add_argument('-m', '--memory_file', dest='memory', required=True,
                        help='Dump of memory from hexbox record binary, use ' +
                        'dump_mem("<file_name>") in gdb_helpers.py')
    parser.add_argument('-o', '--outfile', dest='outfile', required=False,
                        default='results.csv', help='Output file name')

    args = parser.parse_args()

    name_info = args.hexbox_bin.split('--')
    policy = name_info[1]
    app_name = name_info[0].split("/")[-1]

    with open(args.comp_desc, 'rb') as comp_json:
        comp_desc = json.load(comp_json)

    results = {}

    comp_whitelist = memory_reader.get_access_control_list(args.hexbox_bin,
                                                           args.memory, 1024)

    dep_graph = graph_an.build_graph(args.graph)
    region_sizes = ld_gen.get_section_sizes(args.hexbox_bin)
    comp_stats, funct_info, section_info, comp_metadata = \
        get_comp_stats(comp_desc, args.hexbox_bin, dep_graph)
    global_stats = get_global_stats(comp_stats, dep_graph, funct_info,
                                    comp_whitelist)

    base_functs, base_sections, metadata = \
        get_sizes_and_num_instrs(args.baseline_bin)

    (baseline_info, hexbox_info) = get_memory_usage(args.baseline_bin,
                                                    args.hexbox_bin)

    mem_results = compute_memory_stats(app_name, policy, baseline_info,
                                       hexbox_info)



    #  --------------------------Write Raw data file -------------------------
    with open(args.outfile, 'w') as fd:
        num_comps, comp_summary = write_comp_summary(comp_stats, fd)
        fd.write('\n')
        global_results = write_global_summary(global_stats, fd)
        fd.write("\nSize Summary\n")
        fd.write("Program Name,Num Bytes,Num Instr,Num Functions\n")

        base_code, base_instr, base_numFunc = \
            write_program_summary(base_functs, base_sections, "Baseline", fd)
        hexbox_code, hexbox_instr, hexbox_numFunc = \
            write_program_summary(funct_info, section_info, "Hexbox", fd)
        #  calcualte size summary overheads
        compute_size_summary(base_code, base_instr, base_numFunc, hexbox_code,
                             hexbox_instr, hexbox_numFunc, fd)
        write_section_memory_data(baseline_info, hexbox_info, fd)
        # calculate stats for RAM,FLASH, and metadata
        write_memory_stats(mem_results, fd)
        write_whitelist_usage(args.hexbox_bin, args.memory, fd)
        fd.write("\n\n Baseline Metadata Size, %i\n" % metadata)
        fd.write("\n Hexbox Metadata Size, %i\n" % comp_metadata)

    compare_functions(funct_info, base_functs)

    # -----------------------------Write Memory Results -----------------------
    with open("memory_table_" + args.outfile, 'wb') as summary_fd:
        dw = csv.DictWriter(summary_fd, fieldnames=mem_results)
        dw.writeheader()
        dw.writerow(mem_results)
    # ----------------------------Compile Static Results-----------------------
    static_results = \
        compile_static_results(app_name, policy, hexbox_instr, base_instr,
                               comp_stats, hexbox_numFunc, comp_summary,
                               global_results, hexbox_info, num_comps)
    with open("static_table_" + args.outfile, 'wb') as summary_fd:
        dw = csv.DictWriter(summary_fd, fieldnames=static_results)
        dw.writeheader()
        dw.writerow(static_results)
