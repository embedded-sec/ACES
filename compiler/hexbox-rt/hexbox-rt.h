#ifndef __HEXBOX_RT__
#define __HEXBOX_RT__
#include "emulator.h"

#define NUM_DEFAULT_REGIONS 0 //Deny all to unprivileged, text, and ram
#define AVAILABLE_NUM_MPU_REGIONS 8 - NUM_DEFAULT_REGIONS
#define NUM_RESERVED_REGIONS 3  // default code, RO-Ram, stack


enum hexbox_switch_type{ENTRY, EXIT, START, ERROR};

struct hexbox_MPU_region{
  uint32_t base_addr;
  uint32_t attr;
};

struct hexbox_policy {
  uint16_t count;
  uint8_t id;
  uint8_t priv;
  struct hexbox_MPU_region regions[AVAILABLE_NUM_MPU_REGIONS];
};

struct hexbox_transition_list{
  struct hexbox_transition_list *next;
  uint32_t id;
};

struct hexbox_entry{
  uint32_t id;
  struct hexbox_policy *policy;
};

struct hexbox_metadata{
    struct hexbox_policy * return_policy;
    uint32_t count;  //Number of dest entries
    struct hexbox_entry dests[1];
};

struct exception_frame{
  uint32_t r0;
  uint32_t r1;
  uint32_t r2;
  uint32_t r3;
  uint32_t r12;
  uint32_t *lr;
  uint32_t *pc;
  uint32_t xPSR;
};

struct comp_stack_entry{
  uint32_t * ret_ptr;
  struct hexbox_policy *policy;
  uint32_t  stack_addr;
  uint32_t  stack_attr;
};


extern struct comp_stack_entry * hexbox_comp_stack_ptr AT_HEXBOX_DATA;
#endif
