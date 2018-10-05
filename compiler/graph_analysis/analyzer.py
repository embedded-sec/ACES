import networkx as nx
import json
import matplotlib.pyplot as plt
import pygraphviz
from networkx.drawing.nx_agraph import graphviz_layout
import networkx.algorithms.approximation as approx
import networkx.algorithms.dag as dag
import networkx.algorithms.components as comps
import ld_helpers
import devices
from  pprint import pprint
import collections

from key_defs import *

# This can be changed by commandline argument
MAX_DATA_REGIONS = 4

#Number of MPU regions reserved to set global permissions
NUM_DEFAULT_MPU_REGIONS = 4


CONTROL_EDGES = ['Callee','Indirect Call']

DATA_EDGES = [DATA_EDGE_TYPE, PERIPHERAL_EDGE_TYPE, ALIAS_EDGE_TYPE]

DEFAULT_NODE_ADDR = {'colorscheme':'set312'}

NODE_TYPE_ATTRS = {FUNCTION_TYPE:{},
                   "Indirect":{'shape':'diamond','color':'blue'},
                   GLOBAL_TYPE:{'shape':'box','color':'magenta'},
                   PERIPHERAL_NODE_TYPE:{'shape':'hexagon','color':'orange'},
                   }

EDGE_TYPE_ATTRS = {"Caller":{},
                   "Callee":{},
                   "Indirect Call":{'style':'dotted'},
                   "Data":{'color':'magenta'},
                   "Alias":{},
                   PERIPHERAL_EDGE_TYPE:{'color':'orange'},
                   }
'''
EDGE_TYPE_LUT = {'Callee':'control','Globals':'data','Asm_Calls':'control',
                 'Unknown':'unknown', 'Indirects':'indirect','Filename':'filename'}
NODE_TYPE_LUT = {'Function':('function','ellipse',[]),
                 'Asm_Calls':('asm_call','ellipse',[]),
                 'Globals':('data','box',['Filename']),
                 'Unknown':('unknown','pentagon',[]),
                 'Indirects':('indirect','diamond',['MayCall']),
                 'Filename':('filename','hexagon',[])}
'''

SYSCALL_COMP_REQUIREMENTS = {"_sbrk": ["malloc", "_sbrk_r"]}


def lowest_cost_data_merge(R,c_region):
    data_regions = nx.get_node_attributes(R,DATA_REGION_KEY).keys()
    preds = []
    for p in R.predecessors(c_region):
        if p in data_regions:
            preds.append(p)

    min_cost = (None,None,None)
    for i in range(len(preds)):
        src = preds[i]
        code_regions = set(R.successors(src))
        for j in range(i+1,len(preds)):
            dest = preds[j]
            code_regions.update(R.successors(dest))
            if min_cost[2] == None:
                min_cost = (src,dest,len(code_regions)-1)
            elif min_cost[2] > len(code_regions):
                min_cost = (src,dest,len(code_regions)-1)

            if min_cost[2] == 0:
                print "Data min_cost", min_cost
                return min_cost

    print "Data min_cost", min_cost
    return min_cost


def look_up_mpu_peripheral(R,T,n):
    return R.node[n][KEY_MPU_TREE_NAME]

def lowest_cost_peripheral_merge(R,T,c_region):
    peripheral_regions =[]
    for p in R.predecessors(c_region):
        if R.node[p][TYPE_KEY] == PERIPHERAL_REGION_KEY:
            peripheral_regions.append(p)

    required_pers = set()
    for p in peripheral_regions:
        required_pers.update(R.node[p][KEY_REQUIRED_PERIPHERALS])

    min_cost = (None,None,None)
    for i in range(len(peripheral_regions)):
        src = peripheral_regions[i]
        mpu_tree_src = look_up_mpu_peripheral(R,T,src)
        for j in range(i+1,len(peripheral_regions)):
            dest = peripheral_regions[j]
            mpu_tree_dest = look_up_mpu_peripheral(R,T,dest)
            if mpu_tree_src == None or mpu_tree_dest == None:
                continue

            covered_peripherals = devices.get_covered_peripherals(T,mpu_tree_src,mpu_tree_dest)
            
            if covered_peripherals == None:
                cost = None
            else:
                cost = len(covered_peripherals.difference(required_pers))

            if cost == None:
                pass
            elif min_cost[2] == None:
                min_cost = (src,dest,cost)
            elif min_cost[2] > cost:
                min_cost = (src,dest,cost)

            if min_cost[2] == 0:
                return min_cost
    return min_cost


