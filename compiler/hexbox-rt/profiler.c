#include "profiler.h"
#include "emulator.h"


#define PROFILER_FAULT while(1){}


// Address for buffer to store compartment switch addresses
#define COMP_EMULATOR_RECORD_ADDR 0x10000000
#define COMP_EMULATOR_RECORD_SIZE 1024
#define RECORD_SIZE 4
// Address for buffer to store pc of compartments switch
#define COMP_SWITCH_ADDRS 0x1000E000
// Just stores a list of address without regard to compartment
#define EMULATOR_RAW_ADDRS 0x1000F000
#define SIZE_RECORD_MEMORY 0x10000 // 64KB
// Macros auto set by adjusting above definitions
#define COMP_EMULATOR_END_ADDR  COMP_SWITCH_ADDRS
#define COMP_SWITCH_BUF_SIZE (EMULATOR_RAW_ADDRS - COMP_SWITCH_ADDRS)
#define EMULATOR_RAW_BUF_SIZE ((COMP_EMULATOR_RECORD_ADDR + SIZE_RECORD_MEMORY) - EMULATOR_RAW_ADDRS)


uint32_t * AT_HEXBOX_CODE __profiler_get_compartment_buffer(uint32_t id){
  uint32_t * addr = (uint32_t *)COMP_EMULATOR_RECORD_ADDR;
  addr += ( id * (COMP_EMULATOR_RECORD_SIZE) / RECORD_SIZE);
  if (addr < (uint32_t *) COMP_EMULATOR_RECORD_ADDR  || \
      addr >= (uint32_t *) COMP_EMULATOR_END_ADDR){
    PROFILER_FAULT  //Not enough space to record accesses
  }
  return addr;
}


void __profiler_record_emulator_compartment_access(uint32_t id, uint32_t addr){
  /*  NOTE  If need more space for application in future, array of lists,
    first item in list is compartment id, if it match search every element
    in list, if not skip to next lists

    struct emulator_record_list {
        uint32_t comp_policy_addr
        struct emulator_acl_entry[128]
    }
    struct emulator_record_list *emulator_records[NUMBER_WILL_FIT];
  */
  uint32_t * buffer =  __profiler_get_compartment_buffer(id);
  uint32_t i;

  buffer[0] = (uint32_t)(hexbox_comp_stack_ptr->policy);
  struct emulator_acl_entry *entry = (struct emulator_acl_entry *) &buffer[1];
  //for(i = 1; i+1<COMP_EMULATOR_RECORD_SIZE / sizeof(uint32_t); i += 2){
  for(i = 0; &(entry[i].end_addr) < buffer + (COMP_EMULATOR_RECORD_SIZE / sizeof(buffer)); ++i){
    if (entry[i].start_addr == 0){
      entry[i].start_addr = addr;
      entry[i].end_addr = addr + 4;
      return;
    }else if (addr >= (entry[i].start_addr - 4) && addr <= entry[i].end_addr){
        if (addr == (entry[i].start_addr - 4)){
          entry[i].start_addr = addr;
        }else if (entry[i].end_addr == addr){
          entry[i].end_addr = addr + 4;
        }
        return;
    }


  }
  PROFILER_FAULT  //Not enough space to record accesses
}


void __profiler_record_emulator_addr(uint32_t addr){
  //  TODO Change to  use red-black tree allocated in an array
  //  A large amount of time is used just searching through the array
  uint32_t i;
  struct profiler_addr_record* buf =  (struct profiler_addr_record*)EMULATOR_RAW_ADDRS;

  for (i = 0; i < EMULATOR_RAW_BUF_SIZE / sizeof(struct profiler_addr_record); i++){
    if (buf[i].addr == 0){
      //buf[i].pc = pc;
      buf[i].addr = addr;
      ++buf[i].count;
      return;
    }
    else if (buf[i].addr ==  addr){
      ++buf[i].count;
      return;
    }
  }
  PROFILER_FAULT  //Not enough space to record accesses
}


void __profiler_clear_record_buffer(){
  uint32_t i =0;
  uint32_t * buffer = (uint32_t * )COMP_EMULATOR_RECORD_ADDR;
  for (i=0 ; i<(SIZE_RECORD_MEMORY)/sizeof(uint32_t) ;i++){
    buffer[i] = 0;
  }
}


void __profiler_count_comp_addr(uint32_t pc){
  //  TODO Change to  use red-black tree allocated in an array
  //  A large amount of time is used just searching through the array
  uint32_t i;
  struct profiler_pc_record* buf = (struct profiler_pc_record*)COMP_SWITCH_BUF_SIZE;

  for (i = 0; i < COMP_SWITCH_BUF_SIZE / sizeof(struct profiler_pc_record); ++i){
    if (buf[i].pc == pc || buf[i].pc ==  0){
      buf[i].pc = pc;
      buf[i].count++;
      break;
    }
  }
}
