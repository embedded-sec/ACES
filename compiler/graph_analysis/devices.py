'''This file defines a single variable that defines the peripherals for
supported devices
'''
from key_defs import *
import networkx as nx

EXCLUDE = "EXCLUDE"


def get_device_desc(device_name):

    peripherals = DEVICE_DEFS[device_name][PERIPHERAL_KEY]
    for p in peripherals:
        p[TYPE_KEY] = PERIPHERAL_NODE_TYPE

    for inc in DEVICE_DEFS[device_name][INCLUDE_KEY]:
        desc, T = get_device_desc(inc)
        peripherals.extend(desc)
    desc = sorted(peripherals, key=lambda k: k[BASE_ADDR_KEY])

    T = build_mpu_region_tree(desc)
    return (desc, T)


def get_peripheral_dict(device_desc, base_addr,size):
    for device in device_desc:
        if base_addr >= device[BASE_ADDR_KEY] and \
           base_addr <= device[END_ADDR_KEY]:
            return device
    return None


def next_power_2(size):
    return 1 << (size - 1).bit_length()


def next_power_2_pwr(size):
    return (size - 1).bit_length()


def get_mpu_region_node(start_addr, size):
    attrs = { BASE_ADDR_KEY: start_addr,
              PWR2_SIZE_KEY: size,
              TYPE_KEY: PERIPHERAL_REGION_KEY,
              PERIPHERAL_REGION_KEY: -1,
              PRIV_KEY: False }
    name = str("0x%08x" % start_addr) + "_" + str(size)
    return(name, attrs)


def get_mpu_regions_root():
    return get_mpu_region_node(0, 32)


def add_mpu_region(T, p, start_addr, pwr2size):
    node, node_attrs = get_mpu_region_node(start_addr, pwr2size)

    if not T.has_node(node):
        T.add_node(node, node_attrs)
        pwr2size += 1
        start_addr = start_addr & ~(2**pwr2size - 1)
        add_mpu_region(T, node, start_addr, pwr2size)
    T.add_edge(node, p)


def set_peripheral_flag(T,n):
    T.node[n][PRIV_KEY] = True;
    for pre in T.predecessors(n):
        set_peripheral_flag(T, pre)

def add_privilege_flags(T, peripherals):
    for per in peripherals:
        per_name = per[NAME_KEY]
        if per.has_key(PRIV_KEY) and per[PRIV_KEY]:
            set_peripheral_flag(T,per_name)


def simplifiy_mpu_region_tree(T,root):
    '''
        Removes any mpu region nodes with only one child mpu region node
        keeping the child. This makes it so the smallest MPU regions to cover
        its leaves is kept
    '''
    successor_list = T.successors(root)
    if len(successor_list) == 1:
        s = successor_list[0]
        if T.node[s][TYPE_KEY] == PERIPHERAL_REGION_KEY:
            p = T.predecessors(root)
            if len(p) > 0:
                T.add_edge(p[0], s)
                T.remove_node(root)
            simplifiy_mpu_region_tree(T, s)
    else:
        for s in successor_list:
            simplifiy_mpu_region_tree(T, s)


def remove_predecessors(T,node):
    for p in T.predecessors(node):
        remove_predecessors(T, p)
        if T.has_node(p):
            T.remove_node(p)


def remove_prohibited_merges(T):
    no_merge_nodes = []
    for node, attr in T.nodes(True):
        if attr.has_key(EXCLUDE) and attr[EXCLUDE]:
            # Note want to keep first predecessor of the peripheral node
            no_merge_nodes.append(node)

    for node in no_merge_nodes:
        remove_predecessors(T,node)
        T.remove_node(node)


def get_nearest_common_ancestor(T, n1, n2):
    Undirected_T = T.to_undirected()
    try:
        path = nx.shortest_path(Undirected_T, n1, n2)
        for n in path:
            for p in T.predecessors(n):
                # The MPU region that covers p1,p2 is the node with no parent
                #on the path, i.e. nearest ancestor
                if not (p in path):
                    return n
    except nx.exception.NetworkXNoPath:
        return None


def is_child(T, p, c):
    try:
        path = nx.shortest_path(T, p, c)
        return True
    except nx.exception.NetworkXNoPath:
        return False


