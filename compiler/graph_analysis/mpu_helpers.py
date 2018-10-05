
KB = 1024
MB = 1024*KB
GB = 1024*MB

def encode_size(size):
    value = size
    if size == 0:
        return 0;
    count = 0
    while value > 0:
        value = value >> 1
        count += 1

    count -= 2  #Counts one to many and field is size -1
    print "Size field value:",count
    return count

def get_AP_bits(PR,PW,UR,UW):
    lut_value = ((UW << 3)|( UR << 2)|(PW << 1)| PR)&0xF;
         # NO R | P-R | BAD | P-RW
    LUT = [0b000,0b101,0xBAD,0b001,  #No Unprivileged Access
           0xBAD,0b110,0xBAD,0b010,  # Unprivileged Read
           0xBAD,0xBAD,0xBAD,0xBAD, # Up Write without read not allowed
           0xBAD,0xBAD,0xBAD,0b011] #Unprivileged RW

    AP = LUT[lut_value]
    if AP == 0xBAD:
        print "Invalid Permissions Requested"
        return None
    return AP

def encode_mpu_attributes(XN,PR,PW,UR,UW,mem_type,size,enable,dis_sub=[]):
    attr =0;
    attr |= ((XN & 1) << 28)
    attr |= ((get_AP_bits(PR,PW,UR,UW) & 7) << 24)
    attr |= get_TEX_CBS(mem_type)
    attr |= (encode_size(size) & 0x1F ) << 1
    if size !=0:
        attr |= (enable & 1)
    else:
        attr |= (enable & 0)
    if size > 128 and len(dis_sub) > 0:
        for sub in dis_sub:
            if sub >=0 and sub < 8:
                attr |= ((1 << 8) << sub)  #sub regions bits 15:8
            else:
                print "Sub Regions must be in range [0,7] is:", sub
                raise ValueError
    elif (size <= 128 and len(dis_sub) > 0):
        print "Subregions only allowed when size > 128/ size is:", size
        raise ValueError
    return attr

def get_TEX_CBS(memory_type):
    '''
     Encode commonly used TEX and CBS setting into attr
     (TEX,C,B,S)
    '''
    attr =0
    if memory_type is 'FLASH':
        attr |= 0 &(7 << 19) #TEX
        attr |= (1<<17)    #C
        attr |= (0<<16)    #B
        attr |= (0<<18)    #S
    elif memory_type is 'INTERNAL_RAM':
        attr |= 0 &(7 << 19) #TEX
        attr |= (1<<17)    #C
        attr |= (0<<16)    #B
        attr |= (1<<18)    #S
    elif memory_type is 'EXTERNAL_RAM':
        attr |= 0 &(7 << 19) #TEX
        attr |= (1<<17)    #C
        attr |= (1<<16)    #B
        attr |= (1<<18)    #S
    elif memory_type is 'PERIPHERALS':
        attr |= 0 &(7 << 19) #TEX
        attr |= (0<<17)    #C
        attr |= (1<<16)    #B
        attr |= (1<<18)    #S
    else:
        print "Invalid Memory Type"
    return attr

def encode_addr(addr,num,enable):
   addr = addr & 0xFFFFFFE0
   addr |= num & 0xF
   addr |= (enable & 1) << 4
   return addr

def encode_mpu_region(MPU_config, n, addr, size, ty, dis_sub=[]):
    #print "0x%x " % addr
    MPU_config['Addrs'][n] = encode_addr(addr,n,1)
    if ty == 'FLASH-XR':
        MPU_config['Attrs'][n] = encode_mpu_attributes(0,1,0,1,0,'FLASH',size,1,dis_sub)
    elif ty == 'RAM-RW':
        MPU_config['Attrs'][n] = encode_mpu_attributes(1,1,1,1,1,'INTERNAL_RAM',size,1,dis_sub)
    elif ty == 'RAM-RO':
        MPU_config['Attrs'][n] = encode_mpu_attributes(1,1,1,1,0,'INTERNAL_RAM',size,1,dis_sub)
    else:
        MPU_config['Attrs'][n] = encode_mpu_attributes(1,1,1,1,1,'PERIPHERALS',size,1,dis_sub)


def disable_region(MPU_config,n):
    MPU_config['Addrs'][n] = encode_addr(0,0,0)
    MPU_config['Attrs'][n] = 0

if __name__ =='__main__':
    # Default Flash
    flash_default = encode_mpu_attributes(0,1,0,1,0,'FLASH',512*KB,1)
    flash_default_addr = encode_addr(0x08000000,0,1)
    ram_default = encode_mpu_attributes(1,1,1,1,1,'INTERNAL_RAM',128*KB,1)
    ram_default_addr = encode_addr(0x20000000,1,1)
    per_default = encode_mpu_attributes(1,1,1,1,1,'PERIPHERALS',512*MB,1)
    per_default_addr = encode_addr(0x40000000,6,1)
    hexbox_stack = encode_mpu_attributes(1,1,1,0,0,'INTERNAL_RAM',128,1)
    hexbox_stack_addr = encode_addr(0x20000000+128*KB-128,7,1)

    SCB = encode_mpu_attributes(1,1,1,1,1,'PERIPHERALS',0x1000,1)
    SCB_addr = encode_addr(0xE000E000,2,1)

    #Boxes
    flash_box1 = encode_mpu_attributes(0,1,0,1,0,'FLASH',1*KB,1)
    flash_box1_addr = encode_addr(0x08000000+(512*KB),2,1)
    ram_box1 = encode_mpu_attributes(0,1,0,1,0,'INTERNAL_RAM',1*KB,1)
    flash_box2 = encode_mpu_attributes(0,1,0,1,0,'FLASH',1*KB,1)
    flash_box2_addr = encode_addr(0x08000000+(513*KB),2,1)
    ram_box2 = encode_mpu_attributes(0,1,0,1,0,'INTERNAL_RAM',1*KB,1)

    #print "\nFlash Default: ", flash_default_addr, ",", flash_default
    #print "RAM Default: ", ram_default_addr, ",",  ram_default
    #print "Peripherals Default: ", per_default_addr, ",", per_default
    #print "Hexbox Stack Default: ", hexbox_stack_addr, ",",  hexbox_stack
    #print "SCB Default: ", SCB_addr, ",",  SCB

    #print ""
    #print "Box1 Flash: ", flash_box1_addr, ",", flash_box1
    #print "Box1 RAM: ", 0, ",", ram_box1
    #print "Box2 Flash: ", flash_box2_addr, ",",flash_box2
    #print "Box1 RAM: ", 0, ",", ram_box2
