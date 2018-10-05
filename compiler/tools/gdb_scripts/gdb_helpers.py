import gdb
import re
import os
import numpy
import csv
from collections import OrderedDict


ISCR_LUT = ['Thread mode',
            'Reserved',
            'NMI',
            'HardFault',
            'MemManage',
            'BusFault',
            'UsageFault',
            'Reserved',
            'Reserved',
            'Reserved',
            'Reserved',
            'SVCall',
            'Reserved for Debug',
            'Reserved',
            'PendSV',
            'SysTick']

def get_section_start_and_end(section_name):
    '''
        Gets the section start and end addr for the given section
    '''
    file_info = gdb.execute('info file', to_string=True)
    m = re.search('0x([\d,a-f,A-F]{8}) - 0x([\d,a-f,A-F]{8}) is (%s)' % section_name, file_info)
    if m:
        start_addr = int(m.groups()[0], 16)
        end_addr = int(m.groups()[1], 16)
        print ("Found 0x%08x:0x%08x" % (start_addr, end_addr))
        return (start_addr, end_addr)
    else:

        print file_info
        print "Section Name Not Found: ", section_name
        raise ValueError("Section Name not Found")


def get_value_at_symbol(symbol_str):
    '''
        Gets the value at the symbol provided
        Returns (int)
    '''
    r_str = gdb.execute('x /x %s' % symbol_str, to_string=True)
    match = re.search(r':\t0x([\d,a-f,A-F]{8})',r_str)
    return int(match.groups()[0],16)


def get_print_num(in_str):
    '''
        Gets teh number returned from p /x %s
    '''
    p_str = gdb.execute('p /x %s' % (in_str), to_string=True)
    return int(p_str.split("=")[1], 16)

def get_filename():
    '''
        Returns the filename of the file being debugged
    '''
    info = gdb.execute('info files', to_string=True)
    #  Symbols from "/abs/path/to/file.elf".
    info = info.split("\n")[0]
    return os.path.split(info[14:-2])[1]


def get_mem(addr):
    res = gdb.execute('x 0x%x' % addr, to_string=True)
    (addr, value) = res.split(":")
    value = int(value.split('x')[1].strip(), 16)
    return value


def set_mem(addr, value):
    gdb.execute('set *(uint32_t*)0x%x = 0x%x' % (addr, value))


def get_stacked_pc(stackoffset=0):
    '''
        Gets the PC pushed on the stack from in an ISR
        Offset can be used adjust if additional things have been
        pushed to stack
    '''
    sp = get_print_num('$sp')
    return get_mem(sp+(4*6)+stackoffset)


def parse_hardfault(hardfault, sp_offset):
    print "Hard Fault 0x%x Reason: " % hardfault,
    if hardfault & (1 << 30):
        print "Forced--Other fault elavated"
    if hardfault & (1 << 1):
        print "Bus Fault"
    print "Stacked PC 0x%x" % (get_stacked_pc(sp_offset))


BFAR = 0xE000ED38
MMAR = 0xE000ED34


def parse_cfsr(cfsr, sp_offset):
    print "CFSR 0x%x" % cfsr
    print "MemManage Flags"
    if cfsr & (1 << 7):
        print "\tMemManage Fault Address Valid: 0x%x" % get_mem(MMAR)
    if cfsr & (1 << 5):
        print "\tMemManage fault occurred during floating-point lazy state preservation"
    if cfsr & (1 << 4):
        print "\tStacking for an exception entry has caused one or more access violations"
    if cfsr & (1 << 3):
        print "\tUnstacking for an exception return has caused one or more access violations"
    if cfsr & (1 << 1):
        print "\tData Access, Stacked PC 0x%x, Faulting Addr 0x%x" % (
            get_stacked_pc(sp_offset), get_mem(MMAR))
    if cfsr & (1):
        print "\tInstruction Access Violation, Stacked PC 0x%x" % (get_stacked_pc(sp_offset))
    print "BusFault:"
    if cfsr & (1 << 15):
        print "\t Bus Fault Addr Valid 0x%x" % get_mem(BFAR)
    if cfsr & (1 << 13):
        print "\tbus fault occurred during"
    if cfsr & (1 << 12):
        print "\tException Stacking fault"
    if cfsr & (1 << 11):
        print "\tException UnStacking fault"
    if cfsr & (1 << 10):
        print "\tImprecise data bus error, may not have location"
    if cfsr & (1 << 9):
        print "\tPrecise data bus error, Faulting Addr: %0x" % get_mem(BFAR)
    if cfsr & (1 << 8):
        print "\tInstruction bus error"

    print "Other Faults"
    if cfsr & (1 << (9+16)):
        print "\tDiv by zero, Stacked PC has Addr"
    if cfsr & (1 << (8+16)):
        print "\tUnaligned Fault Stacking fault"
    if cfsr & (1 << (3+16)):
        print "\tNo Coprocessor"
    if cfsr & (1 << (2+16)):
        print "\tInvalid PC load UsageFault, Stacked PC has Addr"
    if cfsr & (1 << (1+16)):
        print "\tInvalid state UsageFault, Stacked PC has Addr"
    if cfsr & (1 << (16)):
        print "\tUndefined instruction UsageFault, Stacked PC has Addr"