def move_to_same_comp(R, functs):
    '''
        TODO:  Rename this function, hacked to force the keys in functs to be
        in and their list in default compartment
        Ensures all functions in functs are in the same compartment as their
        key.
        Inputs:
            R - Region graph
            functs - dictionary of lists, with key being function name and list
                     of functions that should be placed in same compartment as
                     the key
        TODO: Extend to use PDG, to update dependencies, for now assumes
              funct_lists are library functions and thus we don't know their
              dependencies
    '''

    code_regions = nx.get_node_attributes(R, CODE_REGION_KEY)

    for key, funct_list in functs.items():
        for n, attr in R.nodes(True):
            if CODE_REGION_KEY in attr:
                for f in funct_list:
                    if f in attr[OBJECTS_KEY]:
                        attr[OBJECTS_KEY].remove(f)

                if key in attr[OBJECTS_KEY]:
                    attr[OBJECTS_KEY].remove(key)


def make_implementable(R, T):
    '''
    Lowers the region graph to number of available MPU regions
        R: A region graph
        T: Device Tree describing MPU regions for peripherals
        This makes the the graph implementable by reducing the number of data
        and peripheral dependancies to below the available mpu threashold.
    '''
    remove_all_non_region_nodes(R)
    move_to_same_comp(R, SYSCALL_COMP_REQUIREMENTS)

    #code_regions = nx.get_node_attributes(R,CODE_REGION_KEY)

    for c_region,attrs in R.nodes(True):
        changed = True
        if attrs[TYPE_KEY] != CODE_REGION_KEY:
            continue
        
        while len(R.predecessors(c_region)) > MAX_DATA_REGIONS and changed:
            changed = False
            
            (d1, d2,d_cost) = lowest_cost_data_merge(R, c_region)
            (p1, p2, p_cost) = lowest_cost_peripheral_merge(R,T,c_region)
            if p_cost == None and d_cost == None:
                changed = False
            elif p_cost == None and d_cost!=None:
                R, changed = merge_data_region(R,d1,d2)
            elif p_cost != None and d_cost == None:
                changed = merge_peripheral_regions(R,T,c_region,p1,p2)
            else:
                if d_cost < p_cost:
                    R, changed = merge_data_region(R,d1,d2)
                    #R, changed = merge_regions(R,d1,d2)
                else:
                    changed = merge_peripheral_regions(R,T,c_region,p1,p2)

            if not changed:
                print "Unable to make implementable", c_region, R.predecessors(c_region)
                return R,False
    return R,True


def merge_data_region(R,d1,d2):
    changed = True
    d1_objs = R.node[d1][OBJECTS_KEY]
    d1_objs.extend(R.node[d2][OBJECTS_KEY])
    R = nx.contracted_nodes(R,d1,d2)
    return R, changed


def merge_regions(R,d1,d2):
    '''
        Merges Code or Data regions
    '''
    if R.node[d1][TYPE_KEY] != R.node[d2][TYPE_KEY]:
        raise TypeError("Trying to merge nodes of different types")

    if R.node[d1][TYPE_KEY] == PERIPHERAL_REGION_KEY:
        raise TypeError("Cannot merge peripherals with this method")

    changed = True
    d1_objs = R.node[d1][OBJECTS_KEY]
    d1_objs.extend(R.node[d2][OBJECTS_KEY])
    contract_nodes_no_copy(R,d1,d2)
    return R, changed


