#ifndef __EMULATOR_H
#define __EMULATOR_H



#include <stdint.h>

#define AT_HEXBOX_DATA __attribute__((section(".hexbox_rt_ram")))
#define AT_HEXBOX_CODE __attribute__((section(".hexbox_rt_code")))

struct reg_frame{
  uint32_t r0;
  uint32_t r1;
  uint32_t r2;
  uint32_t r3;
  uint32_t r4;
  uint32_t r5;
  uint32_t r6;
  uint32_t r7;
  uint32_t r8;
  uint32_t r9;
  uint32_t r10;
  uint32_t r11;
  uint32_t r12;
  uint32_t sp; //r13
  uint32_t lr; //r14
  uint32_t pc; //r15
  uint32_t psr;
};

struct emulator_acl_entry{
  uint32_t start_addr;
  uint32_t end_addr;
};

void AT_HEXBOX_CODE __attribute__((naked))__hexbox_emulator_isr() ;
uint8_t AT_HEXBOX_CODE emulate_store(uint32_t inst,uint32_t * Regs, uint32_t comp_id) ;

#endif
