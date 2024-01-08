#!/bin/bash

# Virtual env wrapper
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
export WORKON_HOME=$HOME/.virtualenvs
export PROJECT_HOME=$HOME/projects
source /usr/local/bin/virtualenvwrapper.sh

# Bash completion
source /etc/profile.d/bash_completion.sh 

# Activate virtual environment
source /root/.virtualenvs/workenv/bin/activate