def remove_all_non_region_nodes(R):
    '''
       This should be run after all desired nodes have been mapped to a region
       any unmapped Functions, or Globals will be put in the default always
       accessible regions.  Any unmapped peripherals will be inaccessable
    '''
    count =0
    for node,attrs in R.nodes(True):
        if (not attrs.has_key(TYPE_KEY)) or \
          (not attrs[TYPE_KEY] in [CODE_REGION_KEY,DATA_REGION_KEY,PERIPHERAL_REGION_KEY]):
            count +=1
            if attrs[TYPE_KEY] == PERIPHERAL_REGION_KEY:
                print "WARNING: Removing %s not added a region attrs:" % (node), attrs
            R.remove_node(node)
    code_nodes = nx.get_node_attributes(R,CODE_REGION_KEY).keys()

    #Remove control edges
    for c_node in code_nodes:
        for s in R.successors(c_node):
            R.remove_edge(c_node,s)

    return count


def merge_peripheral_regions(R,T,code_region,per1,per2):
    '''
    Merges peripheral by finding the parent node on the path between the
    nodes
    '''
    #print "Merging P:",per1,":",per2
    p1 = look_up_mpu_peripheral(R,T,per1)
    p2 = look_up_mpu_peripheral(R,T,per2)

    merged = False
    mpu_parent = devices.get_nearest_common_ancestor(T,p1,p2)

    if mpu_parent:
        merged = True
        required_pers = set()
        required_pers.update(R.node[per1][KEY_REQUIRED_PERIPHERALS])
        required_pers.update(R.node[per2][KEY_REQUIRED_PERIPHERALS])
        new_mpu_region,new_attrs = get_mpu_region(T,mpu_parent,code_region,required_pers)
        R.add_node(new_mpu_region,new_attrs)
        remove_covered_peripherals(R,T,code_region,new_mpu_region)

    return merged


def remove_covered_peripherals(R,T,code_region,mpu_region):
    '''
        Removes nodes in R, that are under the added mpu region
        This happens when merging two peripherals in the device tree captures
        other peripherals that the code_region also depends on.
    '''
    mpu_tree_name = R.node[mpu_region][KEY_MPU_TREE_NAME]
    mpu_attrs = R.node[mpu_region]
    #covered_pers = devices.get_covered_peripherals(T,mpu_tree_name)
    for region in R.predecessors(code_region):
        r_attrs = R.node[region]
        if r_attrs[TYPE_KEY] == PERIPHERAL_REGION_KEY:
            other_mpu_region_t_name = r_attrs[KEY_MPU_TREE_NAME]
            if devices.is_child(T,mpu_tree_name, other_mpu_region_t_name):
                mpu_attrs[KEY_REQUIRED_PERIPHERALS].update(r_attrs[KEY_REQUIRED_PERIPHERALS])
                R.add_node(mpu_region, mpu_attrs)
                R.add_edge(mpu_region, code_region)
                R.remove_node(region)


def merge_on_attr(G,attr=REGION_KEY):
    '''
    Merges all nodes that share the same attribute
    '''

    node_to_attr = nx.get_node_attributes(G,attr)
    attr_to_nodelist = {}  # {attr:[nodes,...]}
    for n, attr in node_to_attr.items():
        if not attr_to_nodelist.has_key(attr):
            attr_to_nodelist[attr] = []
        attr_to_nodelist[attr].append(n)

    M = G.copy()
    for attr,node_list in attr_to_nodelist.items():
        root_node =node_list[0]
        for n in node_list[1:]:
            M = nx.contracted_nodes(M,root_node,n,False)
    return M


def get_mpu_config(compartments):
    mpu_config = {}
    for key in compartments.keys():
        attrs = [100794405,319160355,100794387,0]+[0]*MAX_DATA_REGIONS
        addrs = [134217744,536870929,134742034,0]+[0]*MAX_DATA_REGIONS
        mpu_config[key]={"Attrs":attrs,"Addrs":addrs}
    return mpu_config