def print_exception_stack(offset=0):
    '''
        Prints registers pushed on the stack by exception entry

    '''
    #  http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.dui0553a/Babefdjc.html
    sp = get_print_num('$sp')
    sp += offset
    print "Registers Stacked by Exception"
    print "R0: 0x%x" % get_mem(sp)
    print "R1: 0x%x" % get_mem(sp+4)
    print "R2: 0x%x" % get_mem(sp+8)
    print "R3: 0x%x" % get_mem(sp+12)
    print "R12: 0x%x" % get_mem(sp+16)
    print "LR: 0x%x" % get_mem(sp+20)
    print "PC: 0x%x" % get_mem(sp+24)
    print "xPSR: 0x%x" % get_mem(sp+28)
    # TODO Check CCR for floating point and print S0-S15 FPSCR


def print_hardfault_info(stack_offset=0):
    '''
        Prints Hardfault info, alias for print_hardfault_info
    '''
    print ("Configurable Fault Status Reg")
    hardfault_status = get_mem(0xE000ED2C)
    print_exception_stack(stack_offset)
    parse_hardfault(hardfault_status, stack_offset)

    cfsr = get_mem(0xE000ED28)
    parse_cfsr(cfsr, stack_offset)


def hf(stack_offset=0):
    '''
        Prints Hardfault info, alias for print_hardfault_info
    '''
    print_hardfault_info(stack_offset)


def hfb(stack_offset=0):
    '''
        Prints Hardfault info and sets break point on faulting pc
    '''
    hf(stack_offset)
    pc = get_stacked_pc(stack_offset)
    gdb.execute('b *0x%x' % pc)


# See ARM Documentation for details
# http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.dui0553a/Cihjddef.html
MPU_CTRL = 0xE000ED94
MPU_RNR = 0xE000ED98
MPU_RBAR = 0xE000ED9C
MPU_RASR = 0xE000EDA0
PER_LUT = {0: '(P-,U-)', 1: '(P-RW,U-)', 2: '(P-RW,U-R)', 3: '(P-RW,U-RW)',
           4: '(Undef)', 5: '(P-R,U-)', 6: '(P-R,U-R)', 7: '(P-R,U-R)'
           }


def decode_mpu(rbar, rasr):
    AP = (rasr >> 24) & 0x7
    M = (rasr >> 1) & 0x1F
    print "\tRegion %i" % (rbar & 0xf)
    start = rbar & (~0x1F)
    print "\tStart: 0x%x" % (start)
    size = 2**(M+1)
    print "\tEnd: 0x%x" % (start+size-1)
    print "\tSize: %i, 0x%x" % (size, size)
    print "\tPermissions 26:24: 0x%x ,%s" % (AP, PER_LUT[AP])
    print "\tExecute Never: ", ((rasr & (0x1 << 28)) >> 28)
    print "\tSCB 18:16, 0x%x:" % ((rasr & (0x7 << 16)) >> 16)
    print "\tTEX 21:19, 0x%x:" % ((rasr & (0x7 << 19)) >> 19)
    print "\tEnabled :", (rasr & 0x1)
    print "RBAR: 0x%x" % rbar
    print "RASR: 0x%x" % rasr
    print "-"*40


def print_mpu_ctrl_reg():
    mpu_ctrl = get_mem(MPU_CTRL)
    print "MPU_CTRL: 0x%x" % (mpu_ctrl)
    print "\tEnabled: ", (mpu_ctrl & 0x1)
    print "\tEnabled During NMI/HF: ", ((mpu_ctrl >> 1) & 0x1)
    print "\tPriv Has Default Map:", ((mpu_ctrl >> 2) & 0x1)


