#include "emulator.h"
#ifndef ENFORCE
#include "profiler.h"
#endif
#include <stdio.h>
//******************************STORE INSTRUCTIONS***************************/
                                    // 16   12   8    4    0   12    8    4    0
                                  //|    |    |    |    |    |    |    |    |
#define tSTMIA       0xC000       //|1100|0 Rn|reg list |
#define tSTR_im2     0x9000         //|1001|0Rt | imm8    |
#define tSTR_im1     0x6000         //|0110|0imm5 |Rn |Rt |
#define tSTRB_im1    0x0000         //|0111|0imm5 |Rn |Rt |
#define tSTRH_im1    0x0000         //|1000|0imm5 |Rn |Rt |
#define tSTR_reg     0x0000         //|0101|000|Rm-Rn-| Rt|
#define tSTRB_reg    0x0000         //|0101|010|Rm-Rn-| Rt|
#define tSTRH_reg    0x0000         //|0101|001|Rm-Rn-| Rt|

#define t2STRB_im2   0x00000000     //|11111|000|0000| Rn | Rt |1PUW|  imm8   |
#define t2STRH_im2   0x00000000     //|11111|000|0010| Rn | Rt |1PUW|  imm8   |
#define t2STR_im2    0x00000000     //|11111|000|0100| Rn | Rt |1PUW|  imm8   |

#define t2STRB_im1   0x00000000     //|11111|000|1000| Rn | Rt |     imm12    |
#define t2STRH_im1   0x00000000     //|11111|000|1010| Rn | Rt |     imm12    |
#define t2STR_im1    0x00000000     //|11111|000|1100| Rn | Rt |     imm12    |

#define t2STRB_reg   0x00000000     //|11111|000|0000| Rn | Rt |0000|00i2| Rm |
#define t2STRH_reg   0x00000000     //|11111|000|0010| Rn | Rt |0000|00i2| Rm |
#define t2STR_reg    0x00000000     //|11111|000|0100| Rn | Rt |0000|00i2| Rm |

#define t2STRD_im    0x00000000     //|11101|00P|U1W0| Rn | Rt | Rt2|   imm8  |
#define t2STREX_im   0x00000000     //|11101|000|0100| Rn | Rt | Rd |   imm8  |
#define t2STREXB_im  0x00000000     //|11101|000|1100| Rn | Rt |1111|0100| Rd |
#define t2STREXH_im  0x00000000     //|11101|000|1100| Rn | Rt |1111|0101| Rd |
#define t2STMIA      0xE8800000     //|11101|000|1W00| Rn |0M0| reg list      |
#define t2STMDB      0xE9000000     //|11101|001|0W00| Rn |0M0| reg list      |

//******************************STORE INSTRUCTIONS***************************/

#define EMULATOR_FAULT while(1);

uint32_t AT_HEXBOX_DATA __hexbox_emulator_registers[17];
uint32_t AT_HEXBOX_DATA __hexbox_emulator_stack[200];


/**
void check_addr(uint32_t addr)

If compiled in ENFOCE mode
  Checks the address to determine if should be allowed or not
else
  Records the access and returns
*/
#ifdef ENFORCE
extern uint32_t* __hexbox_acl_lut[] AT_HEXBOX_CODE; //Needs to be in flash
void AT_HEXBOX_CODE check_addr(uint32_t comp_id, uint32_t addr){
     // ACLS list is (uint32_t size)[emulator_acl_entry1,entry 2.]
    uint32_t * buf_addr = __hexbox_acl_lut[comp_id];
    struct emulator_acl_entry * acl_entry_ptr;
    if (buf_addr != NULL){
      uint32_t size = buf_addr[0];
      acl_entry_ptr = (struct emulator_acl_entry *)(buf_addr + 1);
      for (uint32_t i = 0; i < size ; ++i ){
        if (acl_entry_ptr[i].start_addr <= addr  &&
            acl_entry_ptr[i].end_addr > addr){
          return;
        }
      }
    }
  EMULATOR_FAULT;
}

#else  // Record Mode ----------------------------------------------------
void AT_HEXBOX_CODE check_addr(uint32_t comp_id, uint32_t addr){
    //__profiler_record_emulator_addr(addr);
    __profiler_record_emulator_compartment_access(comp_id, addr);
    return;

}
#endif



/**
setup emulator

mov r12, :lower16:funct1_A\n\t"
"movt r12, :upper16:funct1_A\n\t"


*/
void AT_HEXBOX_CODE __attribute__((naked))__hexbox_emulator_isr_setup(){

  __asm(
    "pop {R0-R3}\n\t"
    "ldr R12,=__hexbox_emulator_registers \n\t"
    "stmia R12!, {R0-R11} \n\t"
    "pop {R0,R2,R3,R4} \n\t"
    "mov R1,SP \n\t"
    "stmia R12!, {R0-R4} \n\t"
    "ldr R0,[R3] \n\t"
    "ldr R1,=__hexbox_emulator_registers \n\t"
    "ldr SP,=__hexbox_emulator_stack+(400-4) \n\t"
    "bl emulate_store \n\t"
    "ldr r12,=__hexbox_emulator_registers+44\n\t"
    "ldmia r12,{r0-r4} \n\t"
    "mov sp,r1 \n\t"
    "sub r12,r12,44 \n\t"
    "ldmia r12!, {r0-r11} \n\t"
    "ldr r12, [r12] \n\t"
    "push {r0-r3,r12} \n\t"
    "bx lr\n\t"
  );
}