def get_compartment_description(R):
    '''
        This gets the compartment description which is given to 
        LLVM to apply during compilation
        Input:
            R(region graph): 
        Returns:
            description(dict):  A dictionary that is dumped to a
                                json file that describes the compartments
                                to be made by the compiler
    '''
    #code_regions = nx.get_node_attributes(R,CODE_REGION_KEY)
    #data_regions = nx.get_node_attributes(R,DATA_REGION_KEY)

    description = {POLICY_KEY_REGIONS:{},
              POLICY_KEY_COMPARTMENTS:{},
              POLICY_KEY_MPU_CONFIG:{},
              POLICY_NUM_MPU_REGIONS:NUM_DEFAULT_MPU_REGIONS + MAX_DATA_REGIONS}

    for node,attrs in R.nodes(True):
        if attrs[TYPE_KEY] in [CODE_REGION_KEY,DATA_REGION_KEY]:
            add_region_to_comp_desc(R,node,description)
        if attrs[TYPE_KEY] == CODE_REGION_KEY:
            add_compartment_to_comp_desc(R,node,description)

    mpu_config = get_mpu_config(description[POLICY_KEY_COMPARTMENTS])
    add_default_mpu_config(mpu_config)
    description[POLICY_KEY_MPU_CONFIG] = mpu_config

    return description


def add_default_mpu_config(mpu_config):
    '''
        Default MPU configuration, mostly place holders as
    '''
    default_conf ={
      "Attrs":[100794405,319160355,319094807,319094807].extend([0] * MAX_DATA_REGIONS),
      "Addrs":[134217744,536870929,3758153746,3758153747].extend([0] * MAX_DATA_REGIONS)
    }
    mpu_config["__hexbox_default"] = default_conf


def add_region_to_comp_desc(R,r_node,comp_desc):
    r_node_to_comp_lut = {CODE_REGION_KEY:"Code",DATA_REGION_KEY:"Data","Size":0,"Align":1}
    r_type =R.node[r_node][TYPE_KEY]
    policy_r_type = r_node_to_comp_lut[r_type]
    region = {POLICY_REGION_KEY_OBJECTS: R.node[r_node][OBJECTS_KEY],
              POLICY_REGION_KEY_TYPE: policy_r_type,
              "Size":0,
              "Align":1}
    comp_desc[POLICY_KEY_REGIONS][r_node]=region


def add_compartment_to_comp_desc(R,code_region,comp_desc):
    peripheral_regions = set()
    data_regions = set()
    for p in R.predecessors(code_region):
        if R.node[p][TYPE_KEY] == DATA_REGION_KEY:
            data_regions.add(p)
        elif R.node[p][TYPE_KEY] == PERIPHERAL_REGION_KEY:
            per = ( R.node[p][BASE_ADDR_KEY],
                    R.node[p][PWR2_SIZE_KEY],
                    R.node[p][PRIV_KEY])
            peripheral_regions.add(per)
    pers_dicts =[]
    priv = False
    for per in peripheral_regions:
        pers_dicts.append({"Addr":per[0],"Size":per[1]})
        priv |= per[2]
    compartment = {"Data":list(data_regions),"Peripherals":pers_dicts,"Priv":priv}
    comp_desc[POLICY_KEY_COMPARTMENTS][code_region] = compartment


def add_region_node(R,name,r_type,r_id=0,objects=None,attrs=None,merge=None,name_attr=None):
    if not hasattr(objects,'__iter__'):
        #objects = [objects]
        pass
    region_attrs = {r_type:r_id, TYPE_KEY:r_type}
    if name_attr:
        region_attrs[NAME_KEY]=name_attr
    if objects:
        region_attrs[OBJECTS_KEY]=objects
    if attrs:
        region_attrs[ATTR_KEY]=attrs
    if merge:
        region_attrs[MERGE_KEY]=merge
    R.add_node(name,region_attrs)


