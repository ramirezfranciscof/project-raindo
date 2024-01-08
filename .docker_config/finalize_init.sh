#!/bin/bash
set -em

echo $(date -u) > /opt/INIT_COMPLETED

jupyter-lab --ip=0.0.0.0 --no-browser --allow-root
