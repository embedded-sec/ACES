import os

TEXT_MAGIC_KEY ='<HEXBOX_TEXT_SECTIONS>'
DATA_MAGIC_KEY ='<HEXBOX_DATA_SECTIONS>'

def write_stack_section(outfile):
    outfile.write('  .stack :\n')
    outfile.write('  {\n')
    outfile.write('    . = . + _Min_Stack_Size - 4; \n')
    outfile.write('    _estack = .;\n')
    outfile.write('    . += 4;\n')
    outfile.write('  } >RAM\n\n')

def update_heap_end(outfile):
    outfile.write('    PROVIDE (_end_heap = . );\n')
    outfile.write('    PROVIDE (end_heap = . );\n')

def check_linker(ld_script):
    '''
        Makes sure that strings have not already been added to linker
    '''

    add_data = True
    add_text = True
    with open(ld_script,'r') as infile:
        for line in infile.readlines():
            if TEXT_MAGIC_KEY in line:
                add_text = False
            if DATA_MAGIC_KEY in line:
                add_data = False
    return add_text,add_data

def add_magic_strs_to_linker(ld_script):
    add_text, add_data = check_linker(ld_script)
    if not(add_text or add_data):
        return
    org_file = ld_script+'.org'
    os.rename(ld_script,org_file)
    with open(org_file,'r') as infile:
        with open(ld_script,'w') as outfile:
            for line in infile.readlines():
                if add_text and line.strip().startswith('.data'):
                    add_text = False
                    print "Added Text Comment"
                    outfile.write('  /* <HEXBOX_TEXT_SECTIONS> */\n')
                    write_stack_section(outfile)
                if add_data and line.strip().startswith('/DISCARD/'):
                    add_data = False
                    print "Added Data Comment"
                    outfile.write('/* <HEXBOX_DATA_SECTIONS> */\n')
                if line.strip().startswith("_estack"):
                    outfile.write("/* %s */\n"%line.strip('\n').strip('*/').strip("/*"))
                    continue
                if line.strip().startswith('. = . + _Min_Heap_Size;'):
                    outfile.write(line)
                    update_heap_end(outfile)
                    continue
                if line.strip().startswith('. = . + _Min_Stack_Size'):
                    outfile.write("/* %s */\n"%line.strip('\n'))
                    continue
                outfile.write(line)


def comment_if_disallowed(line,prohibit_list):
    for disallowed in prohibit_list:
        if line.strip() == disallowed:
            print "Commenting ", line,
            return "// "+line

    return line

def fix_up_asm(asm_file):
    #LLVM and GCC handle these differently
    disallowed_list = ['.cpu cortex-m4','.fpu softvfp','.thumb']
    org_file = asm_file + '.org'
    new_file = asm_file + '.new'
    with open(asm_file,'r') as infile:
        with open(new_file,'w') as outfile:
            for line in infile.readlines():
                line = comment_if_disallowed(line,disallowed_list)
                outfile.write(line)
    os.rename(asm_file,org_file)
    os.rename(new_file,asm_file)

def make_weak(line,handler_list):
    for handler in handler_list:
        if line.startswith(handler):
            return "__attribute__((weak)) "+line
    return line

def fix_up_handlers(input_file):

    handler_list = ['void MemManage_Handler',
                    'void SVC_Handler',
                    'void DebugMon_Handler']
    org_file = input_file + '.org'
    new_file = input_file + '.new'
    with open(input_file,'r') as infile:
        with open(new_file,'w') as outfile:
            for line in infile.readlines():
                line = make_weak(line,handler_list)
                outfile.write(line)
    os.rename(input_file,org_file)
    os.rename(new_file,input_file)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-a','--asm',dest='asm_file',
                        help= "Asm File to fix up")
    parser.add_argument('-l','--ld_script',dest='ld_script',
                        help= "Linker Script to add comments to")
    parser.add_argument('-h','--handler',dest='handler_file',
                        help= "Handler File to fix up",)

    args = parser.parse_args()
    if args.asm_file:
        fix_up_asm(args.asm_file);
    if args.ld_script:
        add_magic_strs_to_linker(args.ld_script)
    if args.handler_file:
        fix_up_handler_file(args.handler_file);

    if not (args.asm_file or args.ld_script or args.handler_file) :
        print "No input given"
        parser.print_usage()
