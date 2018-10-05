#!/bin/bash
set -x

declare -a arr=("peripheral"
                "filename"
                "filename-no-opt"
                )


for i in "${arr[@]}"
do
  make all HEXBOX_METHOD=$i >$i_final.log 2>$i_final.log
done