def make_peripheral_regions(R,T):
    '''
        R : Region Graph
        T : Peripheral Tree, maps peripherals to mpu regions
        Converts all peripherals to mpu_regions on the peripheral tree,
        each peripheral is mapped to a unique mpu_region per code region.
        IE mpu_region is not shared between code regions
    '''
    for node, attrs in R.nodes(True):
        if attrs[TYPE_KEY] == PERIPHERAL_NODE_TYPE:
            periph = node
            for code_region in R.successors(periph):
                r_type = PERIPHERAL_REGION_KEY
                per_tree_name = attrs[NAME_KEY]
                mpu_tree_name = T.predecessors(per_tree_name)[0]
                mpu_name,mpu_attrs = get_mpu_region(T,mpu_tree_name,
                                                    code_region,[per_tree_name])
                R.add_node(mpu_name,mpu_attrs)
                R.add_edge(mpu_name,code_region)
            R.remove_node(periph)


def get_mpu_region(T,tree_node,code_region,required_pers):

    mpu_attrs = T.node[tree_node]
    if not mpu_attrs.has_key(KEY_REQUIRED_PERIPHERALS):
        mpu_attrs[KEY_REQUIRED_PERIPHERALS] = set()
    mpu_attrs[KEY_REQUIRED_PERIPHERALS].update(required_pers)
    mpu_attrs[KEY_MPU_TREE_NAME] = tree_node
    mpu_name = tree_node+"_"+code_region
    return mpu_name, mpu_attrs


def optimize_filename_groupings(G,filename_to_code_nodes):
    '''
        Inputs:
            move -  boolean to determine if relocations actually happen
    '''
    node_to_filenames = nx.get_node_attributes(G,FILENAME_TYPE)
    for n,attrs in G.nodes(True):
        if attrs[TYPE_KEY] != FUNCTION_TYPE or \
            not node_to_filenames.has_key(n):
            continue
        filename = node_to_filenames[n]
        new_filename = filename
        max_connect = 0
        neighbors = set(nx.all_neighbors(G,n))
        for fname, comp in filename_to_code_nodes.items():
            comp_set = set(comp)
            con = len(neighbors.intersection(comp_set))
            if (con > max_connect):
                new_filename = fname
        filename_to_code_nodes[filename].remove(n)
        filename_to_code_nodes[new_filename].append(n)
        if len(filename_to_code_nodes[filename]) == 0:
            filename_to_code_nodes.pop(filename,None)


def get_peripheral_nodes(G):
    p = filter(lambda (n, d): d['Type'] == PERIPHERAL_NODE_TYPE, G.nodes(data=True))
    return p


def make_region_graph(G,T):
    R = G.copy()
    make_peripheral_regions(R,T)
    contract_nodes =[]
    type2count = collections.defaultdict(int)
    for n, attrs in G.nodes(True):
        ty = attrs[TYPE_KEY]
        if ty == FUNCTION_TYPE:
            reg_id = type2count[CODE_REGION_KEY]
            type2count[CODE_REGION_KEY] += 1
            reg_name = CODE_REGION_KEY +'%i_' % reg_id
            reg_ty = CODE_REGION_KEY
            add_region_node(R,reg_name,reg_ty,reg_id,[n])
            contract_nodes.append( (reg_name, n) )
        elif ty == GLOBAL_TYPE:
            reg_ty = DATA_REGION_KEY
            reg_id = type2count[DATA_REGION_KEY]
            type2count[DATA_REGION_KEY] += 1
            reg_name = DATA_REGION_KEY +'%i_' % reg_id
            add_region_node(R,reg_name,reg_ty,reg_id,[n])
            contract_nodes.append( (reg_name,n) )
    for (u,v) in contract_nodes:
        contract_nodes_no_copy(R,u,v)
    return R


