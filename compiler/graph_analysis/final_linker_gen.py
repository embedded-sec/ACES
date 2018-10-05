
import json
import subprocess
import csv
import operator
import ld_helpers
import pprint
import mpu_helpers


DEFAULT_RAM_SECTIONS = ['.data', '.bss', '._user_heap_stack',
                        '.stack', '.hexbox_rt_ram']
DEFAULT_FLASH_SECTIONS = ['.isr_vector', '.rodata', '.ARM.extab',
                          '.ARM', '.text', '.hexbox_rt_code']
DEFAULT_STACK_REGION = '.stack'

FLASH_ADDR = 0x08000000
FLASH_SIZE = 1*1024*1024
RAM_ADDR = 0x20000000
RAM_SIZE = 128*1024


'''
.isr_vector            392   134217728
.text                10536   134218120
.rodata                448   134228656
.ARM.extab              24   134229104
.ARM                   200   134229128
.data                 1096   536870912
.hexbox_text_0      512688   134229328
.hexbox_text_1         196   134742016
.hexbox_text_2         938   134742212
.ccmram                  0   268435456
.bss                    72   536872008
._user_heap_stack     1536   536872080
'''

def parse_size_data(size_output_str):
    data=size_output_str.split('\n')
    print data
    size_data ={}
    for line in data[2:]:# Skip first two lines
        fields = line.split()
        if len(fields) != 3:
            break
        name = fields[0]
        if name.endswith("_bss"):
            name = name[:-4]
        elif name.endswith("_data"):
            name = name[:-5]
        size = int(fields[1])
        if size >= 0:
            if size == 0:
                size = 0
            elif size <32:
                size = 32
            if size_data.has_key(name):
                size_data[name]['size'] += size
            else:
                size_data[name] = {'size':size,'addr':int(fields[2])}
    return size_data


def get_section_sizes(object_filename):
    #arm-none-eabi-size -A -d bin/temp.obj
    cmd =['arm-none-eabi-size', '-A','-d']
    cmd.append(object_filename)
    stdout = subprocess.check_output(cmd)
    size_data = parse_size_data(stdout)
    return size_data


def get_default_ram_sections(size_data):
    size = 0
    for name in DEFAULT_RAM_SECTIONS:
        size += size_data[name]['size']
    return size


def get_default_flash_sections(size_data):
    size = 0
    for name in DEFAULT_FLASH_SECTIONS:
        try:
            size += size_data[name]['size']
        except KeyError:
            print "Default section not present in final binary"
            pass
    return size


def create_flash_linker_string(flash_sorted_sections):
    '''
        Creates the linker string for all the flash regions.  Also returns a
        dictionary of the linker sections, with their start addr and sizes

    '''
    flash_regions ={}
    str_list = []
    hexbox_code = ld_helpers.get_hexbox_rt_code_region()
    str_list.extend(hexbox_code)
    last_flash_addr = FLASH_ADDR + FLASH_SIZE
    for section in flash_sorted_sections:
        name = section[0]
        size = ld_helpers.next_power_2(section[1])
        last_flash_addr = last_flash_addr - size
        addr = last_flash_addr
        flash_regions[name] = {'addr':addr,'size':size}
        str_list.extend(ld_helpers.set_code_sections(name,addr,size))
    text_str = "\n".join(str_list)
    return text_str, flash_regions


def create_ram_linker_string(ram_sorted_sections):
    ram_regions = {}
    hexbox_data = ld_helpers.get_hexbox_rt_data_region()
    str_list = []
    str_list.extend(hexbox_data)
    last_ram_addr = RAM_ADDR + RAM_SIZE
    for section in ram_sorted_sections:
        name = section[0]
        size = ld_helpers.next_power_2(section[1])
        last_ram_addr = last_ram_addr - size
        addr = last_ram_addr
        ram_regions[name] = {'addr':addr,'size':size}
        str_list.extend(ld_helpers.set_ram_sections(name,addr,size))
    data_str = "\n".join(str_list)
    return data_str,ram_regions


def get_sorted_sections(size_data):
    hexbox_flash_sections = {}
    hexbox_ram_sections = {}
    for name,data in size_data.items():
        addr = data['addr']
        aligned_size = ld_helpers.next_power_2(data['size'])
        if addr >= FLASH_ADDR  and addr < (FLASH_ADDR + FLASH_SIZE):
            if name not in DEFAULT_FLASH_SECTIONS:
                hexbox_flash_sections[name] = aligned_size
        elif addr >= RAM_ADDR  and addr < (RAM_ADDR + RAM_SIZE):
            if name not in DEFAULT_RAM_SECTIONS:
                hexbox_ram_sections[name] = aligned_size

    flash_sorted_sections = sorted(hexbox_flash_sections.items(), key=operator.itemgetter(1),reverse=True)
    ram_sorted_sections = sorted(hexbox_ram_sections.items(), key=operator.itemgetter(1), reverse=True)
    return (flash_sorted_sections , ram_sorted_sections)


