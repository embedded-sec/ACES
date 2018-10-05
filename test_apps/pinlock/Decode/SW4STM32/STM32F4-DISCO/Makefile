######################################
# Makefile by CubeMX2Makefile.py
######################################

#Path to base of all hexbox repos
HEXBOX_ROOT = $(HOME)/open_source_code/ACES/

######################################
# target
######################################

HEXBOX_POLICY_METHOD ?= filename
NUM_MPU_REGIONS ?= 8
BUILD_OPTIONS = --$(HEXBOX_METHOD)--mpu-$(NUM_MPU_REGIONS)
TARGET= PinLock$(BUILD_OPTIONS)

######################################
# building variables
######################################
# debug build?
DEBUG = 1
# optimization
OPT_LEVEL = O0
OPT = $(OPT_LEVEL)

#######################################
# pathes
#######################################
# Build path
BUILD_DIR = .build
HEXBOX_DIR =$(BUILD_DIR)/hexbox
BIN_DIR = bin

######################################
# source
######################################
C_SOURCES = ../../Src/main.c ../../Src/stm32f4xx_it.c ../../Src/system_stm32f4xx.c ../../Src/stm32f4xx_hal_msp.c ../../../Drivers/stm32f4xx_hal_uart.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma_ex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_hcd.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c_ex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr_ex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rtc.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_spi.c ../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c  ../../../Drivers/BSP/STM32F4-Discovery/stm32f4_discovery.c ../../../mbedtls-2.2.1/library/sha256.c
ASM_SOURCES = ../../SW4STM32/startup_stm32f407xx.s

