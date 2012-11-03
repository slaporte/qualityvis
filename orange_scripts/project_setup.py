"""
Load this into a Python Script widget (does not have
to be connected to any other widgets), and set the 
project directory to the location of the git repo.

Hit execute and enjoy!
"""
PROJECT_DIR = '/home/mahmoud/work/qualityvis'

import sys
sys.path.append(PROJECT_DIR)
sys.path.append(PROJECT_DIR+'/orange_scripts')