def get_default_region(policy,size_data,size=8):
    default_conf ={
      "Attrs":[0] * size,
      "Addrs":[0] * size
    }
    policy["MPU_CONFIG"]["__hexbox_default"]=default_conf
    get_base_mpu_regions(policy["MPU_CONFIG"]["__hexbox_default"],size_data)


def get_mpu_config(policy,ld_regions,size_data):
    '''
     Builds the mpu configs for each of the compartments, these are assigned to
     regions MPU_R3-MPU_R6
    '''
    size = policy["NUM_MPU_REGIONS"]
    get_default_region(policy,size_data)
    for region in ld_regions:

    #for comp_name,comp_data in policy['Compartments'].items():
        print region
        if not policy["Compartments"].has_key(region):
            continue
        print "Getting MPU Config: ", region
        comp_data = policy["Compartments"][region]
        MPU_config = policy['MPU_CONFIG'][region]

        get_base_mpu_regions(MPU_config, size_data)
        #Code Region
        size = ld_regions[region]['size']
        addr = ld_regions[region]['addr']
        # This compartment code region
        mpu_helpers.encode_mpu_region(MPU_config, 3,addr,size,'FLASH-XR')
        n = 4
        comp_data = policy["Compartments"][region]
        for data_name in comp_data['Data']:
            size = ld_regions[data_name]['size']
            addr = ld_regions[data_name]['addr']
            mpu_helpers.encode_mpu_region(MPU_config,n,addr,size,'RAM-RW')
            n += 1
        for p_data in comp_data['Peripherals']:
            size = 2**p_data['Size']
            addr = p_data['Addr']
            mpu_helpers.encode_mpu_region(MPU_config,n,addr,size,'PER-RW')
            n += 1
        for i in range(n,8):
            mpu_helpers.disable_region(MPU_config,n)
        #if n >8:
            # print "To many regions in policy file for compartment: ",comp_data
        #    quit(-1)


def get_base_mpu_regions(MPU_config,size_data):

    default_flash_size = get_default_flash_sections(size_data)
    default_ram_size = get_default_ram_sections(size_data)
    flash_pow_size = ld_helpers.next_power_2(default_flash_size);
    ram_pow_size = ld_helpers.next_power_2(default_ram_size);

    mpu_helpers.encode_mpu_region(MPU_config,0,0,4*1024*1024*1024,'RAM-RO',[0,7])
    mpu_helpers.encode_mpu_region(MPU_config,1,FLASH_ADDR,flash_pow_size,'FLASH-XR')
    #mpu_helpers.encode_mpu_region(MPU_config,2,RAM_ADDR,ram_pow_size,'RAM-RW')
    stack_pwr_2 =  ld_helpers.next_power_2(size_data[DEFAULT_STACK_REGION]['size'])
    stack_addr = size_data[DEFAULT_STACK_REGION]['addr']
    # print "Stack Base Addr 0x%08x" % stack_addr
    mpu_helpers.encode_mpu_region(MPU_config,2,stack_addr,stack_pwr_2,'RAM-RW')


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o','--object',dest='object_filename',required=True,
                        help='Object File')
    parser.add_argument('-t','--templater',dest='template',required=True,
                        help='Template linker script')
    parser.add_argument('-l','--linker_script',dest='ld_script', required=True,
                         help='Name of output filename')
    parser.add_argument('-p','--policy',dest='policy_file', required = True,
                        help = "Policy file used to derive the permissions for each region")
    parser.add_argument('-f','--final_policy',dest='final_policy', required = True,
                        help = "Copy of Policy file with the permissions specified")

    args = parser.parse_args()

    size_data = get_section_sizes(args.object_filename)
    # print size_data
    default_ram_size = get_default_ram_sections(size_data)
    # print default_ram_size
    default_flash_size = get_default_flash_sections(size_data)
    flash_pow_size = ld_helpers.next_power_2(default_flash_size);
    ram_pow_size = ld_helpers.next_power_2(default_ram_size);
    # print default_flash_size

    (flash_sorted_sections , ram_sorted_sections) = get_sorted_sections(size_data)
    # print flash_sorted_sections
    # print ram_sorted_sections
    text_str,flash_regions = create_flash_linker_string(flash_sorted_sections)
    data_str,ram_regions = create_ram_linker_string(ram_sorted_sections)
    ld_helpers.write_linker(args.template, args.ld_script, text_str, data_str)

    with open(args.policy_file,'rb') as in_policy:
        policy = json.load(in_policy)

    ld_regions = flash_regions.copy()
    ld_regions.update(ram_regions)
    get_mpu_config(policy,ld_regions,size_data)


    with open(args.final_policy,'wb') as out_file:
        json.dump(policy,out_file,sort_keys=True, indent=4, separators=(',', ': '))