def print_mpu_config():
    for i in range(8):
        print "Reading %i" % i
        set_mem(MPU_RNR, i)
        rbar = get_mem(MPU_RBAR)
        rasr = get_mem(MPU_RASR)
        decode_mpu(rbar, rasr)
    print_mpu_ctrl_reg()


def mpu():
    print_mpu_config()


def get_isr():
    '''
    Prints the interrupt that caused the interrupt.
    Useful when hit default handler and do not know why
    '''
    iscr = get_mem(0xE000ED04)  # This is ISCR
    isr = iscr & 0x1FF
    if isr < len(ISCR_LUT):
        print "%i: %s" % (isr, ISCR_LUT[isr])
    else:
        print "%i: IRQ%i" % (isr, isr-16)


# def hexbox_svc(offset=0):
#     '''
#     Run on first instruction of SVC handler for hexbox
#     '''
#     sp = get_print_num('$sp')
#     sp += offset
#     lr = get_mem(sp+20)
#     pc = get_mem(sp+24)
#     pc_str = gdb.execute("info sym 0x%08x" % (pc-2), to_string=True)
#     lr_str = gdb.execute("info sym 0x%08x" % lr, to_string=True)
#     svc = get_mem(pc-2)
#     svc = svc & 0xFF
#     if (svc == 100):
#         print "Entry: %s  --> %s" % (pc_str.strip(), lr_str.strip())
#     elif (svc == 101):
#         print "Return: %s  <-- %s" % (lr_str.strip(), pc_str.strip())

#     else:
#         print "Unknown SVC"


FP_CONTROL = 0xe0002000
FP_REMAP = FP_CONTROL + 4
FP_COMP_BASE = FP_CONTROL + 8
FP_COMP = range(FP_COMP_BASE, FP_COMP_BASE+(8*4), 4)


def decode_flash_break():
    get_mem(FP_CONTROL)


def get_hexbox_stats():
    stats = [
        '__hexbox_total_exe_time',
        '__hexbox_init_exe_time',
        '__hexbox_unknown_comp_exe_time',
        '__hexbox_entry_exe_time',
        '__hexbox_exit_exe_time',
        '__hexbox_comp_exe_times',
        '__hexbox_comp_emu_exe_times',
        '__hexbox_entries',
        '__hexbox_exits',
        '__hexbox_comp_entries',
        '__hexbox_comp_exits',
        '__hexbox_comp_emu_calls'
    ]
    get_stats(stats)


def get_stats(var_names):
    global HEXBOX_STATS, BASELINE_STATS
    app_name = get_filename()
    for var in var_names:
        r = gdb.execute('p %s' % (var), to_string=True)
        print "%s : %s" % (var, r.strip())
        r = r.strip('\n')
        res = r.split('=')[1]
        res = re.sub('[\{\}]', '', res)
        res = res.strip()
        res = res.split(',')
        for val in res:
            if '<repeats' in val:
                values = val.split()
                repeated_value = values[0]
                num_repeatitions = int(values[2])
                for i in range(num_repeatitions):
                    res.insert(res.index(val)+1, repeated_value)
                res.remove(val)
        res = map(int, res)
        if 'hexbox' in app_name:
            HEXBOX_STATS[var].append(res)
        else:
            BASELINE_STATS[var].append(res)


def get_baseline_stats():
    stats = ['runtime']
    get_stats(stats)


def save_state():
    r0 = get_print_num("$r0")
    r1 = get_print_num("$r1")
    r2 = get_print_num("$r2")
    r3 = get_print_num("$r3")
    pc = get_print_num("$pc")
    lr = get_print_num("$lr")
    r12 = get_print_num("$r12")
    sp = get_print_num("$sp")
    xPSR = get_print_num("$xPSR")
    handler_addr = get_print_num("&DebugMon_Handler")+1
    gdb.execute("set $pc = 0x%x" % handler_addr)
    gdb.execute("finish")
    gdb.execute("set {uint32_t}0xe000201C=0")
    gdb.execute("set $r0 =0x%x" % r0)
    gdb.execute("set $r1 =0x%x" % r1)
    gdb.execute("set $r2 =0x%x" % r2)
    gdb.execute("set $r3 =0x%x" % r3)
    gdb.execute("set $r12 =0x%x" % r12)
    gdb.execute("set $lr =0x%x" % lr)
    gdb.execute("set $pc =0x%x" % pc)
    gdb.execute("set $sp =0x%x" % sp)
    gdb.execute("set $xPSR =0x%x" % xPSR)
    gdb.execute("c")


