
BUILD_DIR = ../../llvm/hexbox-rt-lib
LLVM_PATH = ../../llvm/bins/bin
INCLUDE_PATH = ../../gcc/bins/arm-none-eabi/include/
CLANG = $(LLVM_PATH)/clang
OPT_LEVEL = -O2


CFLAGS = -flto -fno-exceptions -I$(INCLUDE_PATH) -fshort-enums
CFLAGS += -fno-builtin -ffreestanding -fmessage-length=0 -ffunction-sections -g
CFLAGS += -gdwarf-2 -fdata-sections


all: syscalls hexbox-enforce hexbox-record


hexbox-enforce: $(BUILD_DIR) $(BUILD_DIR)/enforce-hexbox-rt-v6-m.o \
				$(BUILD_DIR)/enforce-hexbox-rt-v7-m.o \
				$(BUILD_DIR)/enforce-hexbox-rt-v7e-m.o
	@echo Done Building Hexbox-Enforce


hexbox-record: $(BUILD_DIR) $(BUILD_DIR)/record-hexbox-rt-v6-m.o \
				$(BUILD_DIR)/record-hexbox-rt-v7-m.o \
				$(BUILD_DIR)/record-hexbox-rt-v7e-m.o
	@echo Done Building Hexbox-Record

syscalls: $(BUILD_DIR) $(BUILD_DIR)/syscalls-v6-m.o \
					$(BUILD_DIR)/syscalls-v7-m.o \
					$(BUILD_DIR)/syscalls-v7e-m.o
	@echo Done Building Syscalls

$(BUILD_DIR):
	mkdir -p $@

# ===========================Syscalls ==========================================
$(BUILD_DIR)/syscalls-v6-m.o: syscalls-v6-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/syscalls-v7-m.o: syscalls-v7-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/syscalls-v7e-m.o: syscalls-v7e-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)
# ======================End  Syscalls ==========================================

# ======================Hexbox Enforce Lib =====================================
$(BUILD_DIR)/enforce-hexbox-rt-v6-m.o: enforce-hexbox-rt-v6-m.bc enforce-emulator-v6-m.bc enforce-profiler-v6-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/enforce-hexbox-rt-v7-m.o: enforce-hexbox-rt-v7-m.bc enforce-emulator-v7-m.bc enforce-profiler-v7-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/enforce-hexbox-rt-v7e-m.o: enforce-hexbox-rt-v7e-m.bc enforce-emulator-v7e-m.bc enforce-profiler-v7e-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)
# ====================== End Hexbox Enforce Lib ================================

# ======================Hexbox Record Lib =====================================
$(BUILD_DIR)/record-hexbox-rt-v6-m.o: record-hexbox-rt-v6-m.bc record-emulator-v6-m.bc record-profiler-v6-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/record-hexbox-rt-v7-m.o: record-hexbox-rt-v7-m.bc record-emulator-v7-m.bc record-profiler-v7-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)

$(BUILD_DIR)/record-hexbox-rt-v7e-m.o: record-hexbox-rt-v7e-m.bc record-emulator-v7e-m.bc record-profiler-v7e-m.bc
	$(LLVM_PATH)/llvm-link $^ -o $(@)
# ====================== End Record Enforce Lib ================================

# ====================== Compile to BitCode ====================================
enforce-%-v6-m.bc: %.c
	$(CLANG) -DENFORCE $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m0   \
	$(CFLAGS) $< -o $@

enforce-%-v7-m.bc: %.c
	$(CLANG) -DENFORCE $(OPT_LEVEL) -c -target arm-none-eabi -mcpu=cortex-m3   \
	$(CFLAGS) $< -o $@

enforce-%-v7e-m.bc: %.c
	$(CLANG) -DENFORCE $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m4   \
	$(CFLAGS) $< -o $@
# ====================== End Compile to BitCode ================================

# ====================== Compile to BitCode ====================================
record-%-v6-m.bc: %.c
	$(CLANG) $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m0   \
	$(CFLAGS) $< -o $@

record-%-v7-m.bc: %.c
	$(CLANG) $(OPT_LEVEL) -c -target arm-none-eabi -mcpu=cortex-m3   \
	$(CFLAGS) $< -o $@

record-%-v7e-m.bc: %.c
	$(CLANG) $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m4   \
	$(CFLAGS) $< -o $@
# ====================== End Compile to BitCode ================================


# ====================== Compile to BitCode ====================================
%-v6-m.bc: %.c
	$(CLANG) $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m0   \
	$(CFLAGS) $< -o $@

%-v7-m.bc: %.c
	$(CLANG) $(OPT_LEVEL) -c -target arm-none-eabi -mcpu=cortex-m3   \
	$(CFLAGS) $< -o $@

%-v7e-m.bc: %.c
	$(CLANG) $(OPT_LEVEL)  -c -target arm-none-eabi -mcpu=cortex-m4   \
	$(CFLAGS) $< -o $@
# ====================== End Compile to BitCode ================================

clean:
	rm -f *.o
	rm -f *.bc
	rm -f $(BUILD_DIR)/*.o
