#ifndef __PROFILER__
#define __PROFILER__
#include "emulator.h"
#include "hexbox-rt.h"



struct profiler_pc_record{
  uint32_t pc;
  uint32_t count;
};


struct profiler_addr_record{
  uint32_t addr;
  uint32_t count;
};


void AT_HEXBOX_CODE __profiler_record_emulator_addr(uint32_t addr);
void AT_HEXBOX_CODE __profiler_record_emulator_compartment_access(uint32_t id, uint32_t addr);
void AT_HEXBOX_CODE __profiler_count_comp_addr(uint32_t pc);
void AT_HEXBOX_CODE __profiler_clear_record_buffer();



#endif