def partition_by_peripheral(G,T):
    '''
        Forms initial set of compartments by peripheral.
    '''
    R = make_region_graph(G,T)
    print "Partitioning by Peripheral"
    worklist = collections.deque()
    for n, attrs in R.nodes(True):
        print n, attrs
        if attrs[TYPE_KEY]  == PERIPHERAL_REGION_KEY:
            print "Found Peripheral"
            for p in R.successors(n):
                if not p in worklist:
                    print "Adding Predecessor"
                    worklist.append(p)

    # Add all neighboring code regions that are only adjacent to only a
    # single region dependent on a peripheral region
    updated = True
    round_num = 0
    while updated:
        updated = False
        print "Round Number", round_num
        round_num += 1
        potential_merges = collections.defaultdict(set)
        for code_region in worklist:

            dep_per = get_dependent_peripherals(R, code_region)
            all_neighbors = R.predecessors(code_region)
            all_neighbors.extend(R.successors(code_region))
            for n in all_neighbors:
                if n == code_region:
                    continue
                if R.node[n][TYPE_KEY] == CODE_REGION_KEY:
                    n_dep_per = get_dependent_peripherals(R, n)
                    if dep_per == n_dep_per or len(n_dep_per)== 0:
                        print 'Potential Merges: ', code_region, " ", n
                        potential_merges[n].add(code_region)

        # Merge code regions which only have one potential merge code region
        worklist = collections.deque()
        for key, merges in potential_merges.items():
            if len(merges) == 1:
                updated = True
                region = merges.pop()
                if key in R.nodes() and region in R.nodes():
                    merge_regions(R, region, key)
                    worklist.append(region)
                    if key in worklist:
                        worklist.remove(key)

    nx.drawing.nx_pydot.write_dot(R,"by_peripheral_before-final.dot")
    # Merge all areas not dependent on a peripheral
    no_peripheral_regions = []
    for n, attrs in R.nodes(True):
        if attrs[TYPE_KEY] == CODE_REGION_KEY:
            has_peripheral = False
            for s in R.predecessors(n):
                if R.node[s][TYPE_KEY] == PERIPHERAL_REGION_KEY:
                    has_peripheral = True
                    break;
            if not has_peripheral:
                no_peripheral_regions.append(n)
    if len(no_peripheral_regions) > 1:
        code_region = no_peripheral_regions[0]
        for n in no_peripheral_regions[1:]:
            merge_regions(R,code_region,n)

    nx.drawing.nx_pydot.write_dot(R,"by_peripheral_before_lowering.dot")
    R, is_implementable = make_implementable(R,T)
    nx.drawing.nx_pydot.write_dot(R,"by_peripheral_merged.dot")
    if is_implementable:
        return get_compartment_description(R)
    else:
        print "Cannot implement when grouping by peripheral"
        quit(-1)


def get_dependent_peripherals(R, n):
    peripherals = set()
    for s in R.predecessors(n):
        if R.node[s][TYPE_KEY] == PERIPHERAL_REGION_KEY:
            peripherals.update( R.node[s][KEY_REQUIRED_PERIPHERALS])
    return peripherals



def partition_by_filename_no_optimization(G,T):
    return partition_by_filename(G,T,False)

def partition_by_filename(G,T,opt=True):
    '''
        Puts all functions from same file in the same region
        Inputs:
            G(PDG):  The program dependency graph
            T(nx.Digraph):  The device description of peripherals as Tree
            opt(bool):      Apply optimizations if True
        Returns:
            (dict):     A compartment description that is given to LLVM
                        as a json file
    '''

    filename_to_code_nodes = collections.defaultdict(list)
    filename_to_data_nodes = collections.defaultdict(list)

    print "Merging By filename, Opt: ", opt
    Region_Graph = G.copy()
    for (node,attrs) in Region_Graph.nodes(True):
        if attrs.has_key(FILENAME_TYPE):
            filename = attrs[FILENAME_TYPE]
            if attrs[TYPE_KEY] == FUNCTION_TYPE:
                filename_to_code_nodes[filename].append(node)
            elif attrs[TYPE_KEY] == GLOBAL_TYPE:
                filename_to_data_nodes[filename].append(node)

    if opt:
        optimize_filename_groupings(G,filename_to_code_nodes)

    make_peripheral_regions(Region_Graph,T)
    Region_Graph = build_regions_from_dict(Region_Graph,filename_to_code_nodes,CODE_REGION_KEY)
    Region_Graph = build_regions_from_dict(Region_Graph,filename_to_data_nodes,DATA_REGION_KEY)

    Region_Graph, is_implementable = make_implementable(Region_Graph,T)
    nx.drawing.nx_pydot.write_dot(Region_Graph,"by_filename_code_merged.dot")
    if is_implementable:
        return get_compartment_description(Region_Graph)
    else:
        print "Cannot implement when grouping by filename"
        quit(-1)


