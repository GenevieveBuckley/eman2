#!/bin/bash

set -xe

build_dir="${SRC_DIR}/../build_eman"

rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

cmake --version
if [[ ${HOST} =~ .*linux.* ]]; then
    cmake $SRC_DIR -DCMAKE_TOOLCHAIN_FILE="${RECIPE_DIR}/cross-linux.cmake" -DENABLE_OPTIMIZE_COMPATIBILITY=ON
else
    cmake $SRC_DIR
fi

make -j${CPU_COUNT}
make install
