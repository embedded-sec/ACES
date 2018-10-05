#include <stdint.h>
#include <stddef.h>
#include "hexbox-rt.h"
#include "emulator.h"
#ifndef ENFORCE
#include "profiler.h"
#endif


#define AT_HEXBOX_DATA __attribute__((section(".hexbox_rt_ram")))
#define AT_HEXBOX_CODE __attribute__((section(".hexbox_rt_code")))

//TODO: CLEAN up old definitions, start with __hexbox...


#define MPU_CONFIG_REG     *((volatile uint32_t *) 0xE000ED94)
#define MPU_REGION_NUM_REG *((volatile uint32_t *) 0xE000ED98)
#define MPU_REGION_ADDR_REG *((volatile uint32_t *) 0xE000ED9C)
#define MPU_REGION_ATTR_REG *((volatile uint32_t *) 0xE000EDA0)

#define MMAR *((volatile uint32_t *) 0xE000ED34)
#define CFSR *((volatile uint32_t *) 0xE000ED28)
#define DEMCR *((volatile uint32_t *) 0xE000EDFC)
#define SCB_SHCSR_MEMFAULTENA_Pos          16U
#define SCB_SHCSR_MEMFAULTENA_Msk          (1UL << SCB_SHCSR_MEMFAULTENA_Pos)
#define SHCSR *((volatile uint32_t *)0xE000ED24)
#define SHPR2 *((volatile uint32_t *)0xE000ED1C)

#define EXCEPTION_STACK_NUM_WORDS 8

#define HEXBOX_INVALID_TRANS_PTR 20
#define COMP_STACK_SIZE 16
#define STACK_FULL 21
#define INVALID_RETURN 22

#define MPU_DISABLE_CONSTANT 0
#define MPU_STACK_REGION_NUM 2

#define HEXBOX_FAULT while(1){}
#define MOD_PRIVILEGES

#ifdef MOD_PRIVILEGES
  #define DROP_PRIVILEGES __asm("msr CONTROL, %[reg] " : :[reg]"r"(1):"memory")
  #define SET_PRIVILEGES __asm("msr CONTROL, %[reg] " : :[reg]"r"(0):"memory")
#else
  #define DROP_PRIVILEGES
  #define SET_PRIVILEGES
#endif


struct comp_stack_entry hexbox_comp_stack[COMP_STACK_SIZE] AT_HEXBOX_DATA;
struct comp_stack_entry * hexbox_comp_stack_ptr AT_HEXBOX_DATA;

//struct comp_stack_entry * hexbox_current_comp;


struct hexbox_policy* AT_HEXBOX_CODE __hexbox_get_policy(struct hexbox_metadata * md, uint32_t dest) ;
void AT_HEXBOX_CODE __hexbox_apply_policy(struct hexbox_policy * policy);
void AT_HEXBOX_CODE __hexbox_stack_push_and_apply(uint32_t * ret_ptr,struct hexbox_policy * p,uint32_t sp);
void AT_HEXBOX_CODE __hexbox_stack_pop_and_apply();

void AT_HEXBOX_CODE __hexbox_apply_stack_mask(struct hexbox_MPU_region* region,uint32_t sp);
void AT_HEXBOX_CODE __hexbox_mpu_set_stack(uint32_t addr,uint32_t attrs);

void AT_HEXBOX_CODE __hexbox_start_dwt_counter();
void AT_HEXBOX_CODE __hexbox_stop_dwt_counter();
void AT_HEXBOX_CODE __hexbox_reset_stats();

uint32_t AT_HEXBOX_CODE __hexbox_get_and_reset_dwt_counter(uint32_t sub_isr);


extern struct hexbox_policy* _hexbox_comp___hexbox_default;


//Can't be placed in HEXBOX DATA as needs to be initialized before any SVC's
//happen (ie needs to be in .bss) only used for profiling
uint32_t stack_initialized = 0;

uint32_t AT_HEXBOX_DATA __hexbox_entries;
uint32_t AT_HEXBOX_DATA __hexbox_exits;
uint32_t AT_HEXBOX_DATA __hexbox_entry_exe_time;
uint32_t AT_HEXBOX_DATA __hexbox_exit_exe_time;
uint32_t AT_HEXBOX_DATA __hexbox_total_exe_time;
uint32_t AT_HEXBOX_DATA __hexbox_init_exe_time;
uint32_t AT_HEXBOX_DATA __hexbox_unknown_comp_exe_time;