#######################################
# binaries
#######################################
CLANG = $(HEXBOX_ROOT)/llvm/bins/bin/clang
LLVMGOLD = $(HEXBOX_ROOT)/llvm/bins/lib/LLVMgold.so
ARM_NONE_EABI_PATH = $(HEXBOX_ROOT)/gcc/bins/
CC = $(CLANG)
AS = $(CLANG)
LD = $(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-ld
CP = $(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-objcopy
AR = $(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-ar
SZ = $(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-size
HEX = $(CP) -O ihex
BIN = $(CP) -O binary -S

#######################################
# Hexbox defines
#######################################
HEXBOX_POLICY_FILE = $(HEXBOX_DIR)/hexbox-policy$(BUILD_OPTIONS).json
HEXBOX_FINAL_POLICY_FILE = $(HEXBOX_DIR)/hexbox-final-policy$(BUILD_OPTIONS).json
HEXBOX_SIZE_FILE = $(HEXBOX_DIR)/hexbox-size$(BUILD_OPTIONS).json
HEXBOX_ANALYSIS_FILE = $(HEXBOX_DIR)/hexbox-analysis$(BUILD_OPTIONS).json
#HEXBOX_IR_FILE = $(BIN_DIR)/$(TARGET).elf.0.2.internalize.bc
HEXBOX_IR_FILE = $(BIN_DIR)/$(TARGET).elf.0.5.precodegen.bc
#HEXBOX_LINKER_TEMPLATE = $(LDSCRIPT)
HEXBOX_INTER_LINKER_SCRIPT = $(HEXBOX_DIR)/hexbox-intermediate$(BUILD_OPTIONS).ld
HEXBOX_FINAL_LINKER_SCRIPT = $(HEXBOX_DIR)/hexbox-final$(BUILD_OPTIONS).ld
HEXBOX_MEM_ACCESSES = mem_accesses$(BUILD_OPTIONS).o

#######################################
# CFLAGS
#######################################
# macros for gcc
AS_DEFS =
C_DEFS = -DUSE_HAL_DRIVER -DSTM32F407xx -DUSE_STM32F4_DISCO
# includes for gcc
AS_INCLUDES =
C_INCLUDES = -I../../inc -I ../../../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I ../../../Drivers/STM32F4xx_HAL_Driver/Inc -I ../../../Drivers -I ../../../Drivers/BSP/STM32F4-Discovery -I ../../../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I ../../../Drivers/CMSIS/Include -I ../../../mbedtls-2.2.1/include/mbedtls
# compile gcc flags

C_INCLUDES += -I$(HEXBOX_ROOT)gcc/bins//arm-none-eabi/include

ASFLAGS = -mcpu=cortex-m4 soft $(AS_DEFS) $(AS_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections -flto
CFLAGS = -mcpu=cortex-m4 -mfloat-abi=soft $(C_DEFS) $(C_INCLUDES) -$(OPT) -Wall -fdata-sections -ffunction-sections -target arm-none-eabi -mthumb
CFLAGS += --sysroot=$(ARM_NONE_EABI_PATH)arm-none-eabi -fno-builtin -fshort-enums -fno-exceptions -flto -ffreestanding -fmessage-length=0 -ffunction-sections -g
ifeq ($(DEBUG), 1)
CFLAGS += -g -gdwarf-2
endif
# Generate dependency information
#CFLAGS += -std=c99 -MD -MP -MF .dep/$(@F).d

#######################################
# LDFLAGS
#######################################
# link script
LDSCRIPT = STM32F407VGTx_FLASH.ld
# libraries
LIBS = -lc -lm
LIBDIR = -L $(HEXBOX_ROOT)gcc/bins//arm-none-eabi/lib/thumb/v7e-m -L $(HEXBOX_ROOT)gcc/bins//lib/gcc/arm-none-eabi/6.3.1/thumb/v7e-m 

LDFLAGS=-plugin=$(LLVMGOLD) --plugin-opt=save-temps -g --plugin-opt=-mcpu=cortex-m4
LDFLAGS+=--plugin-opt=-float-abi=soft --plugin-opt=$(OPT_LEVEL) --start-group -lc -lm -lgcc --end-group
LDFLAGS+= $(LIBDIR) $(LIBS)  -Map=$(BUILD_DIR)/$(TARGET).map --gc-sections

##############################################################################
# default action: build all
# primary TARGETS

all: baseline hexbox_record hexbox

baseline: setup $(BIN_DIR) $(BIN_DIR)/$(TARGET).elf

hexbox: setup $(BIN_DIR) $(BIN_DIR)/$(TARGET)--hexbox--final.elf

hexbox_record: setup $(BIN_DIR) $(BIN_DIR)/$(TARGET)--hexbox--record.elf

hexbox_inter: setup $(BIN_DIR) $(BIN_DIR)/$(TARGET)--hexbox--inter.elf

dot : $(BIN_DIR) $(HEXBOX_DIR) $(HEXBOX_DIR)/$(TARGET).svg

setup:
	export C_INCLUDE_PATH=$(HEXBOX_ROOT)gcc/bins//arm-none-eabi/include

FORCE :
#######################################
# build the application
#######################################
# list of ASM program objects
ASM_OBJECTS = $(addprefix $(BUILD_DIR)/,$(notdir $(ASM_SOURCES:.s=.o)))
vpath %.s $(sort $(dir $(ASM_SOURCES)))

# list of objects
OBJECTS += $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
vpath %.c $(sort $(dir $(C_SOURCES)))

HEXBOX_MEM_ACCESS_OBJECT = $(addprefix $(HEXBOX_DIR)/,$(notdir $(HEXBOX_MEM_ACCESSES:.s=.o)))
vpath %.c $(sort $(dir $(HEXBOX_MEM_ACCESSES)))

OBJECTS += $(HEXBOX_ROOT)llvm/hexbox-rt-lib/syscalls-v7e-m.o
###############################################
# Setup HEXBOX applciations

HEXBOX_ASM_OBJECTS = $(addprefix $(HEXBOX_DIR)/,$(notdir $(ASM_SOURCES:.s=.o)))
vpath %.s $(sort $(dir $(ASM_SOURCES)))

# list of objects
HEXBOX_OBJECTS += $(addprefix $(HEXBOX_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
vpath %.c $(sort $(dir $(C_SOURCES)))

HEXBOX_OBJECTS += $(HEXBOX_ROOT)llvm/hexbox-rt-lib/syscalls-v7e-m.o


$(BUILD_DIR)/%.o: %.c Makefile | $(BUILD_DIR)
	$(CC) -c $(CFLAGS) $< -o $@

$(BUILD_DIR)/%.o: %.s Makefile | $(BUILD_DIR)
	$(AS) -c $(CFLAGS) $< -o $@

$(BIN_DIR)/$(TARGET).elf: $(ASM_OBJECTS) $(OBJECTS) Makefile
	$(LD) $(ASM_OBJECTS) $(OBJECTS)	$(LDFLAGS) -T$(LDSCRIPT) \
	--plugin-opt=-info-output-file=$@.stats -o $@ -g
	$(SZ) $@

$(BUILD_DIR):
	mkdir -p $@

$(HEXBOX_DIR)/%.o: %.c Makefile | $(HEXBOX_DIR)
	$(CC) -c $(CFLAGS) $< -o $@

$(HEXBOX_DIR)/%.o: %.s Makefile | $(HEXBOX_DIR)
	$(AS) -c $(CFLAGS) $< -o $@

# Build baseline saving intermediates
$(HEXBOX_IR_FILE): $(BIN_DIR)/$(TARGET).elf

# Build default saving intermediates
$(HEXBOX_IR_FILE): $(BIN_DIR)/$(TARGET).elf

# Run Analysis on IR
$(HEXBOX_ANALYSIS_FILE): $(HEXBOX_IR_FILE) Makefile | $(HEXBOX_DIR)
	$(LD) $(ASM_OBJECTS) $(HEXBOX_IR_FILE) $(LDFLAGS) -T$(LDSCRIPT) \
	--plugin-opt=-info-output-file=$@.stats -o $@ -g \
	--plugin-opt=-hexbox-analysis-results=$(HEXBOX_ANALYSIS_FILE) \
	--plugin-opt=-hexbox-analysis-size=$(HEXBOX_SIZE_FILE) \
	-o $(BIN_DIR)/$(TARGET)--baseline.elf >/dev/null 2>/dev/null

# Generate Linker Script and Partitioning
$(HEXBOX_POLICY_FILE): $(HEXBOX_ANALYSIS_FILE) Makefile | $(HEXBOX_DIR)
	python $(HEXBOX_ROOT)/compiler/graph_analysis/analyzer.py -j=$(HEXBOX_ANALYSIS_FILE) -s=$(HEXBOX_SIZE_FILE) \
	  -o=$(HEXBOX_POLICY_FILE) -T=$(LDSCRIPT) -L=$(HEXBOX_INTER_LINKER_SCRIPT) \
	  -m=$(HEXBOX_METHOD) -b=STM32F479 -n=$(NUM_MPU_REGIONS)

# Generate Linker Script and Partitioning
$(HEXBOX_INTER_LINKER_SCRIPT): $(HEXBOX_ANALYSIS_FILE) Makefile | $(HEXBOX_DIR)
	python $(HEXBOX_ROOT)/compiler/graph_analysis/analyzer.py -j=$(HEXBOX_ANALYSIS_FILE) -s=$(HEXBOX_SIZE_FILE) \
    -o=$(HEXBOX_POLICY_FILE) -T=$(LDSCRIPT) -L=$(HEXBOX_INTER_LINKER_SCRIPT) \
    -m=$(HEXBOX_METHOD) -b=STM32F479

$(HEXBOX_FINAL_LINKER_SCRIPT): $(BIN_DIR)/$(TARGET)--hexbox--inter.elf Makefile | $(HEXBOX_DIR)
			python $(HEXBOX_ROOT)/compiler/graph_analysis/final_linker_gen.py -o=$(BIN_DIR)/$(TARGET)--hexbox--inter.elf \
			-t=$(LDSCRIPT) -l=$(HEXBOX_FINAL_LINKER_SCRIPT) -p=$(HEXBOX_POLICY_FILE)\
			-f=$(HEXBOX_FINAL_POLICY_FILE)

$(HEXBOX_FINAL_POLICY_FILE): $(BIN_DIR)/$(TARGET)--hexbox--inter.elf Makefile | $(HEXBOX_DIR)
			python $(HEXBOX_ROOT)/compiler/graph_analysis/final_linker_gen.py -o=$(BIN_DIR)/$(TARGET)--hexbox--inter.elf \
			-t=$(LDSCRIPT) -l=$(HEXBOX_FINAL_LINKER_SCRIPT) -p=$(HEXBOX_POLICY_FILE)\
			-f=$(HEXBOX_FINAL_POLICY_FILE)

# Generate Intermediate Partitioned Binary
$(BIN_DIR)/$(TARGET)--hexbox--inter.elf:$(HEXBOX_POLICY_FILE) $(HEXBOX_INTER_LINKER_SCRIPT) | $(HEXBOX_DIR)
	$(LD) $(ASM_OBJECTS) $(HEXBOX_IR_FILE) $(HEXBOX_ROOT)/llvm/hexbox-rt-lib/record-hexbox-rt-v7e-m.o $(LDFLAGS) \
    --plugin-opt=-info-output-file=$@.stats \
    --plugin-opt=-hexbox-policy=$(HEXBOX_POLICY_FILE) \
    -T$(HEXBOX_INTER_LINKER_SCRIPT) \
    -o $@

# Generate Record Partitioned Binary
$(BIN_DIR)/$(TARGET)--hexbox--record.elf:$(HEXBOX_FINAL_POLICY_FILE) $(HEXBOX_FINAL_LINKER_SCRIPT)| $(HEXBOX_DIR)
	$(LD) $(ASM_OBJECTS) $(HEXBOX_IR_FILE) $(HEXBOX_ROOT)/llvm/hexbox-rt-lib/record-hexbox-rt-v7e-m.o $(LDFLAGS) \
    --plugin-opt=-info-output-file=$@.stats \
    --plugin-opt=-hexbox-policy=$(HEXBOX_FINAL_POLICY_FILE) \
    -T$(HEXBOX_FINAL_LINKER_SCRIPT) \
    -o $@

# Generate Final Partitioned Binary
$(BIN_DIR)/$(TARGET)--hexbox--final.elf:$(HEXBOX_FINAL_POLICY_FILE) $(HEXBOX_FINAL_LINKER_SCRIPT) $(HEXBOX_MEM_ACCESS_OBJECT)| $(HEXBOX_DIR)
	$(LD) $(ASM_OBJECTS) $(HEXBOX_MEM_ACCESS_OBJECT) $(HEXBOX_IR_FILE) $(HEXBOX_ROOT)/llvm/hexbox-rt-lib/enforce-hexbox-rt-v7e-m.o $(LDFLAGS) \
    --plugin-opt=-info-output-file=$@.stats \
    --plugin-opt=-hexbox-policy=$(HEXBOX_FINAL_POLICY_FILE) \
    -T$(HEXBOX_FINAL_LINKER_SCRIPT) \
    -o $@


# Generate Final Partitioned Binary
$(BIN_DIR)/$(TARGET)--hexbox--final.elf:$(HEXBOX_FINAL_POLICY_FILE) $(HEXBOX_FINAL_LINKER_SCRIPT) $(HEXBOX_MEM_ACCESS_OBJECT)| $(HEXBOX_DIR)
	$(LD) $(ASM_OBJECTS) $(HEXBOX_MEM_ACCESS_OBJECT) $(HEXBOX_IR_FILE) \
    $(LDFLAGS) $(HEXBOX_ROOT)/llvm/hexbox-rt-lib/enforce-hexbox-rt-v7e-m.o \
    --plugin-opt=-info-output-file=$@.stats \
    --plugin-opt=-hexbox-policy=$(HEXBOX_FINAL_POLICY_FILE) \
    -T$(HEXBOX_FINAL_LINKER_SCRIPT) \
    -o $@ -g



$(HEXBOX_DIR)/$(TARGET).dot: $(HEXBOX_ANALYSIS_FILE) FORCE
	python $(HEXBOX_ROOT)compiler/graph_analysis/analyzer.py -j=$(HEXBOX_ANALYSIS_FILE) -s=$(HEXBOX_SIZE_FILE) \
	-d=$@

$(HEXBOX_DIR)/$(TARGET).svg: $(HEXBOX_DIR)/$(TARGET).dot FORCE
	dot -Tsvg $^ -o $@

$(HEXBOX_DIR):
	mkdir -p $@

$(BIN_DIR):
	mkdir -p $@



#######################################
# clean up
#######################################
clean:
	-rm -fR .dep $(BUILD_DIR) $(BIN_DIR)
	-rm -f *.dot
	-rm -f run.tmp
#######################################
# dependencies
#######################################
-include $(shell mkdir .dep 2>/dev/null) $(wildcard .dep/*)

.PHONY: clean all

# *** EOF ***