def dump_mem(filename="accesses.bin"):
    '''
        Dumps memory used to generate white list for compartments
    '''
    gdb.execute("dump binary memory %s 0x10000000 0x1000E000" % filename)


def connect():
    gdb.execute('target remote localhost:3333')
    gdb.execute('monitor reset halt')


def load():
    gdb.execute('load')


def cl():
    'Short connect and load'
    connect()
    load()


def c():
    'short connect for load us py c()'
    connect()


def clm():
    'short connect break on main'
    cl()
    gdb.execute('b main')

#######################################################################################################
#                                    Performance Measurement                                          #
#######################################################################################################


'''
These functions are to count cycles executed using
DWT_CTRL and DWT_* registers. See ARM's documentation
for more details.
http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.ddi0439c/BABJFFGJ.html
'''

DWT_CTRL = 0xE0001000
DWT_CYCCNT = 0xE0001004
DWT_CPICNT = 0xE0001008
DWT_EXCCNT = 0xE000100C
DWT_SLEEPCNT = 0xE0001010
DWT_LSUCNT = 0xE0001014
DWT_FOLDCNT = 0xE0001018


DWT_CYCCNT_Msk = 0x00000001  # counters mask values
DWT_ALL_Msk = 0x00000001  # 0x403F0001 <--- revise the all mask, for hexbox we will be just using CYCCNT si


def set_cycle_counter():
    set_mem(DWT_CTRL, DWT_CYCCNT_Msk)


def reset_cycle_counter():
    set_mem(DWT_CYCCNT, 0)


def get_cycle_counter():
    return get_mem(DWT_CYCCNT)

# enables the other counters (other than the total cycles counter, e.g.SLEEPCNT..etc)


def set_all_counters():
    global DWT_CTRL
    global DWT_CYCCNT
    global DWT_CPICNT
    global DWT_EXCCNT
    global DWT_SLEEPCNT
    global DWT_LSUCNT
    global DWT_FOLDCNT
    set_mem(DWT_CTRL, DWT_ALL_Msk)


def reset_all_counters():
    global DWT_CTRL
    global DWT_CYCCNT
    global DWT_CPICNT
    global DWT_EXCCNT
    global DWT_SLEEPCNT
    global DWT_LSUCNT
    global DWT_FOLDCNT
    set_mem(DWT_CYCCNT, 0)
    set_mem(DWT_CPICNT, 0)
    set_mem(DWT_EXCCNT, 0)
    set_mem(DWT_SLEEPCNT, 0)
    set_mem(DWT_LSUCNT, 0)
    set_mem(DWT_FOLDCNT, 0)


'''
    Shortcuts for the functions above to ease debugging
'''


def gc():
    get_cycle_counter()


# short hand to set and reset all counters
def rac():
    reset_all_counters()
    set_all_counters()


COUNTS = []
# short hand to print the value of all the counters


def pcntr():
    global COUNTS
    global DWT_CTRL
    global DWT_CYCCNT
    global DWT_CPICNT
    global DWT_EXCCNT
    global DWT_SLEEPCNT
    global DWT_LSUCNT
    global DWT_FOLDCNT
    #  cntr_table = Texttable()
    print('DWT_CYCCNT', get_mem(DWT_CYCCNT))
    COUNTS.append(get_mem(DWT_CYCCNT))
    print(COUNTS)
    print("Counts Ave: ", numpy.average(COUNTS))
    print("Counts STD: ", numpy.std(COUNTS, ddof=1))
    #  cntr_table.add_rows([['COUNTER', 'VALUE'],
    #                     ['DWT_CYCCNT', get_mem(DWT_CYCCNT)],
    #                     ['DWT_CPICNT', get_mem(DWT_CPICNT)],
    #                     ['DWT_EXCCNT', get_mem(DWT_EXCCNT)],
    #                     ['DWT_SLEEPCNT', get_mem(DWT_SLEEPCNT)],
    #                     ['DWT_LSUCNT', get_mem(DWT_LSUCNT)],
    #                     ['DWT_FOLDCNT', get_mem(DWT_FOLDCNT)]])
    # print(cntr_table.draw())