#define MAX_COMPS 50
uint32_t AT_HEXBOX_DATA __hexbox_comp_entries[MAX_COMPS];
uint32_t AT_HEXBOX_DATA __hexbox_comp_exits[MAX_COMPS];
uint32_t AT_HEXBOX_DATA __hexbox_comp_exe_times[MAX_COMPS];
uint32_t AT_HEXBOX_DATA __hexbox_comp_emu_calls[MAX_COMPS];
uint32_t AT_HEXBOX_DATA __hexbox_comp_emu_exe_times[MAX_COMPS];


#define MPU_ENABLE_CONSTANT 0x5  //Enable and activate default map




/*
Calculates the stack mask used to block writes to the largest portion of
the stack that can be blocked.

sp: Stack pointer at time of entry_point
region: The mpu register configuration for this region

It takes the region size and divides it into 8 sub regions,
Then looks at the most significant bits less than the region size
This determine how many sub regions should be disabled
IE if region is 2**N bits size, then look at bits N-1:N-3, this is the
number of subregions that can be disabled (D). Bits calculated by 2**D-1
*/
void __attribute__((used)) __hexbox_apply_stack_mask(struct hexbox_MPU_region* region,uint32_t sp){


  uint32_t subregions;
  uint32_t num_used;
  uint32_t region_size;
  uint32_t attrs;
  region_size = (((region->attr)>>1) & 0x1F);//Size encode in MPU i N-1
  num_used = ((sp+32) >> (region_size - 2)) & 0x7; //Region size is N-1 +32 because 32 bytes are from exception entry
  //Invert because stack grows down (Thus high address needs masked first)
  subregions = (0xFF00 >>(7-num_used)) & 0xFF;
  attrs = (region->attr & 0xFFFF00FF) | (subregions << 8);
  __hexbox_mpu_set_stack(region->base_addr,attrs);


}

void __hexbox_mpu_set_stack(uint32_t addr,uint32_t attrs){
  MPU_REGION_NUM_REG = MPU_STACK_REGION_NUM;
  MPU_REGION_ADDR_REG = addr; //sets region to write to
  MPU_REGION_ATTR_REG = attrs;

}

void __attribute__((used)) __hexbox_init_data_section(uint32_t * vma_start,\
     uint32_t* ram_start,uint32_t *ram_end )
{
  uint32_t * cur_data_ptr;
  uint32_t * cur_vma_ptr;
  cur_data_ptr = ram_start;
  cur_vma_ptr = vma_start;
  while (cur_data_ptr < ram_end){
    *cur_data_ptr = *cur_vma_ptr;
    cur_data_ptr +=1;
    cur_vma_ptr +=1;
  }
}


void __attribute__((used)) __hexbox_init_bss_section(uint32_t* ram_start,\
     uint32_t *ram_end )
{
  uint32_t * cur_bss_ptr;
  cur_bss_ptr = ram_start;
  while (cur_bss_ptr < ram_end){
    *cur_bss_ptr = 0;
    cur_bss_ptr +=1;
  }
}



#define SVC100 0xDF64
#define SVC101 0xDF65
#define SVC102 0xDF66
#define SVC0 0xDF00
#define SVCFF 0xDFFF
/* HEXBOX Runtime  ************************************************************/
enum hexbox_switch_type __attribute__((used))handle_svc(struct exception_frame *stack){ 

    enum hexbox_switch_type switch_type = ERROR;
    __asm volatile ("cpsid i" : : : "memory");
    __asm volatile ("cpsid f" : : : "memory");

    uint32_t pre_exception_sp = ((uint32_t)stack+EXCEPTION_STACK_NUM_WORDS);
    uint16_t instr = (uint16_t)(*((stack->pc)-1)>>16);

    uint32_t id;