uint8_t AT_HEXBOX_CODE emulate_store(uint32_t inst,uint32_t * Regs, uint32_t comp_id){
  uint16_t opcode;
  uint16_t thumb_inst;
  uint8_t Rn;
  uint8_t Rm;
  uint8_t Rt;
  uint8_t i;
  uint32_t offset;
  uint16_t reg_list;
  uint32_t addr;
  uint32_t size;
  uint8_t wback;
  uint8_t add;
  uint32_t index;

  opcode = inst & 0xF800;
  thumb_inst = inst &0xFFFF;
  switch (opcode){
    case 0xC000 :
      //tSTMIA       0xC000       //|1100|0 Rn|reg list |
      Rn = (thumb_inst >>8) & 7;
      for (reg_list = thumb_inst&0xff, i=0 ;
            reg_list;
            ++i, reg_list = reg_list>>1){
        if (reg_list & 1){
          check_addr(comp_id, Regs[Rn]);
          *((uint32_t *)Regs[Rn]) = Regs[i];
          Regs[Rn] += 4;
        }
      }
      return 2;
      break;
    case 0x9000 :
      //tSTR_im2     STR<c> <Rt>,[SP,#<imm8>]      //|1001|0Rt | imm8    |
      Rt = (thumb_inst>>8) & 0x7;
      Rn = 13;//SP
      offset = ((thumb_inst & 0xFF)<<2);
      addr = Regs[Rn]+offset;
      check_addr(comp_id, addr);
      *(uint32_t *)addr = Regs[Rt];
      return 2;
      break;
    case 0x6000 :
      //tSTR_im1     0x6000         //|0110|0imm5 |Rn |Rt |
      Rn = (thumb_inst>>3) & 0x7;
      Rt = thumb_inst & 0x7;
      offset = (thumb_inst>>4) & 0x7C; //imm5:00
      addr = Regs[Rn]+offset;
      check_addr(comp_id, addr);
      *(uint32_t *)addr = Regs[Rt];
      return 2;
      break;
    case 0x7000 :
      //tSTRB_im1    0x0000         //|0111|0imm5 |Rn |Rt |
      offset = (thumb_inst>>6) & 0x1F;
      Rn = (thumb_inst>>3) & 0x7;
      Rt = thumb_inst & 0x7;
      addr = Regs[Rn]+offset;
      check_addr(comp_id, addr);
      *((uint8_t*)addr) = Regs[Rt];
      return 2;
      break;
    case  0x8000:
      //tSTRH_im1    0x0000         //|1000|0imm5 |Rn |Rt |
      offset = (thumb_inst>>5) & (0x1F<<1);
      Rn = (thumb_inst>>3) & 0x7;
      Rt = thumb_inst & 0x7;
      addr = Regs[Rn]+offset;
      check_addr(comp_id, addr);
      *((uint16_t*)addr) = Regs[Rt];
      return 2;
      break;
    case 0x5000 :
      //tSTR_reg     0x0000         //|0101|000|Rm-Rn-| Rt|
      //tSTRB_reg    0x0000         //|0101|010|Rm-Rn-| Rt|
      //tSTRH_reg    0x0000         //|0101|001|Rm-Rn-| Rt|
      size = (thumb_inst >> 9) & 0x7;
      Rm = (thumb_inst>>6) & 0x7;
      Rn = (thumb_inst>>3) & 0x7;
      Rt = thumb_inst & 0x7;
      addr = Regs[Rn]+Regs[Rm];
      check_addr(comp_id, addr);
      switch(size){
        case 0:
          *(uint32_t *)addr = Regs[Rt];
          break;
        case 1:
            *(uint16_t *)addr = Regs[Rt];
            break;
        case 2:
            *(uint8_t *)addr = Regs[Rt];
            break;
        default:
          EMULATOR_FAULT;
      };
      return 2;
      break;
    case  0xF800:
      size = (inst>>4) & 0x7;
      Rt = (inst >> 28) & 0xF;
      Rn = inst & 0xF;
      wback = 0;
      index = 1;
      add = 1;
      if (inst & 0x0080){
        //t2STRB_im1   //| Rt |     imm12    |11111|000|1000| Rn |
        //t2STRH_im1   //| Rt |     imm12    |11111|000|1010| Rn |
        //t2STR_im1    //| Rt |     imm12    |11111|000|1100| Rn |
        offset = (inst>>16) & 0xFFF;
      }else if (inst & 0x08000000){
        //t2STRB_im2   0x00000000     //| Rt |1PUW|  imm8   |11111|000|0000| Rn |
        //t2STRH_im2   0x00000000     //| Rt |1PUW|  imm8   |11111|000|0010| Rn |
        //t2STR_im2    0x00000000     //| Rt |1PUW|  imm8   |11111|000|0100| Rn |
        offset = (inst>>16) & 0xFF;
        index = (inst>>26) & 0x1;
        add = (inst>>25) & 0x1;
        wback = (inst>>24) & 0x1;
      }else{
        //t2STRB_reg   0x00000000     //| Rt |0000|00i2| Rm |11111|000|0000| Rn |
        //t2STRH_reg   0x00000000     //| Rt |0000|00i2| Rm |11111|000|0010| Rn |
        //t2STR_reg    0x00000000     //| Rt |0000|00i2| Rm |11111|000|0100| Rn |
        Rm = (inst>>16) & 0xF;
        offset = (inst >> 20) & 0x3;
        offset = Regs[Rm] << offset;
      }

      if (index == 1){
        if (add == 1){
          addr = Regs[Rn]+offset;
        }
        else{
          addr = Regs[Rn]-offset;
        }
      }else{
        addr = Regs[Rn];
      }
      check_addr(comp_id, addr);
      switch (size){
        case 0:
          *(uint8_t *)addr =(uint8_t)Regs[Rt];
          break;
        case 2:
          *(uint16_t *)addr =(uint16_t)Regs[Rt];
          break;
        case 4:
          *(uint32_t *)addr =(uint32_t)Regs[Rt];
          break;
        default:
          EMULATOR_FAULT;
          break;
        };
      if (wback){
          if (add){
            Regs[Rn] += offset;
          }else{
            Regs[Rn] -= offset;
          }
      }
      return 4;
      break;
    case  0xE800://Armv7m ARch reference Section A5 pg 142
        //0b 111|1101|0000
        Rn = (inst) &0xF;
        wback = (inst >> 5) & 1;
        addr = Regs[Rn];
        if ((inst & 0x7C0) == 0x080){
          //t2STMIA     //|0M0| reg list      |11101|000|10WL| Rn |
          reg_list = (inst>>16) & 0x5fff;
          addr = Regs[Rn];
          check_addr(comp_id, addr);
          for (i=0; reg_list; ++i, reg_list = reg_list>>1){
            if (reg_list & 1){
              *(uint32_t *)addr = Regs[i];
              addr += 4;
            }
          }
          if (wback){
            Regs[Rn]=addr;
          }
          return 4;
        }else if((inst & 0x7C0) == 0x100){
          //t2STMDB     //|0M0| reg list      |11101|001|00WL| Rn |
          reg_list = (inst>>16)&0x5fff;
          for (i=15; i != 0xFF; i--){
            if ((reg_list >> i) & 1){
              addr -= 4;
              check_addr(comp_id, addr);
              *(uint32_t* )addr = Regs[i];
            }
          }
          if (wback){
            Regs[Rn]=addr;
          }
          return 4;
        }else if (((inst & 0x170)==0x60) || ((inst & 0x150)==0x140)){
            //t2STD | Rt | Rt2 | imm8 |1110|100P|U1W0| Rn
            Rm = (inst>>24) & 0xf;
            Rt =  (inst>>28) & 0xf;
            add = (inst >>7) & 0x1;
            index = (inst>>8) & 0x01;
            offset = ((inst >>16) & 0xff) << 2;
            if (index){
              if(add){
                addr += offset;
              }
              else{
                addr -= offset;
              }
            }
            check_addr(comp_id, addr);
            *(uint32_t* )addr = Regs[Rt];
            check_addr(comp_id, addr+4);
            *(uint32_t* )(addr+4) = Regs[Rm];
            if (wback){
              if (add){
                Regs[Rn] += offset;
              }
              else{
                Regs[Rn] -= offset;
              }
            }
            return 4;
          }
        //Exclusive stores will cause this but I don't think I've seen them in
        //practice implement later
        EMULATOR_FAULT;
      break;
    case  0xb000:
      //tPUSH only pushes LR, r0-r7
      reg_list = (inst) & 0xff;
      Rn = 13;
      addr = Regs[Rn];
      //Save LR
      if((inst & 0x0100) != 0 ){
        addr -= 4;
        check_addr(comp_id, addr);
        *(uint32_t* )addr = Regs[14];
      }
      for (i=7; i != 0xFF; i--){
        if ((reg_list >> i) & 1){
          addr -= 4;
          check_addr(comp_id, addr);
          *(uint32_t* )addr = Regs[i];
        }
      }
      Regs[Rn]=addr;

      return 2;

    default:
      //perhaps fault
      EMULATOR_FAULT;
      return 0;
      break;

  };
  return 0;
}