###############################################

# get the current app name in order to setup the breakpoints correctly


def get_current_app():
    res = gdb.execute('info file', to_string=True)
    res = res.split("\n")[0]
    res = res.split("\"")[1]
    res = res.rsplit("/")
    # print(str(res[len(res)-1]))
    return str(res[len(res) - 1])


def mrh():
    'short for monitor reset'
    gdb.execute('monitor reset halt')


class EndBreakpoint(gdb.Breakpoint):
    def set_params(self, results_file, summary_filename,
                   stack_funct=None, limit=20):
        self.results_file = results_file
        self.summary_filename = summary_filename
        self.iter_limit = limit
        self.iter_count = 0
        self.stack_measure_function = stack_funct

    def stop(self):
        app_name = get_filename()
        if 'hexbox' in app_name:
            get_hexbox_stats()
        elif 'uVisor'in app_name:
            pcntr()
        else:
            get_baseline_stats()
        self.iter_count += 1
        if self.iter_count < self.iter_limit:
            mrh()
            rac()
        else:
            print("[+] Measurements ended, parsing and writing to results file")
            collect_write_results(self.results_file, self.summary_filename,
                                  self.stack_measure_function)
            print('='*80)
            print('END:' + self.results_file)
            print('=' * 80)
            gdb.execute('quit')
        return False


def record_memory():
    '''
        Writes the memory file used for hexbox white list creation
    '''
    filename = get_filename()
    name, ext = os.path.splitext(filename)
    dump_mem('mem_accesses_' + name + '.bin')




BR_LIST = {'STM32469I_EVAL--peripheral--mpu-8--baseline.elf': '*SVC_Handler+110',
           'STM32469I_EVAL--filename-no-opt--mpu-8--hexbox--final.elf': 'hexbox-rt.c:365',
           'STM32469I_EVAL--filename--mpu-8--hexbox--final.elf': 'hexbox-rt.c:365',
           'STM32469I_EVAL--peripheral--mpu-8--hexbox--final.elf': 'hexbox-rt.c:365',
           'uVisor-pinlock.elf': 'stop_recording()'}


##############################################
#       HEXBOX & BASELINE STATS GLOBALS      #
##############################################
HEXBOX_STATS = OrderedDict([
    ('__hexbox_total_exe_time', []),
    ('__hexbox_init_exe_time', []),
    ('__hexbox_unknown_comp_exe_time', []),
    ('__hexbox_entry_exe_time', []),
    ('__hexbox_exit_exe_time', []),
    ('__hexbox_comp_exe_times', []),
    ('__hexbox_comp_emu_exe_times', []),
    ('__hexbox_entries', []),
    ('__hexbox_exits', []),
    ('__hexbox_comp_entries', []),
    ('__hexbox_comp_exits', []),
    ('__hexbox_comp_emu_calls', [])
])


BASELINE_STATS = OrderedDict([
                            ('runtime', [])
])