def get_covered_peripherals(T, n1, n2=None):
    '''
     Determines how many peripherals are covered
     either between two nodes or by n1
    '''
    if n2 is None:
        ancestor = n1
    else:
        ancestor = get_nearest_common_ancestor(T, n1, n2)
    if ancestor is not None:
        return get_leaves(T, ancestor)


def get_leaves(T, node):
    successor_list = T.successors(node)
    leaves = set()
    if len(successor_list) == 0:
        leaves.add(node)
    for s in T.successors(node):
        leaves.update(get_leaves(T, s))
    return leaves


def build_mpu_region_tree(devices_desc):
    '''
        Builds a tree of MPU regions that cover the peripherals
        This is a sparse binary tree with the leaves being the peripherals
        and the internal nodes being mpu regions.  The peripherals coverd by
        the region can be found by getting all the leaves of a node

        In additon the minimal covering of a two peripherals can be found by
        finding their common ancestor, and counting it leaves
    '''
    T = nx.DiGraph()
    root_name, root_attrs = get_mpu_regions_root()
    T.add_node(root_name, root_attrs)
    for p in devices_desc:
        T.add_node(p[NAME_KEY], p)
        pwr2size = next_power_2_pwr(p[END_ADDR_KEY] - p[BASE_ADDR_KEY] + 1)
        start_addr = p[BASE_ADDR_KEY] & ~(2**pwr2size - 1)
        if p[BASE_ADDR_KEY] & (2**pwr2size - 1):
            pwr2size += 1
        add_mpu_region(T, p[NAME_KEY], start_addr, pwr2size)
    #  nx.drawing.nx_pydot.write_dot(T, "mpu_full_map.dot")
    remove_prohibited_merges(T)

    #  nx.drawing.nx_pydot.write_dot(T, "illegals_removed.dot")

    for node in T.nodes():
        if T.has_node(node) and len(T.predecessors(node)) == 0:
            simplifiy_mpu_region_tree(T, node)
    add_privilege_flags(T, devices_desc)
    #  nx.drawing.nx_pydot.write_dot(T,"mpu_simplified_map.dot")
    return T

