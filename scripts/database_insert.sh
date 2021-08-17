#!/bin/sh

set -x

echo "Running database insert"
echo `date`

module load anaconda3
source activate /opt/environments/cpra-web-portal
cd /opt/repositories/cpra-web-portal
python scripts/database_insert.py