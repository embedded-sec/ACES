
def write_linker(template_linker, linker_out, text_str,data_str):
    with open(template_linker) as infile:
        with open(linker_out,'w') as outfile:
            for line in infile.readlines():
                if '<HEXBOX_TEXT_SECTIONS>' in line:
                    outfile.write(text_str)
                elif '<HEXBOX_DATA_SECTIONS>' in line:
                    outfile.write(data_str)
                else:
                    outfile.write(line)

def make_linker_script(template_linker, linker_out, partitions):
    text_str, data_str = get_sections_strings_from_partition(partitions)
    write_linker(template_linker, linker_out, text_str,data_str)

def set_code_sections(name,addr,size):
    section = []
    section.append("\t%s 0x%x :" % (name,addr))
    section.append("\t{")
    section.append("\t_%s_start = .;" % name)
    section.append("\t*(%s);" % name)
    section.append("\t*(%s*);" % name)
    section.append("\t_%s_end = . ;" % name)
    section.append("\t} \n")
    return section

def set_ram_sections(name,addr,size):
    data_section = []
    start_var = name+"_vma_start"
    data_section_name = '%s_data' % name
    declare_str =  "%s = LOADADDR(%s);" % (start_var, data_section_name)
    data_section.append("\t%s" %declare_str)
    data_section.append("\t%s 0x%x :" % (data_section_name,addr))
    data_section.append("\t{")
    data_section.append("\t%s_data_start = .;" % name)
    #data_section.append("\t. = ALIGN(%i);" % align)
    data_section.append("\t%s_mpu_start = .;" % name)
    data_section.append("\t*(%s);" % data_section_name)
    data_section.append("\t*(%s*);" % data_section_name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section_end_var = "%s_data_end" % name
    data_section.append("\t%s = .;" % data_section_end_var)
    data_section.append("\t} AT>FLASH\n")
    # BSS Section
    bss_section_name = '%s_bss' %name
    data_section.append("\t%s %s :" % (bss_section_name,data_section_end_var))
    data_section.append("\t{")
    data_section.append("\t%s_bss_start = .;" % name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section.append("\t*(%s);" % bss_section_name)
    data_section.append("\t*(%s*);" % bss_section_name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section.append("\t%s_bss_end = .;" % name)
    data_section.append("\t} \n")
    return data_section

def get_code_sections(name, align, offset=False):
    text_section = []

    if offset:
        text_section.extend(add_flash_filler(offset,align))
    text_section.append("\t%s : " % (name))
    text_section.append("\t{")
    #text_section.append("\t. = ALIGN(%i);" % align)
    text_section.append("\tPROVIDE(%s_start = .);" % name)
    text_section.append("\t*(%s);" % name)
    text_section.append("\t*(%s*);" % name)
    text_section.append("\tPROVIDE(%s_end = . );" % name)
    text_section.append("\t} >FLASH\n")
    return text_section

def add_ram_filler(offset,align):
    data_section = []
    data_section.append("\t.ram_filler : ")
    data_section.append("\t{")
    data_section.append("\t\t. = . + %i;" % offset)
    data_section.append("\t\t. = ALIGN(%i);" % align)
    data_section.append("\t} >RAM\n")
    return data_section

def add_flash_filler(offset,align):
    data_section = []
    data_section.append("\t.flash_filler : ")
    data_section.append("\t{")
    data_section.append("\t\t. = . + %i;" % offset)
    data_section.append("\t\t. = ALIGN(%i);" % align)
    data_section.append("\t} >FLASH\n")
    return data_section

def get_data_sections(name,align,offset=False):
    data_section =[]
    if offset:
        data_section.extend(add_ram_filler(offset,align))
    #Data Section

    start_var = name+"_vma_start"
    data_section_name = '%s_data' % name
    declare_str =  "%s = LOADADDR(%s);" % (start_var, data_section_name)
    data_section.append("\t%s" %declare_str)
    data_section.append("\t%s :" % (data_section_name))
    data_section.append("\t{")
    data_section.append("\t%s_data_start = .;" % name)
    #data_section.append("\t. = ALIGN(%i);" % align)
    data_section.append("\t%s_mpu_start = .;" % name)
    data_section.append("\t*(%s);" % data_section_name)
    data_section.append("\t*(%s*);" % data_section_name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section.append("\t%s_data_end = .;" % name)
    data_section.append("\t} >RAM AT>FLASH\n")
    # BSS Section
    bss_section_name = '%s_bss' %name
    data_section.append("\t%s : " % (bss_section_name))
    data_section.append("\t{")
    data_section.append("\t%s_bss_start = .;" % name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section.append("\t*(%s);" % bss_section_name)
    data_section.append("\t*(%s*);" % bss_section_name)
    data_section.append("\t. = ALIGN(%i);" % 4)
    data_section.append("\t%s_bss_end = .;" % name)
    data_section.append("\t} >RAM\n")

    return data_section

def get_sections_strings_from_partition(partitions):
    data_section = []
    text_section = []
    for r_id in sorted(partitions['Regions'].keys()):
        region = partitions['Regions'][r_id]
        #print "Adding to Linker: ", r_id
        align = 0

        if region['Type'] =='Code':

            text_section.extend(get_code_sections(r_id,align))
        else:
            data_section.extend(get_data_sections(r_id,align))

    data_str = "\n".join(data_section)
    text_str = "\n".join(text_section)
    return text_str, data_str


def get_hexbox_rt_code_region():
    code_region = []
    code_region.append('    .hexbox_rt_code :')
    code_region.append('    {')
    code_region.append('        PROVIDE_HIDDEN(hexbox_rt_code__start = .);')
    code_region.append('        *(.hexbox_rt_code)')
    code_region.append('        *(.hexbox_rt_code*)')
    code_region.append('        PROVIDE_HIDDEN(hexbox_rt_code__end = .);')
    code_region.append('    } >FLASH')
    code_region.append('')
    return code_region


def get_hexbox_rt_data_region():
    data_region = []
    data_region.append('    .hexbox_rt_ram__vma_start = LOADADDR(.hexbox_rt_ram);')
    data_region.append('    .hexbox_rt_ram :')
    data_region.append('    {')
    data_region.append('    . = ALIGN(4);')
    data_region.append('    .hexbox_rt_ram__start = .;')
    data_region.append('    *(.hexbox_rt_ram);')
    data_region.append('    *(.hexbox_rt_ram*);')
    data_region.append('    . = ALIGN(4);')
    data_region.append('    .hexbox_rt_ram__end = .;')
    data_region.append('    } >RAM AT>FLASH')
    data_region.append('')
    return data_region


def next_power_2(size):
    if size == 0:
        return 0
    return 1 << (size - 1).bit_length()
