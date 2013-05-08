# Import required modules
import logging
from twisted.trial import unittest
from hwm.core.configuration import *
from hwm.hardware.devices import manager
from hwm.hardware.devices.drivers import driver
from pkg_resources import Requirement, resource_filename

class TestBaseDriver(unittest.TestCase):
  """ This test suite tests the functionality of the base driver class that all other drivers inherit from.
  """
  
  def setUp(self):
    # Set a local reference to Configuration (how other modules should typically access Config)
    self.config = Configuration
    self.config.verbose_startup = False
    
    # Set the source data directory
    self.source_data_directory = resource_filename(Requirement.parse("Mercury2HWM"),"hwm")
    
    # Disable logging for most events
    logging.disable(logging.CRITICAL)
  
  def tearDown(self):
    # Clear the configuration
    self._reset_config_entries()
    
    # Reset the configuration reference
    self.config = None
  
  def test_driver_locking(self):
    """ Tests the locking functionality of the base driver class.
    """
    
    # Load a valid device configuration
    self.config.read_configuration(self.source_data_directory+'/hardware/devices/tests/data/devices_configuration_valid.yml')
    device_manager = manager.DeviceManager()
    
    # Get a driver to test
    test_driver = device_manager.get_device_driver("test_device2")
    
    # Lock the driver
    test_driver.reserve_device()
    
    # Try to lock it again
    self.assertRaises(driver.DeviceInUse, test_driver.reserve_device)
    
    # Unlock and relock
    test_driver.free_device()
    test_driver.reserve_device()
  
  def _reset_config_entries(self):
    # Reset the recorded configuration entries
    self.config.options = {}
    self.config.user_options = {}