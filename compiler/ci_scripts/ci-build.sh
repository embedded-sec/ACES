# Needs to be run from root of repo
set -e
SCRIPT_DIR=`dirname \`readlink -f $0\``
mkdir -p ${SCRIPT_DIR}/../../llvm/build
cd ${SCRIPT_DIR}/../../llvm/build
${SCRIPT_DIR}/cmake_config.sh ../llvm-release_40 ../bins
ninja install
