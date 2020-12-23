#!/bin/sh

set -X

echo "Running databaes insert"
echo `date`

module load anaconda5
source activate cpra-web-portal
python /opt/repostories/cpra-web-portal/database_insert.py