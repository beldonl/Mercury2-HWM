## Sets up the Mercury2 Hardware Manager
# 
# This script uses distribute (fork of setuptools) to install the hardware manager, and its dependencies, on the system.

# Install setuptools if not installed
import distribute_setup
distribute_setup.use_setuptools()

# Import the required packages
from setuptools import setup, find_packages
import glob

# Call the setup function
setup(
  # Project meta-data
  name = "Mercury2HWM",
  version = "1.0dev",
  author = "Michigan Exploration Laboratory",
  description = "The hardware manager component of the Mercury2 ground station administration system.",
  keywords = "mercury2 hardware manager mxl michigan university of michigan",
  url = "http://exploration.engin.umich.edu/",
  
  # Specify which packages to include
  packages = find_packages(),
  
  # Specify the script entry locations
  entry_points = {
    'console_scripts': [
      'HardwareManager = hwm.application.core.initialization:initialize'
    ]
  },

  # Declare dependencies
  install_requires = ['distribute',
                      'Twisted>=12.3.0',
                      'PyYAML>=3.10',
                      'pyOpenSSL>=0.13',
                      'doxypy>=0.4.2',
                      'jsonschema'],
  
  # Specify patterns for data files to include (will be copied to a user directory during installation)
  data_files = [
    ('data/config', glob.glob('data/config/*')),
    ('data/logs', glob.glob('data/logs/*')),
    ('data/schedules', glob.glob('data/schedules/*')),
    ('data/stream_dumps', glob.glob('data/stream_dumps/*'))
  ],
)