    struct hexbox_metadata *md;
    struct hexbox_policy *p;
    // ------------------------Compartment Entry ----------------------------
    if( instr == SVC100){ //Compartment Entry
      switch_type = ENTRY;
      uint32_t *dest_addr = stack->lr;
      md = (struct hexbox_metadata *)(*stack->pc);
      p = __hexbox_get_policy(md,(uint32_t)stack->lr);
      if (p){
          __hexbox_stack_push_and_apply(stack->pc+1,p,pre_exception_sp);
      }
      stack->lr = stack->pc+1;
      stack->pc = dest_addr;
      //id = hexbox_comp_stack_ptr->policy->id;
      stack_initialized = 1;
    }
    //------------------------- Compartment Exit--------------------------
    else if(instr == SVC101){

      switch_type = EXIT;
      //id = hexbox_comp_stack_ptr->policy->id;
      //do check here
      //don't want to return to null location
      if (stack->lr == hexbox_comp_stack_ptr->ret_ptr){
        // Look up meta data from location we are returning to.
        __hexbox_stack_pop_and_apply();
      }
      stack->pc = stack->lr; //This allows ROP within a compartment.

    }
    // ------------------------------SVC to Start Timing --------------------------
    else if (instr == SVC0){
      switch_type = START;
    }
    // -----------------------------SVC to Stop Timing -----------------------------
    else if (instr == SVCFF){
      //  Execution time will already have been added to compartment that was
      //  executing so don't need to do anything here
      while(1);   /* TIMING_STOPS_HERE */
    }

    __asm volatile ("cpsie f" : : : "memory");
    __asm volatile ("cpsie i" : : : "memory");
     //LED2_OFF;
     return switch_type;
}


void __attribute__((used))__hexbox_stack_push_and_apply(uint32_t * ret_ptr,struct hexbox_policy * p, uint32_t sp){

  if (hexbox_comp_stack_ptr+1 < &hexbox_comp_stack[COMP_STACK_SIZE-1]){
    hexbox_comp_stack_ptr += 1;
    hexbox_comp_stack_ptr->ret_ptr = ret_ptr; //set return addr
    MPU_REGION_NUM_REG = MPU_STACK_REGION_NUM;
    hexbox_comp_stack_ptr->stack_addr = MPU_REGION_ADDR_REG;
    hexbox_comp_stack_ptr->stack_attr = MPU_REGION_ATTR_REG;
    hexbox_comp_stack_ptr->policy = p;
    MPU_CONFIG_REG = MPU_DISABLE_CONSTANT;
    __hexbox_apply_policy(p);

    __hexbox_apply_stack_mask(&p->regions[MPU_STACK_REGION_NUM],sp);

    __asm volatile(
     "dsb \n\t"
     "isb \n\t");
     MPU_CONFIG_REG = MPU_ENABLE_CONSTANT;

  }else{
    HEXBOX_FAULT  // Stack Full
  }
}

void __attribute__((used))__hexbox_stack_pop_and_apply(){
    if (hexbox_comp_stack_ptr-1 >= &hexbox_comp_stack[0]){
      hexbox_comp_stack_ptr -=1;
      MPU_CONFIG_REG = MPU_DISABLE_CONSTANT;
      __hexbox_apply_policy(hexbox_comp_stack_ptr->policy);
      __hexbox_mpu_set_stack(hexbox_comp_stack_ptr->stack_addr,
                             hexbox_comp_stack_ptr->stack_attr);
      //hexbox_comp_stack_ptr->ret_ptr = 0;
      __asm volatile(
       "dsb \n\t"
       "isb \n\t");
       MPU_CONFIG_REG = MPU_ENABLE_CONSTANT;
    }
    else{
      HEXBOX_FAULT  // Invalid return
    }
}


struct hexbox_policy* __attribute__((used))__hexbox_get_policy(struct hexbox_metadata * md, uint32_t dest){
  uint32_t i;
  for (i=0; i <md->count; i++ ){
    if(dest == md->dests[i].id){
      return md->dests[i].policy;
    }
  }
  return NULL;
}


void __attribute__((used))__hexbox_apply_policy(struct hexbox_policy * policy){
  uint8_t i;
  uint32_t base_addr;

  for(i = NUM_RESERVED_REGIONS; i < AVAILABLE_NUM_MPU_REGIONS; i++){

      base_addr = policy->regions[i].base_addr;
      MPU_REGION_NUM_REG = i;
      MPU_REGION_ADDR_REG = base_addr; //sets region to write to
      MPU_REGION_ATTR_REG = policy->regions[i].attr;
  }

  if (policy->priv){
    SET_PRIVILEGES;
  }else{
    DROP_PRIVILEGES;
  }
}


