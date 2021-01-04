#!/bin/sh

set -x

echo "Running database insert"
echo `date`

module load anaconda5
source activate cpra-web-portal
python /opt/repositories/cpra-web-portal/scripts/database_insert.py