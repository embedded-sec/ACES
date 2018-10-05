set -e
REPO_ROOT=$(readlink -f `dirname $0`/..)
PROJECT_ROOT_DIR=`dirname ${REPO_ROOT}`
THIS_DIR=`dirname \`readlink -f $0\``
LLVM_DIR=${PROJECT_ROOT_DIR}/llvm/llvm-release_40
CLANG_DIR=${PROJECT_ROOT_DIR}/llvm/clang-release_40


SYM_LINK='ln -sfn'

mkdir -p ${LLVM_DIR}/include/json
${SYM_LINK} ${REPO_ROOT}/llvm/json-forwards.h ${LLVM_DIR}/include/json/json-forwards.h
${SYM_LINK} ${REPO_ROOT}/llvm/json.h ${LLVM_DIR}/include/json/json.h
${SYM_LINK} ${REPO_ROOT}/llvm/InitializePasses.h ${LLVM_DIR}/include/llvm/InitializePasses.h
${SYM_LINK} ${REPO_ROOT}/llvm/LinkAllPasses.h ${LLVM_DIR}/include/llvm/LinkAllPasses.h
${SYM_LINK} ${REPO_ROOT}/llvm/Instrumentation.h ${LLVM_DIR}/include/llvm/Transforms/Instrumentation.h
${SYM_LINK} ${REPO_ROOT}/llvm/LTOCodeGenerator.cpp ${LLVM_DIR}/lib/LTO/LTOCodeGenerator.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/lib-Support-CMakeLists.txt ${LLVM_DIR}/lib/Support/CMakeLists.txt
${SYM_LINK} ${REPO_ROOT}/llvm/jsoncpp.cpp ${LLVM_DIR}/lib/Support/jsoncpp.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/lib-Target-Arm-CMakeLists.txt ${LLVM_DIR}/lib/Target/ARM/CMakeLists.txt
${SYM_LINK} ${REPO_ROOT}/llvm/PassManagerBuilder.cpp ${LLVM_DIR}/lib/Transforms/IPO/PassManagerBuilder.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/lib-Transforms-Utils-CMakeLists.txt ${LLVM_DIR}/lib/Transforms/Utils/CMakeLists.txt
${SYM_LINK} ${REPO_ROOT}/llvm/HexboxAnalysis.cpp ${LLVM_DIR}/lib/Transforms/Utils/HexboxAnalysis.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/ExperimentAnalysis.cpp ${LLVM_DIR}/lib/Transforms/Utils/ExperimentAnalysis.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/HexboxApplication.cpp ${LLVM_DIR}/lib/Transforms/Utils/HexboxApplication.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/Utils.cpp ${LLVM_DIR}/lib/Transforms/Utils/Utils.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/Function.cpp ${LLVM_DIR}/lib/IR/Function.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/Function.h ${LLVM_DIR}/include/llvm/IR/Function.h

# Hexbox Alias Analysis
${SYM_LINK} ${REPO_ROOT}/llvm/lib-Analysis-CMakeLists.txt ${LLVM_DIR}/lib/Analysis/CMakeLists.txt


# Backend
${SYM_LINK} ${REPO_ROOT}/llvm/ARMInstrThumb.td ${LLVM_DIR}/lib/Target/ARM/ARMInstrThumb.td
${SYM_LINK} ${REPO_ROOT}/llvm/ARMInstrInfo.td ${LLVM_DIR}/lib/Target/ARM/ARMInstrInfo.td
${SYM_LINK} ${REPO_ROOT}/llvm/ARMISelLowering.cpp ${LLVM_DIR}/lib/Target/ARM/ARMISelLowering.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/ARMISelLowering.h ${LLVM_DIR}/lib/Target/ARM/ARMISelLowering.h
${SYM_LINK} ${REPO_ROOT}/llvm/ARM.h ${LLVM_DIR}/lib/Target/ARM/ARM.h
${SYM_LINK} ${REPO_ROOT}/llvm/ARMTargetMachine.cpp ${LLVM_DIR}/lib/Target/ARM/ARMTargetMachine.cpp
${SYM_LINK} ${REPO_ROOT}/llvm/MCExperimentPrinter.cpp ${LLVM_DIR}/lib/Target/ARM/MCExperimentPrinter.cpp
#${SYM_LINK} ${REPO_ROOT}/llvm/ARMExpandPseudoInsts.cpp ${LLVM_DIR}/lib/Target/ARM/ARMExpandPseudoInsts.cpp

#IR

${SYM_LINK} ${REPO_ROOT}/llvm/Instructions.h ${LLVM_DIR}/include/llvm/IR/Instructions.h
${SYM_LINK} ${REPO_ROOT}/llvm/SelectionDAGBuilder.cpp ${LLVM_DIR}/lib/CodeGen/SelectionDAG/SelectionDAGBuilder.cpp