void __attribute__((used))__hexbox_set_init(struct hexbox_policy * policy){
  uint8_t i;
  uint32_t base_addr;
  MPU_CONFIG_REG = MPU_DISABLE_CONSTANT;

  for(i=0;i<AVAILABLE_NUM_MPU_REGIONS;i++){

      base_addr = policy->regions[i].base_addr;
      MPU_REGION_NUM_REG = i;
      MPU_REGION_ADDR_REG = base_addr; //sets region to write to
      MPU_REGION_ATTR_REG = policy->regions[i].attr;
  }
  __asm volatile(
   "dsb \n\t"
   "isb \n\t");
  MPU_CONFIG_REG = MPU_ENABLE_CONSTANT;
}


void __hexbox_memset(uint32_t * buf, uint32_t len){
  uint32_t i =0;
  for(i = 0; i<len; i++){
    buf[i] = 0;
  }
}

//DWT CODE modified from
//https://stackoverflow.com/questions/32610019/arm-m4-instructions-per-cycle-ipc-counters

#define DWT_CYCCNT  ((volatile uint32_t*)0xE0001004)
#define DWT_EXCCNT  ((volatile uint32_t*)0xE000100C)
#define DWT_CONTROL ((volatile uint32_t*)0xE0001000)
#define SCB_DEMCR   ((volatile uint32_t*)0xE000EDFC)

void __hexbox_start_dwt_counter(){

  *SCB_DEMCR   = *SCB_DEMCR | 0x01000000;
  *DWT_CYCCNT  = 0; // reset the counter
  *DWT_CONTROL = *DWT_CONTROL | 1 ;
}


/**
* __hexbox_get_and_reset_dwt_counter
* Stops the DWT Counter, reads and clears it
* This enable capturing of just executing time without counting code num_used
* To profile the Execution
*
* Args: sub_isr add value to account for ISR stack counting if not 0
* Returns:  Count:  Value of DWT_counter
*/
uint32_t __hexbox_get_and_reset_dwt_counter(uint32_t sub_isr){
  uint32_t count;
  uint32_t delta;
  count = *DWT_CYCCNT;
  delta = count - __hexbox_total_exe_time;
  if (sub_isr){
    delta -= *DWT_EXCCNT;
  }
  else{
    delta += *DWT_EXCCNT;
    *DWT_EXCCNT = 0;
  }

  __hexbox_total_exe_time = count;

  //return delta;
  return delta;
}


void __hexbox_reset_stats(){
  __hexbox_entries = 0;
  __hexbox_exits = 0;
  __hexbox_entry_exe_time = 0;
  __hexbox_exit_exe_time = 0;
  __hexbox_init_exe_time = 0;
  __hexbox_total_exe_time = 0;
  __hexbox_unknown_comp_exe_time = 0;
  __hexbox_memset(__hexbox_comp_exits, MAX_COMPS);
  __hexbox_memset(__hexbox_comp_entries, MAX_COMPS);
  __hexbox_memset(__hexbox_comp_exe_times, MAX_COMPS);
  __hexbox_memset(__hexbox_comp_emu_calls, MAX_COMPS);
  __hexbox_memset(__hexbox_comp_emu_exe_times, MAX_COMPS);

}

/*
__hexbox_start

Sets up the first comparment and enters it.  Call function automatically
added by compiler before main executes by compiler.
*/
void __attribute__((used))__hexbox_start(struct hexbox_policy * d){
#ifndef ENFORCE
  __profiler_clear_record_buffer();
#endif

  hexbox_comp_stack_ptr = &hexbox_comp_stack[0];

  MPU_CONFIG_REG = MPU_DISABLE_CONSTANT;
  __hexbox_set_init(d);
  __asm volatile(
   "dsb \n\t"
   "isb \n\t");
   MPU_CONFIG_REG = MPU_ENABLE_CONSTANT;


  SHCSR |= SCB_SHCSR_MEMFAULTENA_Msk;  //Enable MemManage_Fault
  DEMCR |= 0x10000;  //Enable the debug monitor


  if (d->priv){
    SET_PRIVILEGES;
  }else{
    DROP_PRIVILEGES;
  }

}