def contract_nodes_no_copy(G,keep_node,node):
    '''
    same as nx.contract_nodes except doesn't copy the graph instead modifies.
    It contracts the nodes, by moving all edges
    of node, to keep_node, and then removing node

    '''
    for p in G.predecessors(node):
        G.add_edge(p,keep_node)
    for s in G.successors(node):
        G.add_edge(keep_node,s)
    G.remove_node(node)


def build_regions_from_dict(R,region_dict,r_type,r_id=0):
    for key, nodes in region_dict.items():
        region_name = r_type + str(r_id)+"_" 
        r_id += 1
        add_region_node(R,region_name,r_type,r_id,nodes,merge=key)
        for node in nodes:
            contract_nodes_no_copy(R,region_name,node)
            if R.has_node(node):
                R.remove_node(node)
                print "Removed: ", node
    return R


def add_nodes(G,json_data,node_types):
    for node_name,node in json_data.items():
        if node_name.startswith("llvm"):
            continue
        node_ty = node["Attr"]["Type"]
        if not node_ty in node_types:
            continue
        attrs = {}
        #print node_name
        attrs.update(node["Attr"])
        attrs.update(NODE_TYPE_ATTRS[node_ty])
        G.add_node(node_name,attrs)


def make_isr_comp(G):
    irq_region_name = IRQ_REGION_NAME
    irq_list = []
    for node, attrs in G.nodes(True):
        if attrs[TYPE_KEY] == FUNCTION_TYPE and node in devices.INTERRUPT_HANDLERS:
            irq_list.append(node)
    irq_attrs = {TYPE_KEY:CODE_REGION_KEY, OBJECTS_KEY:irq_list}
    G.add_node(irq_region_name,irq_attrs)
    for n in irq_list:
        contract_nodes_no_copy(G,irq_region_name,n)


def add_edges(G,json_data,edge_types):
    '''
        Reads in edges from json data to PDG
        Inputs:
            G(nx.DiGraph):  PDG graph
            json_data(dict):      Dependencies found from LLVM analysis
            edge_type(list):    List of edge types to add to PDG
    '''
    for node_name,node in json_data.items():
        if node_name.startswith("llvm"):
            continue
        if not node.has_key("Connections"):
            continue
        if not G.has_node(node_name):
            continue
        #print node_name
        for dest_name, con_info in node["Connections"].items():
            if not G.has_node(dest_name):
                continue
            if dest_name.startswith("llvm"):
                continue
            con_ty = con_info[TYPE_KEY]
            if not con_ty in edge_types:
                continue
            attr_dict = {}
            attr_dict.update(con_info)
            attr_dict.update(EDGE_TYPE_ATTRS[con_ty])
            G.add_edge(node_name, dest_name, attr_dict=attr_dict)


def add_size_info(G,json_size_file):
    with open(json_size_file) as infile:
        data = json.load(infile)
        properties = {}
        for node_name,props in data.items():
            for key,value in props.items():
                if not properties.has_key(key):
                    properties[key] = {}
                properties[key][node_name] = value
        for p, nodes in properties.items():
            nx.set_node_attributes(G,p,nodes)


