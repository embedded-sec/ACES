#!/bin/bash
#  Usage .build_final [record] [run]
set -x

HEXBOX_ROOT=$(readlink -f `dirname $0`/../..)
echo "Dir ${HEXBOX_ROOT}"

declare -a policies=("peripheral"
                "filename"
                "filename-no-opt"
                )

if [ $1 = "record" ]; then
    for p in "${policies[@]}"
    do
        arm-none-eabi-gdb-py --batch\
        -x ${HEXBOX_ROOT}/compiler/tools/gdb_scripts/gdb_record.py \
        bin/${APP_NAME}--${p}--mpu-8--hexbox--record.elf
    done
fi


for p in "${policies[@]}"
do
  python ${HEXBOX_ROOT}/compiler/graph_analysis/memory_reader.py \
     -m=mem_accesses_${APP_NAME}--$p--mpu-8--hexbox--record.bin\
     -b=bin/${APP_NAME}--$p--mpu-8--hexbox--record.elf \
     -d=.build/hexbox/hexbox-final-policy--$p--mpu-8.json \
     -f mem_accesses--$p--mpu-8.s
  make all HEXBOX_METHOD=$p >${p}--mpu-8_final.log 2>${p}--mpu-8_final.log
done


if [ $1 = "run" ] || [ $2 = "run" ]; then
    rm -rf timing_results/
    arm-none-eabi-gdb-py --batch\
    -x ${HEXBOX_ROOT}/compiler/tools/gdb_scripts/gdb_run.py \
    bin/${APP_NAME}--${policies[0]}--mpu-8--baseline.elf
    for p in "${policies[@]}"
    do
        arm-none-eabi-gdb-py --batch\
        -x ${HEXBOX_ROOT}/compiler/tools/gdb_scripts/gdb_run.py \
        bin/${APP_NAME}--${p}--mpu-8--hexbox--final.elf
    done
    echo "Num Timing Files:" `ls -1 timing_results/ | wc -l`
fi