def collect_write_results(result_file, summary_filename, stack_measure_funct=None):
    '''
        Writes results to specified file
    '''
    global HEXBOX_STATS, BASELINE_STATS
    # open file with app_name

    results_summary = OrderedDict()
    app_filename = get_filename()
    file_info = app_filename.split('--')
    results_summary["App"] = file_info[0]
    results_summary['Policy'] = file_info[1]

    hexbox_total_exec_ave = 0
    with open(result_file, 'w') as res_file:
        # If we are collecting for hexbox
        metric_time_sum = 0
        metric_time_ave = 0
        if 'hexbox' in result_file:
            hexbox_total_exec_ave = get_total_exec_time_ave(HEXBOX_STATS['__hexbox_total_exe_time'])
            # loop through results and write them to the results file
            if stack_measure_funct:
                stack, heap, emulator, cmpt_size = stack_measure_funct()
                results_summary['Stack_Size'] = stack
                results_summary['Heap_Size'] = heap
                results_summary['Emu_Stack_Size'] = emulator
                results_summary['Comp_Stack_Size'] = cmpt_size
            for key in HEXBOX_STATS:
                all_iters_list = HEXBOX_STATS[key]
                metric_time_sum = 0     # RESET THE SUMMATION
                for iter_list in all_iters_list:
                    res_file.write(str(key)+",")
                    for val in iter_list:
                        res_file.write(str(val) + ",")
                    res_file.write("\n")
                    metric_time_sum += numpy.sum(iter_list)
                # Write ave, and if it is tot_exec, calc STDEV and write it
                metric_time_ave = float(metric_time_sum) / len(all_iters_list)
                results_summary[key + '_AVE'] = metric_time_ave
                res_file.write("AVE"+","+str(metric_time_ave))

                # ------------------------------------------------------------------------------------------------------
                # case(1): get stddev if we are calculating total_runtime
                if '__hexbox_total_exe_time' == key:
                    res_file.write("\n")
                    stdev_list = []
                    for iter_list in all_iters_list:
                        # runtime has only one value, so the index is 0
                        stdev_list.append(iter_list[0])
                    # ddof=1 is for a sample, 0 if for normally distibuted infinte sample
                    runtime_stddev = numpy.std(stdev_list, ddof=1) / \
                                     float(hexbox_total_exec_ave)
                    results_summary[key + '_STDDEV'] = runtime_stddev
                    res_file.write("STDDEV" + "," + str(runtime_stddev))

                # ------------------------------------------------------------------------------------------------------
                # case(2): calculate percentage of the metric
                else:
                    res_file.write("\n")
                    metric_percentage = 100*(float(metric_time_ave)/hexbox_total_exec_ave)
                    results_summary[key + '_PER'] = metric_percentage
                    res_file.write("PERCENTAGE"+","+str(metric_percentage))
                # ------------------------------------------------------------------------------------------------------

                res_file.write("\n")    # add 3 empty line for each collected metric
                res_file.write("\n")
                res_file.write("\n")
        else:
            # loop through results and write them to the results file
            print(BASELINE_STATS)
            if stack_measure_funct:
                stack, heap = stack_measure_funct(False)
                results_summary['Stack_Size'] = stack
                results_summary['Heap_Size'] = heap
            for key in BASELINE_STATS:
                all_iters_list = BASELINE_STATS[key]
                # Write the runtime results
                for runtime_val in all_iters_list:
                    # runtime_val is given as 1-element list, so take index1 as int
                    res_file.write(str(key) + "," + str(runtime_val[0]) + "\n")
                # Write ave, then calc STDEV and write it
                metric_time_ave = numpy.mean(all_iters_list)
                results_summary[key + '_AVE'] = metric_time_ave
                res_file.write("AVE"+","+str(metric_time_ave)+"\n")
                # ddof=1 is for a sample, 0 if for normally distibuted infinte sample
                runtime_stddev = numpy.std(all_iters_list, ddof=1) / metric_time_ave
                results_summary[key + '_STDDEV'] = runtime_stddev
                res_file.write("STDDEV"+","+str(runtime_stddev)+"\n")
                res_file.write("\n")  # add 3 empty line for each collected metric
                res_file.write("\n")
                res_file.write("\n")

        with open(summary_filename, 'wb') as outfile:
            wr = csv.DictWriter(outfile, results_summary.keys())
            wr.writeheader()
            wr.writerow(results_summary)

    print("-"*80)
    print("[+] Timing results have been written to file: %s" % result_file)
    print("-"*80)
    return


def get_total_exec_time_ave(runtime_list):
    res = 0
    runtime_iters = len(runtime_list)
    # check we correctly recorded all the results, # of rows should be == ITERATION_LIMIT
    if runtime_iters != ITERATION_LIMIT:
        print("[-] ERROR: runtime_iters != ITERATION_LIMIT, the average runtime is not being calculated correctly!!")
    for runtime in runtime_list:
        res += numpy.sum(runtime)
    ave_runtime = float(res)/runtime_iters
    return ave_runtime
##############################################
#              EXPERIMENT SETUP              #
##############################################



ITERATION_COUNTER = 0
ITERATION_LIMIT = 20
#hexbox_file_id = "hexbox--final.elf"
#elf_file_id = ".elf"
#timing_file_ext = "--timing.csv"
# RESULTS_DIR = '/home/clemen19/project/hexbox/results/usenix-security/Run1/uVisor/results/'    # specify dir to write results to, note the path here is absolute
#app_name = get_current_app()
#brkpt = BR_LIST[app_name]
#end_br = EndBreakpoint(brkpt, type=gdb.BP_BREAKPOINT)
# print('='*80)
#print('START:' + app_name)
#print('=' * 80)
# cl()
# gdb.execute('c')