def remap_peripherals(G, device_desc):
    '''
      G: Dependancy Graph
      Device_desc: Description of peripherals on devices

      Takes constant address access output by compiler which is a heuristic of
      the peripherals accessed and identifies smallest MPU region that will 
      cover it from device description
    '''
    remove_nodes = []
    successors = {}
    predecessors = {}
    for (n, attrs) in G.nodes(True):
        if attrs[TYPE_KEY] == PERIPHERAL_NODE_TYPE:
            base_addr = attrs["Addr"]
            if base_addr == 0xFFFFFFFF:
                remove_nodes.append(n)
                continue
            size = attrs["DataSize"]
            new_node = devices.get_peripheral_dict(device_desc, base_addr, size)

            if new_node:
                node_name = ".periph."+new_node[NAME_KEY]
                #print "Adding Pnode", node_name, new_node
                G.add_node(node_name,new_node)
                if not successors.has_key(node_name):
                    successors[node_name]=[]
                if not predecessors.has_key(node_name):
                    predecessors[node_name]=[]
                successors[node_name].extend(G.successors(n))
                predecessors[node_name].extend(G.predecessors(n))
                remove_nodes.append(n)
            else:
                print "Failed to Remap", n, ": ", attrs

    G.remove_nodes_from(remove_nodes)
    for node, successor_list in successors.items():
        for successor in successor_list:
            G.add_edge(node, successor)

    for node, predecessor_list in predecessors.items():
        for predecessor in predecessor_list:
            G.add_edge(predecessor, node)


def build_graph(dependancy_json):
    '''
        Reads in the program dependancy graph from json file produced by the analysis
        pass of the compiler.  Then builds a networkx graph of Globals and
        functions
    '''
    with open(dependancy_json, 'rb') as infile:
        json_data = json.load(infile)
    PDG = nx.DiGraph()
    add_nodes(PDG,json_data,['Function','Global', PERIPHERAL_NODE_TYPE])
    add_edges(PDG,json_data,['Callee','Indirect Call','Data','Alias',PERIPHERAL_EDGE_TYPE])
    return PDG


if __name__ == '__main__':
    PARTITION_METHODS = {"filename":partition_by_filename,
                         'peripheral':partition_by_peripheral,
                         "filename-no-opt":partition_by_filename_no_optimization}
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-j','--json_graph',dest='json_graph',required=True,
                    help='Json file describing the Nodes of a graph from llvm')
    parser.add_argument('-s','--size',dest='size_file', help='JSON Size File')
    parser.add_argument('-o','--output',dest='outfile',
                        help='JSON file with layout of program, and\
                        allowed transitions of the program')
    parser.add_argument('-T','--linker_template',dest='linker_template',
                        help='Template Linker File')
    parser.add_argument('-L','--linker_output',dest='linker_output',
                        help='Output Linker Script, required with -T')
    parser.add_argument('-m','--method',dest='partion_method',
                        help=('Method for partitionin, valid options: '+str(PARTITION_METHODS.keys()))
                        )
    parser.add_argument('-b','--board',dest='board',
                        help=('Target Board, valid options: '+str(devices.DEVICE_DEFS.keys())),
                        required = True
                        )
    parser.add_argument('-n','--num_mpu_regions',dest='num_mpu_regions',
                        help=('Number of MPU regions on target'),
                        default=8, type=int
                        )

    args = parser.parse_args()
    global MAX_DATA_REGIONS
    MAX_DATA_REGIONS = args.num_mpu_regions - NUM_DEFAULT_MPU_REGIONS

    if args.partion_method and not args.outfile:
        print "-o, --outfile: Required with -m(--method)"
        quit(-1)

    PDG = build_graph(args.json_graph)
    device_desc,T = devices.get_device_desc(args.board)

    if args.outfile and args.partion_method:
        #nx.drawing.nx_pydot.write_dot(PDG,"all_nodes.dot")
        make_isr_comp(PDG)
        remap_peripherals(PDG, device_desc)
        comp_def = PARTITION_METHODS[args.partion_method](PDG,T)

        with open(args.outfile,'wb') as outfile:
            json.dump(comp_def, outfile, sort_keys=True,
                      indent=4, separators=(',', ': '))

        if args.linker_template and args.linker_output:
            ld_helpers.make_linker_script(args.linker_template,
                                          args.linker_output,
                                          comp_def)