DEVICE_DEFS = {
  "STM32F479":{
    INCLUDE_KEY:["ARMv7-M"],
    PERIPHERAL_KEY:[
      {NAME_KEY:"FMC",          BASE_ADDR_KEY:0xA0000000,END_ADDR_KEY:0xA0000FFF},
      {NAME_KEY:"QUAD-SPI",     BASE_ADDR_KEY:0xA0001000,END_ADDR_KEY:0xA0001FFF},
      {NAME_KEY:"RNG",          BASE_ADDR_KEY:0x50060800,END_ADDR_KEY:0x50060BFF},
      {NAME_KEY:"HASH",         BASE_ADDR_KEY:0x50060400,END_ADDR_KEY:0x500607FF},
      {NAME_KEY:"CRYP",         BASE_ADDR_KEY:0x50060000,END_ADDR_KEY:0x500603FF},
      {NAME_KEY:"DCMI",         BASE_ADDR_KEY:0x50050000,END_ADDR_KEY:0x500503FF},
      {NAME_KEY:"USB-OTG-FS",   BASE_ADDR_KEY:0x50000000,END_ADDR_KEY:0x5003FFFF},
      {NAME_KEY:"USB-OTG-HS",   BASE_ADDR_KEY:0x40040000,END_ADDR_KEY:0x4007FFFF},
      {NAME_KEY:"Chrom-ART",     BASE_ADDR_KEY:0x4002B000,END_ADDR_KEY:0x4002BBFF},
      {NAME_KEY:"ETHERNET-MAC5", BASE_ADDR_KEY:0x40029000,END_ADDR_KEY:0x400293FF},
      {NAME_KEY:"ETHERNET-MAC4", BASE_ADDR_KEY:0x40028C00,END_ADDR_KEY:0x40028FFF},
      {NAME_KEY:"ETHERNET-MAC3", BASE_ADDR_KEY:0x40028800,END_ADDR_KEY:0x40028BFF},
      {NAME_KEY:"ETHERNET-MAC2", BASE_ADDR_KEY:0x40028400,END_ADDR_KEY:0x400287FF},
      {NAME_KEY:"ETHERNET-MAC1", BASE_ADDR_KEY:0x40028000,END_ADDR_KEY:0x400283FF},
      {NAME_KEY:"DMA2",         BASE_ADDR_KEY:0x40026400,END_ADDR_KEY:0x400267FF},
      {NAME_KEY:"DMA1",         BASE_ADDR_KEY:0x40026000,END_ADDR_KEY:0x400263FF},
      {NAME_KEY:"BKPSRAM",      BASE_ADDR_KEY:0x40024000,END_ADDR_KEY:0x40024FFF},
      {NAME_KEY:"FLASH-Inte",   BASE_ADDR_KEY:0x40023C00,END_ADDR_KEY:0x40023FFF},
      {NAME_KEY:"RCC",          BASE_ADDR_KEY:0x40023800,END_ADDR_KEY:0x40023BFF},
      {NAME_KEY:"CRC",          BASE_ADDR_KEY:0x40023000,END_ADDR_KEY:0x400233FF},
      {NAME_KEY:"GPIOK",        BASE_ADDR_KEY:0x40022800,END_ADDR_KEY:0x40022BFF},
      {NAME_KEY:"GPIOJ",        BASE_ADDR_KEY:0x40022400,END_ADDR_KEY:0x400227FF},
      {NAME_KEY:"GPIOI",        BASE_ADDR_KEY:0x40022000,END_ADDR_KEY:0x400223FF},
      {NAME_KEY:"GPIOH",        BASE_ADDR_KEY:0x40021C00,END_ADDR_KEY:0x40021FFF},
      {NAME_KEY:"GPIOG",        BASE_ADDR_KEY:0x40021800,END_ADDR_KEY:0x40021BFF},
      {NAME_KEY:"GPIOF",        BASE_ADDR_KEY:0x40021400,END_ADDR_KEY:0x400217FF},
      {NAME_KEY:"GPIOE",        BASE_ADDR_KEY:0x40021000,END_ADDR_KEY:0x400213FF},
      {NAME_KEY:"GPIOD",        BASE_ADDR_KEY:0x40020C00,END_ADDR_KEY:0x40020FFF},
      {NAME_KEY:"GPIOC",        BASE_ADDR_KEY:0x40020800,END_ADDR_KEY:0x40020BFF},
      {NAME_KEY:"GPIOB",        BASE_ADDR_KEY:0x40020400,END_ADDR_KEY:0x400207FF},
      {NAME_KEY:"GPIOA",        BASE_ADDR_KEY:0x40020000,END_ADDR_KEY:0x400203FF},
      {NAME_KEY:"DSI-Host",     BASE_ADDR_KEY:0x40016C00,END_ADDR_KEY:0x400173FF},
      {NAME_KEY:"LCD-TFT",      BASE_ADDR_KEY:0x40016800,END_ADDR_KEY:0x40016BFF},
      {NAME_KEY:"SAI1",         BASE_ADDR_KEY:0x40015800,END_ADDR_KEY:0x40015BFF},
      {NAME_KEY:"SPI6",         BASE_ADDR_KEY:0x40015400,END_ADDR_KEY:0x400157FF},
      {NAME_KEY:"SPI5",         BASE_ADDR_KEY:0x40015000,END_ADDR_KEY:0x400153FF},
      {NAME_KEY:"TIM11",        BASE_ADDR_KEY:0x40014800,END_ADDR_KEY:0x40014BFF},
      {NAME_KEY:"TIM10",        BASE_ADDR_KEY:0x40014400,END_ADDR_KEY:0x400147FF},
      {NAME_KEY:"TIM9",         BASE_ADDR_KEY:0x40014000,END_ADDR_KEY:0x400143FF},
      {NAME_KEY:"EXTI",         BASE_ADDR_KEY:0x40013C00,END_ADDR_KEY:0x40013FFF},
      {NAME_KEY:"SYSCFG",       BASE_ADDR_KEY:0x40013800,END_ADDR_KEY:0x40013BFF},
      {NAME_KEY:"SPI4",         BASE_ADDR_KEY:0x40013400,END_ADDR_KEY:0x400137FF},
      {NAME_KEY:"SPI1",         BASE_ADDR_KEY:0x40013000,END_ADDR_KEY:0x400133FF},
      {NAME_KEY:"SDIO",         BASE_ADDR_KEY:0x40012C00,END_ADDR_KEY:0x40012FFF},
      {NAME_KEY:"ADC1-3",       BASE_ADDR_KEY:0x40012000,END_ADDR_KEY:0x400123FF},
      {NAME_KEY:"USART6",       BASE_ADDR_KEY:0x40011400,END_ADDR_KEY:0x400117FF},
      {NAME_KEY:"USART1",       BASE_ADDR_KEY:0x40011000,END_ADDR_KEY:0x400113FF},
      {NAME_KEY:"TIM8",         BASE_ADDR_KEY:0x40010400,END_ADDR_KEY:0x400107FF},
      {NAME_KEY:"TIM1",         BASE_ADDR_KEY:0x40010000,END_ADDR_KEY:0x400103FF},
      {NAME_KEY:"USART8",       BASE_ADDR_KEY:0x40007C00,END_ADDR_KEY:0x40007FFF},
      {NAME_KEY:"USART7",       BASE_ADDR_KEY:0x40007800,END_ADDR_KEY:0x40007BFF},
      {NAME_KEY:"DAC",          BASE_ADDR_KEY:0x40007400,END_ADDR_KEY:0x400077FF},
      {NAME_KEY:"PWR",          BASE_ADDR_KEY:0x40007000,END_ADDR_KEY:0x400073FF},
      {NAME_KEY:"CAN2",         BASE_ADDR_KEY:0x40006800,END_ADDR_KEY:0x40006BFF},
      {NAME_KEY:"CAN1",         BASE_ADDR_KEY:0x40006400,END_ADDR_KEY:0x400067FF},
      {NAME_KEY:"I2C3",         BASE_ADDR_KEY:0x40005C00,END_ADDR_KEY:0x40005FFF},
      {NAME_KEY:"I2C2",         BASE_ADDR_KEY:0x40005800,END_ADDR_KEY:0x40005BFF},
      {NAME_KEY:"I2C1",         BASE_ADDR_KEY:0x40005400,END_ADDR_KEY:0x400057FF},
      {NAME_KEY:"UART5",        BASE_ADDR_KEY:0x40005000,END_ADDR_KEY:0x400053FF},
      {NAME_KEY:"UART4",        BASE_ADDR_KEY:0x40004C00,END_ADDR_KEY:0x40004FFF},
      {NAME_KEY:"USART3",       BASE_ADDR_KEY:0x40004800,END_ADDR_KEY:0x40004BFF},
      {NAME_KEY:"USART2",       BASE_ADDR_KEY:0x40004400,END_ADDR_KEY:0x400047FF},
      {NAME_KEY:"I2S3ext",      BASE_ADDR_KEY:0x40004000,END_ADDR_KEY:0x400043FF},
      {NAME_KEY:"SPI3",         BASE_ADDR_KEY:0x40003C00,END_ADDR_KEY:0x40003FFF},
      {NAME_KEY:"SPI2",         BASE_ADDR_KEY:0x40003800,END_ADDR_KEY:0x40003BFF},
      {NAME_KEY:"I2S2ext",      BASE_ADDR_KEY:0x40003400,END_ADDR_KEY:0x400037FF},
      {NAME_KEY:"IWDG",         BASE_ADDR_KEY:0x40003000,END_ADDR_KEY:0x400033FF},
      {NAME_KEY:"WWDG",         BASE_ADDR_KEY:0x40002C00,END_ADDR_KEY:0x40002FFF},
      {NAME_KEY:"RTC-BKP",      BASE_ADDR_KEY:0x40002800,END_ADDR_KEY:0x40002BFF},
      {NAME_KEY:"TIM14",        BASE_ADDR_KEY:0x40002000,END_ADDR_KEY:0x400023FF},
      {NAME_KEY:"TIM13",        BASE_ADDR_KEY:0x40001C00,END_ADDR_KEY:0x40001FFF},
      {NAME_KEY:"TIM12",        BASE_ADDR_KEY:0x40001800,END_ADDR_KEY:0x40001BFF},
      {NAME_KEY:"TIM7",         BASE_ADDR_KEY:0x40001400,END_ADDR_KEY:0x400017FF},
      {NAME_KEY:"TIM6",         BASE_ADDR_KEY:0x40001000,END_ADDR_KEY:0x400013FF},
      {NAME_KEY:"TIM5",         BASE_ADDR_KEY:0x40000C00,END_ADDR_KEY:0x40000FFF},
      {NAME_KEY:"TIM4",         BASE_ADDR_KEY:0x40000800,END_ADDR_KEY:0x40000BFF},
      {NAME_KEY:"TIM3",         BASE_ADDR_KEY:0x40000400,END_ADDR_KEY:0x400007FF},
      {NAME_KEY:"TIM2",         BASE_ADDR_KEY:0x40000000,END_ADDR_KEY:0x400003FF},
      {NAME_KEY:"Unknown",      BASE_ADDR_KEY:0x42470000,END_ADDR_KEY:0x4247FFFF},
      {NAME_KEY:"Unknown2",      BASE_ADDR_KEY:0x42258000,END_ADDR_KEY:0x42258FFF},
      {NAME_KEY:"EXT_DEV",      BASE_ADDR_KEY:0xC0000000,END_ADDR_KEY:0xCFFFFFFF},
      {NAME_KEY:"Non-Periph",   BASE_ADDR_KEY:0x00000000,END_ADDR_KEY:0x3FFFFFFF,EXCLUDE:True}
    ]
  },
  "STM32F4Discovery":{
    INCLUDE_KEY:["ARMv7-M"],
    PERIPHERAL_KEY:[
      {NAME_KEY:"FSMC",          BASE_ADDR_KEY:0xA0000000,END_ADDR_KEY:0xA0000FFF},
      {NAME_KEY:"RNG",           BASE_ADDR_KEY:0x50060800,END_ADDR_KEY:0x50060BFF},
      {NAME_KEY:"HASH",          BASE_ADDR_KEY:0x50060400,END_ADDR_KEY:0x500607FF},
      {NAME_KEY:"CRYP",          BASE_ADDR_KEY:0x50060000,END_ADDR_KEY:0x500603FF},
      {NAME_KEY:"DCMI",          BASE_ADDR_KEY:0x50050000,END_ADDR_KEY:0x500503FF},
      {NAME_KEY:"USB-OTG-FS",    BASE_ADDR_KEY:0x50000000,END_ADDR_KEY:0x5003FFFF},
      {NAME_KEY:"USB-OTG-HS",    BASE_ADDR_KEY:0x40040000,END_ADDR_KEY:0x4007FFFF},
      {NAME_KEY:"DMA2D",         BASE_ADDR_KEY:0x4002B000,END_ADDR_KEY:0x4002BBFF},
      {NAME_KEY:"ETHERNET-MAC5", BASE_ADDR_KEY:0x40029000,END_ADDR_KEY:0x400293FF},
      {NAME_KEY:"ETHERNET-MAC4", BASE_ADDR_KEY:0x40028C00,END_ADDR_KEY:0x40028FFF},
      {NAME_KEY:"ETHERNET-MAC3", BASE_ADDR_KEY:0x40028800,END_ADDR_KEY:0x40028BFF},
      {NAME_KEY:"ETHERNET-MAC2", BASE_ADDR_KEY:0x40028400,END_ADDR_KEY:0x400287FF},
      {NAME_KEY:"ETHERNET-MAC1", BASE_ADDR_KEY:0x40028000,END_ADDR_KEY:0x400283FF},
      {NAME_KEY:"DMA2",          BASE_ADDR_KEY:0x40026400,END_ADDR_KEY:0x400267FF},
      {NAME_KEY:"DMA1",          BASE_ADDR_KEY:0x40026000,END_ADDR_KEY:0x400263FF},
      {NAME_KEY:"BKPSRAM",       BASE_ADDR_KEY:0x40024000,END_ADDR_KEY:0x40024FFF},
      {NAME_KEY:"FLASH-Inte",    BASE_ADDR_KEY:0x40023C00,END_ADDR_KEY:0x40023FFF},
      {NAME_KEY:"RCC",           BASE_ADDR_KEY:0x40023800,END_ADDR_KEY:0x40023BFF},
      {NAME_KEY:"CRC",           BASE_ADDR_KEY:0x40023000,END_ADDR_KEY:0x400233FF},
      {NAME_KEY:"GPIOK",         BASE_ADDR_KEY:0x40022800,END_ADDR_KEY:0x40022BFF},
      {NAME_KEY:"GPIOJ",         BASE_ADDR_KEY:0x40022400,END_ADDR_KEY:0x400227FF},
      {NAME_KEY:"GPIOI",         BASE_ADDR_KEY:0x40022000,END_ADDR_KEY:0x400223FF},
      {NAME_KEY:"GPIOH",         BASE_ADDR_KEY:0x40021C00,END_ADDR_KEY:0x40021FFF},
      {NAME_KEY:"GPIOG",         BASE_ADDR_KEY:0x40021800,END_ADDR_KEY:0x40021BFF},
      {NAME_KEY:"GPIOF",         BASE_ADDR_KEY:0x40021400,END_ADDR_KEY:0x400217FF},
      {NAME_KEY:"GPIOE",         BASE_ADDR_KEY:0x40021000,END_ADDR_KEY:0x400213FF},
      {NAME_KEY:"GPIOD",         BASE_ADDR_KEY:0x40020C00,END_ADDR_KEY:0x40020FFF},
      {NAME_KEY:"GPIOC",         BASE_ADDR_KEY:0x40020800,END_ADDR_KEY:0x40020BFF},
      {NAME_KEY:"GPIOB",         BASE_ADDR_KEY:0x40020400,END_ADDR_KEY:0x400207FF},
      {NAME_KEY:"GPIOA",         BASE_ADDR_KEY:0x40020000,END_ADDR_KEY:0x400203FF},
      {NAME_KEY:"LCD-TFT",       BASE_ADDR_KEY:0x40016800,END_ADDR_KEY:0x40016BFF},
      {NAME_KEY:"SAI1",          BASE_ADDR_KEY:0x40015800,END_ADDR_KEY:0x40015BFF},
      {NAME_KEY:"SPI6",          BASE_ADDR_KEY:0x40015400,END_ADDR_KEY:0x400157FF},
      {NAME_KEY:"SPI5",          BASE_ADDR_KEY:0x40015000,END_ADDR_KEY:0x400153FF},
      {NAME_KEY:"TIM11",         BASE_ADDR_KEY:0x40014800,END_ADDR_KEY:0x40014BFF},
      {NAME_KEY:"TIM10",         BASE_ADDR_KEY:0x40014400,END_ADDR_KEY:0x400147FF},
      {NAME_KEY:"TIM9",          BASE_ADDR_KEY:0x40014000,END_ADDR_KEY:0x400143FF},
      {NAME_KEY:"EXTI",          BASE_ADDR_KEY:0x40013C00,END_ADDR_KEY:0x40013FFF},
      {NAME_KEY:"SYSCFG",        BASE_ADDR_KEY:0x40013800,END_ADDR_KEY:0x40013BFF},
      {NAME_KEY:"SPI4",          BASE_ADDR_KEY:0x40013400,END_ADDR_KEY:0x400137FF},
      {NAME_KEY:"SPI1",          BASE_ADDR_KEY:0x40013000,END_ADDR_KEY:0x400133FF},
      {NAME_KEY:"SDIO",          BASE_ADDR_KEY:0x40012C00,END_ADDR_KEY:0x40012FFF},
      {NAME_KEY:"ADC1-3",        BASE_ADDR_KEY:0x40012000,END_ADDR_KEY:0x400123FF},
      {NAME_KEY:"USART6",        BASE_ADDR_KEY:0x40011400,END_ADDR_KEY:0x400117FF},
      {NAME_KEY:"USART1",        BASE_ADDR_KEY:0x40011000,END_ADDR_KEY:0x400113FF},
      {NAME_KEY:"TIM8",          BASE_ADDR_KEY:0x40010400,END_ADDR_KEY:0x400107FF},
      {NAME_KEY:"TIM1",          BASE_ADDR_KEY:0x40010000,END_ADDR_KEY:0x400103FF},
      {NAME_KEY:"USART8",        BASE_ADDR_KEY:0x40007C00,END_ADDR_KEY:0x40007FFF},
      {NAME_KEY:"USART7",        BASE_ADDR_KEY:0x40007800,END_ADDR_KEY:0x40007BFF},
      {NAME_KEY:"DAC",           BASE_ADDR_KEY:0x40007400,END_ADDR_KEY:0x400077FF},
      {NAME_KEY:"PWR",           BASE_ADDR_KEY:0x40007000,END_ADDR_KEY:0x400073FF},
      {NAME_KEY:"CAN2",          BASE_ADDR_KEY:0x40006800,END_ADDR_KEY:0x40006BFF},
      {NAME_KEY:"CAN1",          BASE_ADDR_KEY:0x40006400,END_ADDR_KEY:0x400067FF},
      {NAME_KEY:"I2C3",          BASE_ADDR_KEY:0x40005C00,END_ADDR_KEY:0x40005FFF},
      {NAME_KEY:"I2C2",          BASE_ADDR_KEY:0x40005800,END_ADDR_KEY:0x40005BFF},
      {NAME_KEY:"I2C1",          BASE_ADDR_KEY:0x40005400,END_ADDR_KEY:0x400057FF},
      {NAME_KEY:"UART5",         BASE_ADDR_KEY:0x40005000,END_ADDR_KEY:0x400053FF},
      {NAME_KEY:"UART4",         BASE_ADDR_KEY:0x40004C00,END_ADDR_KEY:0x40004FFF},
      {NAME_KEY:"USART3",        BASE_ADDR_KEY:0x40004800,END_ADDR_KEY:0x40004BFF},
      {NAME_KEY:"USART2",        BASE_ADDR_KEY:0x40004400,END_ADDR_KEY:0x400047FF},
      {NAME_KEY:"I2S3ext",       BASE_ADDR_KEY:0x40004000,END_ADDR_KEY:0x400043FF},
      {NAME_KEY:"SPI3",          BASE_ADDR_KEY:0x40003C00,END_ADDR_KEY:0x40003FFF},
      {NAME_KEY:"SPI2",          BASE_ADDR_KEY:0x40003800,END_ADDR_KEY:0x40003BFF},
      {NAME_KEY:"I2S2ext",       BASE_ADDR_KEY:0x40003400,END_ADDR_KEY:0x400037FF},
      {NAME_KEY:"IWDG",          BASE_ADDR_KEY:0x40003000,END_ADDR_KEY:0x400033FF},
      {NAME_KEY:"WWDG",          BASE_ADDR_KEY:0x40002C00,END_ADDR_KEY:0x40002FFF},
      {NAME_KEY:"RTC-BKP",       BASE_ADDR_KEY:0x40002800,END_ADDR_KEY:0x40002BFF},
      {NAME_KEY:"TIM14",         BASE_ADDR_KEY:0x40002000,END_ADDR_KEY:0x400023FF},
      {NAME_KEY:"TIM13",         BASE_ADDR_KEY:0x40001C00,END_ADDR_KEY:0x40001FFF},
      {NAME_KEY:"TIM12",         BASE_ADDR_KEY:0x40001800,END_ADDR_KEY:0x40001BFF},
      {NAME_KEY:"TIM7",          BASE_ADDR_KEY:0x40001400,END_ADDR_KEY:0x400017FF},
      {NAME_KEY:"TIM6",          BASE_ADDR_KEY:0x40001000,END_ADDR_KEY:0x400013FF},
      {NAME_KEY:"TIM5",          BASE_ADDR_KEY:0x40000C00,END_ADDR_KEY:0x40000FFF},
      {NAME_KEY:"TIM4",          BASE_ADDR_KEY:0x40000800,END_ADDR_KEY:0x40000BFF},
      {NAME_KEY:"TIM3",          BASE_ADDR_KEY:0x40000400,END_ADDR_KEY:0x400007FF},
      {NAME_KEY:"TIM2",          BASE_ADDR_KEY:0x40000000,END_ADDR_KEY:0x400003FF},
      {NAME_KEY:"Unknown",       BASE_ADDR_KEY:0x42470000,END_ADDR_KEY:0x4247FFFF},
      {NAME_KEY:"EXT_DEV",       BASE_ADDR_KEY:0xC0000000,END_ADDR_KEY:0xCFFFFFFF},
      {NAME_KEY:"Non-Periph",    BASE_ADDR_KEY:0x00000000,END_ADDR_KEY:0x3FFFFFFF,EXCLUDE:True}
      ]
  },
  "ARMv7-M":{
    INCLUDE_KEY:[],
    PERIPHERAL_KEY:[
      {NAME_KEY:"PPB",          BASE_ADDR_KEY:0xE0000000,END_ADDR_KEY:0xE00FFFFF,PRIV_KEY:True}
      #{NAME_KEY:"PPB",          BASE_ADDR_KEY:0xE0000000,END_ADDR_KEY:0xE00FFFFF}
    ]
  }
}
