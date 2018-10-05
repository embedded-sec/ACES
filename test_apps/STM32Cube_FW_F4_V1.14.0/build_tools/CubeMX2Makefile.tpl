######################################
# Makefile by CubeMX2Makefile.py
######################################

######################################
# target
######################################
TARGET= $TARGET
HEXBOX_POLICY_METHOD= filename

######################################
# building variables
######################################
# debug build?
DEBUG = 1
# optimization
OPT_LEVEL = O0
OPT = $$(OPT_LEVEL)

#######################################
# pathes
#######################################
# Build path
BUILD_DIR = .build
HEXBOX_DIR =$$(BUILD_DIR)/hexbox
BIN_DIR = bin

######################################
# source
######################################
$C_SOURCES
$ASM_SOURCES

#######################################
# binaries
#######################################
CLANG = $LLVM_PATH/bin/clang
LLVMGOLD = $LLVM_PATH/lib/LLVMgold.so
ARM_NONE_EABI_PATH = $GCC_PATH
CC = $$(CLANG)
AS = $$(CLANG)
LD = $$(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-ld
CP = $$(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-objcopy
AR = $$(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-ar
SZ = $$(ARM_NONE_EABI_PATH)/bin/arm-none-eabi-size
HEX = $$(CP) -O ihex
BIN = $$(CP) -O binary -S

#######################################
# Hexbox defines
#######################################
HEXBOX_POLICY_FILE = $$(HEXBOX_DIR)/hexbox-policy.json
HEXBOX_FINAL_POLICY_FILE = $$(HEXBOX_DIR)/hexbox-final-policy.json
HEXBOX_SIZE_FILE = $$(HEXBOX_DIR)/hexbox-size.json
HEXBOX_ANALYSIS_FILE = $$(HEXBOX_DIR)/hexbox-analysis.json
HEXBOX_IR_FILE = $$(BIN_DIR)/$$(TARGET).elf.0.2.internalize.bc
#HEXBOX_LINKER_TEMPLATE = $$(LDSCRIPT)
HEXBOX_INTER_LINKER_SCRIPT = $$(HEXBOX_DIR)/hexbox-intermediate.ld
HEXBOX_FINAL_LINKER_SCRIPT = $$(HEXBOX_DIR)/hexbox-final.ld
HEXBOX_MEM_ACCESSES = mem_accesses.o

#######################################
# CFLAGS
#######################################
# macros for gcc
$AS_DEFS
$C_DEFS
# includes for gcc
$AS_INCLUDES
$C_INCLUDES
# compile gcc flags

C_INCLUDES += -I$GCC_PATH/arm-none-eabi/include

ASFLAGS = $MCU $FLOAT_ABI $$(AS_DEFS) $$(AS_INCLUDES) $$(OPT) -Wall -fdata-sections -ffunction-sections -flto
CFLAGS = $MCU -mfloat-abi=$FLOAT_ABI $$(C_DEFS) $$(C_INCLUDES) -$$(OPT) -Wall -fdata-sections -ffunction-sections -target arm-none-eabi -mthumb
CFLAGS += --sysroot=$$(ARM_NONE_EABI_PATH)arm-none-eabi -fno-builtin -fshort-enums -fno-exceptions -flto -ffreestanding -fmessage-length=0 -ffunction-sections -g
ifeq ($$(DEBUG), 1)
CFLAGS += -g -gdwarf-2
endif
# Generate dependency information
#CFLAGS += -std=c99 -MD -MP -MF .dep/$$(@F).d

#######################################
# LDFLAGS
#######################################
# link script
$LDSCRIPT
# libraries
LIBS = -lc -lm
LIBDIR = $LD_STD_LIBS $LD_LIB_DIRS

LDFLAGS=-plugin=$$(LLVMGOLD) --plugin-opt=save-temps -g --plugin-opt=$MCU
LDFLAGS+=--plugin-opt=-float-abi=$FLOAT_ABI --plugin-opt=$$(OPT_LEVEL) --start-group -lc -lm -lgcc --end-group
LDFLAGS+= $$(LIBDIR) $$(LIBS) $LD_LIBS -Map=$$(BUILD_DIR)/$$(TARGET).map --gc-sections

##############################################################################
# default action: build all
# primary TARGETS

all: default hexbox_record hexbox

default: setup $$(BIN_DIR) $$(BIN_DIR)/$$(TARGET).elf

hexbox: setup $$(BIN_DIR) $$(BIN_DIR)/$$(TARGET)--hexbox--final.elf

hexbox_record: setup $$(BIN_DIR) $$(BIN_DIR)/$$(TARGET)--hexbox--record.elf

hexbox_inter: setup $$(BIN_DIR) $$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf

dot : $$(BIN_DIR) $$(HEXBOX_DIR) $$(HEXBOX_DIR)/$$(TARGET).svg

setup:
	export C_INCLUDE_PATH=$GCC_PATH/arm-none-eabi/include

FORCE :
#######################################
# build the application
#######################################
# list of ASM program objects
ASM_OBJECTS = $$(addprefix $$(BUILD_DIR)/,$$(notdir $$(ASM_SOURCES:.s=.o)))
vpath %.s $$(sort $$(dir $$(ASM_SOURCES)))

# list of objects
OBJECTS += $$(addprefix $$(BUILD_DIR)/,$$(notdir $$(C_SOURCES:.c=.o)))
vpath %.c $$(sort $$(dir $$(C_SOURCES)))

HEXBOX_MEM_ACCESS_OBJECT = $$(addprefix $$(HEXBOX_DIR)/,$$(notdir $$(HEXBOX_MEM_ACCESSES:.s=.o)))
vpath %.c $$(sort $$(dir $$(HEXBOX_MEM_ACCESSES)))

OBJECTS += $CLANG_SYSCALLS_LIB
###############################################
# Setup HEXBOX applciations

HEXBOX_ASM_OBJECTS = $$(addprefix $$(HEXBOX_DIR)/,$$(notdir $$(ASM_SOURCES:.s=.o)))
vpath %.s $$(sort $$(dir $$(ASM_SOURCES)))

# list of objects
HEXBOX_OBJECTS += $$(addprefix $$(HEXBOX_DIR)/,$$(notdir $$(C_SOURCES:.c=.o)))
vpath %.c $$(sort $$(dir $$(C_SOURCES)))

HEXBOX_OBJECTS += $CLANG_SYSCALLS_LIB


$$(BUILD_DIR)/%.o: %.c Makefile | $$(BUILD_DIR)
	$$(CC) -c $$(CFLAGS) $$< -o $$@

$$(BUILD_DIR)/%.o: %.s Makefile | $$(BUILD_DIR)
	$$(AS) -c $$(CFLAGS) $$< -o $$@

$$(BIN_DIR)/$$(TARGET).elf: $$(ASM_OBJECTS) $$(OBJECTS) Makefile
	$$(LD) $$(ASM_OBJECTS) $$(OBJECTS)	$$(LDFLAGS) -T$$(LDSCRIPT) \
	--plugin-opt=-info-output-file=$$@.stats -o $$@ -g
	$$(SZ) $$@

$$(BUILD_DIR):
	mkdir -p $$@

$$(HEXBOX_DIR)/%.o: %.c Makefile | $$(HEXBOX_DIR)
	$$(CC) -c $$(CFLAGS) $$< -o $$@

$$(HEXBOX_DIR)/%.o: %.s Makefile | $$(HEXBOX_DIR)
	$$(AS) -c $$(CFLAGS) $$< -o $$@

# Build default saving intermediates
$$(HEXBOX_IR_FILE): $$(BIN_DIR)/$$(TARGET).elf

# Run Analysis on IR
$$(HEXBOX_ANALYSIS_FILE): $$(HEXBOX_IR_FILE) Makefile | $$(HEXBOX_DIR)
	$$(LD) $$(ASM_OBJECTS) $$(HEXBOX_IR_FILE) $$(LDFLAGS) -T$$(LDSCRIPT) \
	--plugin-opt=-info-output-file=$$@.stats -o $$@ -g \
	--plugin-opt=-hexbox-analysis-results=$$(HEXBOX_ANALYSIS_FILE) \
	--plugin-opt=-hexbox-analysis-size=$$(HEXBOX_SIZE_FILE) \
	-o $$(BIN_DIR)/$$(TARGET)--baseline.elf >/dev/null 2>/dev/null

# Generate Linker Script and Partitioning
$$(HEXBOX_POLICY_FILE): $$(HEXBOX_ANALYSIS_FILE) Makefile | $$(HEXBOX_DIR)
	python $HEXBOX_GRAPH_TOOL -j=$$(HEXBOX_ANALYSIS_FILE) -s=$$(HEXBOX_SIZE_FILE) \
	  -o=$$(HEXBOX_POLICY_FILE) -T=$$(LDSCRIPT) -L=$$(HEXBOX_INTER_LINKER_SCRIPT) \
	  -m=$$(HEXBOX_POLICY_METHOD) -b=STM32F479

# Generate Linker Script and Partitioning
$$(HEXBOX_INTER_LINKER_SCRIPT): $$(HEXBOX_ANALYSIS_FILE) Makefile | $$(HEXBOX_DIR)
	python $HEXBOX_GRAPH_TOOL -j=$$(HEXBOX_ANALYSIS_FILE) -s=$$(HEXBOX_SIZE_FILE) \
    -o=$$(HEXBOX_POLICY_FILE) -T=$$(LDSCRIPT) -L=$$(HEXBOX_INTER_LINKER_SCRIPT) \
    -m=$$(HEXBOX_POLICY_METHOD) -b=STM32F479

$$(HEXBOX_FINAL_LINKER_SCRIPT): $$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf Makefile | $$(HEXBOX_DIR)
			python $HEXBOX_FINAL_LD_TOOL -o=$$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf \
			-t=$$(LDSCRIPT) -l=$$(HEXBOX_FINAL_LINKER_SCRIPT) -p=$$(HEXBOX_POLICY_FILE)\
			-f=$$(HEXBOX_FINAL_POLICY_FILE)

$$(HEXBOX_FINAL_POLICY_FILE): $$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf Makefile | $$(HEXBOX_DIR)
			python $HEXBOX_FINAL_LD_TOOL -o=$$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf \
			-t=$$(LDSCRIPT) -l=$$(HEXBOX_FINAL_LINKER_SCRIPT) -p=$$(HEXBOX_POLICY_FILE)\
			-f=$$(HEXBOX_FINAL_POLICY_FILE)

# Generate Intermediate Partitioned Binary
$$(BIN_DIR)/$$(TARGET)--hexbox--inter.elf:$$(HEXBOX_POLICY_FILE) $$(HEXBOX_INTER_LINKER_SCRIPT) | $$(HEXBOX_DIR)
	$$(LD) $$(ASM_OBJECTS) $$(HEXBOX_IR_FILE) $HEXBOX_RT_LIB_RECORD $$(LDFLAGS) \
    --plugin-opt=-info-output-file=$$@.stats \
    --plugin-opt=-hexbox-policy=$$(HEXBOX_POLICY_FILE) \
    -T$$(HEXBOX_INTER_LINKER_SCRIPT) \
    -o $$@

# Generate Record Partitioned Binary
$$(BIN_DIR)/$$(TARGET)--hexbox--record.elf:$$(HEXBOX_FINAL_POLICY_FILE) $$(HEXBOX_FINAL_LINKER_SCRIPT)| $$(HEXBOX_DIR)
	$$(LD) $$(ASM_OBJECTS) $$(HEXBOX_IR_FILE) $HEXBOX_RT_LIB_RECORD $$(LDFLAGS) \
    --plugin-opt=-info-output-file=$$@.stats \
    --plugin-opt=-hexbox-policy=$$(HEXBOX_FINAL_POLICY_FILE) \
    -T$$(HEXBOX_FINAL_LINKER_SCRIPT) \
    -o $$@

# Generate Final Partitioned Binary
$$(BIN_DIR)/$$(TARGET)--hexbox--final.elf:$$(HEXBOX_FINAL_POLICY_FILE) $$(HEXBOX_FINAL_LINKER_SCRIPT) $$(HEXBOX_MEM_ACCESS_OBJECT)| $$(HEXBOX_DIR)
	$$(LD) $$(ASM_OBJECTS) $$(HEXBOX_MEM_ACCESS_OBJECT) $$(HEXBOX_IR_FILE) $HEXBOX_RT_LIB_ENFORCE $$(LDFLAGS) \
    --plugin-opt=-info-output-file=$$@.stats \
    --plugin-opt=-hexbox-policy=$$(HEXBOX_FINAL_POLICY_FILE) \
    -T$$(HEXBOX_FINAL_LINKER_SCRIPT) \
    -o $$@



$$(HEXBOX_DIR)/$$(TARGET).dot: $$(HEXBOX_ANALYSIS_FILE) FORCE
	python $HEXBOX_GRAPH_TOOL -j=$$(HEXBOX_ANALYSIS_FILE) -s=$$(HEXBOX_SIZE_FILE) \
	-d=$$@

$$(HEXBOX_DIR)/$$(TARGET).svg: $$(HEXBOX_DIR)/$$(TARGET).dot FORCE
	dot -Tsvg $$^ -o $$@

$$(HEXBOX_DIR):
	mkdir -p $$@

$$(BIN_DIR):
	mkdir -p $$@


results.csv:
	python $HEXBOX_RESULT_TOOL \
	-f=$$(BIN_DIR)/$$(TARGET)--hexbox--final.elf \
	-g=$$(HEXBOX_ANALYSIS_FILE) \
	-c=$$(HEXBOX_FINAL_POLICY_FILE) \
	-b=$$(BIN_DIR)/$$(TARGET)--baseline.elf
#######################################
# clean up
#######################################
clean:
	-rm -fR .dep $$(BUILD_DIR) $$(BIN_DIR)
	-rm -f *.dot
	-rm -f run.tmp

#######################################
# dependencies
#######################################
-include $$(shell mkdir .dep 2>/dev/null) $$(wildcard .dep/*)

.PHONY: clean all

# *** EOF ***
