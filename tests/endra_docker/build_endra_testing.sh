#!/bin/bash
# Get the directory of this script
work_dir="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
# change to root directory of the Brenthy repo
cd $work_dir/../..

rsync -XAva ../WalIdentity tests/endra_docker/python_packages/
rsync -XAva ../Mutablock tests/endra_docker/python_packages/
rsync -XAva ../PrivateBlocks tests/endra_docker/python_packages/
rsync -XAva ../../MultiCrypt tests/endra_docker/python_packages/
rsync -XAva ../../Brenthy/Brenthy/blockchains/Walytis_Beta tests/endra_docker/python_packages/

docker build -t local/endra_testing -f tests/endra_docker/endra_testing.dockerfile .

## Run with:
# docker run -it --privileged local/endra_testing