__attribute__((naked))void SVC_Handler(){
  __asm (
    "push {lr}\n\t"
    "bl __hexbox_start_isr_timing\n\t"
    "mov R0,SP\n\t"
    "add R0,R0,4\n\t"  //Remove additon to the stack
    "bl handle_svc\n\t" //its return value will be in R0 and first arg to __hexbox_stop_isr_timing
    "pop {lr}\n\t"
    "b __hexbox_stop_switch_isr_timing\n\t"  //its return will exit
  );
}


__attribute__((naked))void MemManage_Handler(){
  __asm(
    "push {lr}\n\t"
    "bl __hexbox_start_isr_timing\n\t"
    "pop {lr}\n\t"
    "pop {R0-R3}\n\t"
    "ldr R12,=__hexbox_emulator_registers \n\t"
    "stmia R12!, {R0-R11} \n\t"
    "pop {R0,R2,R3,R4} \n\t"
    "mov R1,SP \n\t"
    "stmia R12!, {R0-R4} \n\t"
    "ldr R0,[R3] \n\t"
    "ldr R1,=__hexbox_emulator_registers \n\t"
    "ldr SP,=__hexbox_emulator_stack+(100*4) \n\t"
    "push {lr} \n\t"
    "bl __hexbox_MemManage_Handler \n\t"
    "pop {lr} \n\t"
    "ldr r12,=__hexbox_emulator_registers+(13*4)\n\t"
    "ldmia r12,{r0-r3} \n\t"
    "mov sp,r0 \n\t"
    "push {r1-r3}\n\t"
    "ldr r12,=__hexbox_emulator_registers \n\t"
    "ldmia r12!, {r0-r11} \n\t"
    "ldr r12, [r12] \n\t"
    "push {r0-r3,r12} \n\t"
    "push {lr}\n\t"
    "bl __hexbox_stop_emu_isr_timing\n\t"
    "pop {lr}\n\t"
    "bx lr\n\t"
  );

}


void __hexbox_start_isr_timing(){
  uint32_t exe_time = __hexbox_get_and_reset_dwt_counter(1);
  uint32_t id;
  if (stack_initialized == 0){
      __hexbox_init_exe_time += exe_time;
  }else{
    id = hexbox_comp_stack_ptr->policy->id;
    if (id <MAX_COMPS){
      __hexbox_comp_exe_times[id] += exe_time;
    }else{
      __hexbox_unknown_comp_exe_time += exe_time;
    }
  }
}

void __hexbox_stop_switch_isr_timing(enum hexbox_switch_type type){
  uint32_t exe_time = __hexbox_get_and_reset_dwt_counter(0);
  uint32_t id;
  switch (type){
    case ENTRY:
      id = hexbox_comp_stack_ptr->policy->id;
      __hexbox_entries++;
      __hexbox_comp_entries[id]++;
      __hexbox_entry_exe_time += exe_time;
      break;
    case EXIT:
      id = hexbox_comp_stack_ptr->policy->id;
      __hexbox_exits++;
      __hexbox_comp_exits[id]++;
      __hexbox_exit_exe_time += exe_time;
      break;
    case START:
      __hexbox_reset_stats();
      __hexbox_start_dwt_counter();
      break;
    default:
      HEXBOX_FAULT
      break;
  }
}

void __hexbox_stop_emu_isr_timing(){
  uint32_t exe_time = __hexbox_get_and_reset_dwt_counter(0);
  uint32_t id = hexbox_comp_stack_ptr->policy->id;
  __hexbox_comp_emu_calls[id]++;

  __hexbox_comp_emu_exe_times[id] += exe_time;
}

void __hexbox_MemManage_Handler(uint32_t instr, struct reg_frame * Regs){
  
  if ( ((CFSR ^ 0x82) == 0) ) //Data only violation, or precise data bus fault
  {
    uint32_t id = hexbox_comp_stack_ptr->policy->id;
    uint8_t inst_size = 0;
    Regs->pc += emulate_store(instr,(uint32_t *)Regs, id);

  }
  else{
    HEXBOX_FAULT  //Invalid memory access, or other memory fault
  }

}
