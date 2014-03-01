""" @package hwm.hardware.devices.drivers.driver
This module defines the base driver classes available to Mercury2. Namely, the HardwareDriver and VirtualDriver classes
which are used to represent physical and virtual devices.
"""

# Import required modules
import logging, threading, time

class Driver(object):
  """ Provides the base driver class interface.
  
  This class provides the interface that all Mercury2 device drivers must use. It defines several functions common to 
  both virtual and physical devices as well as abstract methods that derived drivers must implement.

  @note Individual driver classes should inherit from either HardwareDriver or VirtualDriver, not this class.
  """
  
  def __init__(self, device_configuration, command_parser):
    """ Initializes the new device driver.

    @note Derived drivers should always call this method using super() as it sets several required attributes.
    
    @param device_configuration  A dictionary containing the device configuration (from the devices.yml configuration
                                 file).
    @param command_parser        A reference to the active CommandParser instance. Drivers may use this to execute
                                 commands during a session.
    """
    
    # Set driver attributes
    self.settings = {} if 'settings' not in device_configuration else device_configuration['settings']
    self.configuration = device_configuration
    self.id = self.configuration['id']
    self.allow_concurrent_use = (False if ('allow_concurrent_use' not in self.configuration) else 
                                 self.configuration['allow_concurrent_use'])
    self.associated_pipelines = {}
    self._command_handler = None
    self._command_parser = command_parser

    # Private attributes
    self._use_count = 0
    self._locked = False

  def write_telemetry(self, stream, telemetry_datum, binary=False, **extra_headers):
    """ Writes device telemetry data back to the device's registered pipelines.
    
    This method writes the specified telemetry datum back to the device's registered pipelines that are currently
    in use. The pipelines will then pass the telemetry datum along to their sessions, which will in turn send it to 
    their connected users.

    @note Device state (generated by the get_state() method) is considered standard telemetry and is automatically 
          collected by the device's pipelines. Device drivers should not manually report the state returned by 
          get_state() using this method. 
    @note Occasionally, a pipeline's telemetry stream may be throttled to relieve excess network load. Because telemetry
          data is tied to a timestamp, any telemetry data that the pipeline receives when it is being throttled will be
          discarded. Therefore, it can not be assumed that all data passed to this function will make it to the end 
          user.

    @param stream           A string identifying which of the device's telemetry streams the datum should be associated 
                            with. The user interface will use this to group telemetry data as it flows in and build an 
                            appropriate display for it.
    @param telemetry_datum  The actual telemetry datum. Can take many forms (e.g. a dictionary or binary webcam image).
    @param binary           Whether or not the telemetry payload consists of binary data. If set to true, the data will
                            be encoded before being sent to the user.
    @param **extra_headers  A dictionary containing extra keyword arguments that should be included as additional
                            parameters when sending the telemetry datum.
    """

    # Write the telemetry datum to the device's active pipelines
    for temp_pipeline in self.associated_pipelines:
      if self.associated_pipelines[temp_pipeline].is_active:
        self.associated_pipelines[temp_pipeline].write_telemetry(self.id, stream, int(time.time()), telemetry_datum,
                                                                 binary=binary, **extra_headers)

  def write_output(self, output_data):
    """ Writes device output to the device's pipelines.
    
    This method writes the specified data chunk to every active pipeline registered to this device that specifies it
    as it's output device.

    @note It is important to only write device output to active pipelines that specify this device as it's output
          device. Every device driver should use this method to write their output stream to the pipeline unless it has 
          a specific reason not to.
    """

    # Write the data to each active pipeline that specifies this device as its output device
    for temp_pipeline in self.associated_pipelines:
      if self.associated_pipelines[temp_pipeline].is_active:
        if self is self.associated_pipelines[temp_pipeline].output_device:
          self.associated_pipelines[temp_pipeline].write_output(output_data)
  
  def write(self, input_data):
    """ Writes the specified data chunk to the device.

    This method receives device input data from the pipeline. The default implementation of this method simply discards
    the data. Device drivers that can handle an input data stream (such as a radio) should pass this data to its
    associated device.

    @param input_data  A data chunk of arbitrary size containing data that should be fed to the device.
    """

    return

  def get_command_handler(self):
    """ Returns the device's command handler.

    This method returns the device's command handler. Individual device drivers are responsible for defining and 
    initializing their command handler, as well as assigning it to their driver's "command_handler" attribute.

    @throw Raises CommandHandlerNotDefined if the device driver does not specify a command handler.
    
    @return Returns the driver's command handler.
    """

    if self._command_handler is None:
      raise CommandHandlerNotDefined("The '"+self.id+"' device does not specify a command handler.")

    return self._command_handler

  def get_state(self):
    """ Returns a dictionary containing the current state of the device.

    This method should return a dictionary containing all available/important state for this device. Any Pipeline using
    the device will use this to assemble a real time stream of pipeline telemetry.

    @throw Throws StateNotDefined if no state is available for a given device. This can happen if you forget to override
           this method or if the device genuinely doesn't have any state.

    @return Should return a dictionary containing the device's current state. 
    """

    raise StateNotDefined("The '"+self.id+"' device did not specify any device state.")

  def cleanup_after_session(self):
    """ Allows the driver to cleanup after a session that was using it has ended.

    This method is called during the session cleanup process and provides the driver with an opportunity to cleanup 
    after a session by, for example:
    * Stopping any services that it may offer
    * Stopping device telemetry and data streams

    @note Drivers that allow for concurrent access may be used by multiple pipelines at a time. If this driver allows 
          for concurrent access, it is important to check the driver's _use_count attribute before deciding to terminate 
          services.
    @note If the driver cleanup process involves any asynchronous action (such as a command) a deferred should be 
          returned so that the session coordinator can log the results.
    """

    return

  def prepare_for_session(self, session_pipeline):
    """ Allows the driver to prepare for new sessions.

    This method gives the driver a chance to perform any needed setup actions before a new session on the specified 
    pipeline starts. For example, it could use this callback to load its required services from the pipeline and prepare
    for use any services that it may offer.
    
    @throw Any exceptions thrown in this method will cause a session-fatal error.

    @note This method is called during the session setup process because the services offered by the device's active 
          pipeline may change with each session. It is called after the pipeline sets its active services for the new 
          session but before the pipeline and session setup commands are executed.
    @note The device shouldn't register its services with the pipeline during this step, that occurs once during the
          pipeline/driver initialization process (via the self._register_services() callback).

    @param session_pipeline  The pipeline being used by the session. This can also be found in 
                             self.associated_pipelines.
    """

    return

  def register_pipeline(self, pipeline):
    """ Associates a pipeline with the device.

    This method registers the specified pipeline with the device. This allows the device driver to use the pipeline to 
    pass along device output, register and load services, and write to the pipeline telemetry stream.

    @note This method allows multiple pipelines to be registered with the device. This is because devices can belong to
          several pipelines at a time. In addition, some devices (such as webcams) allow for concurrent use by multiple 
          pipelines.
    @note Device registration occurs automatically during the initial pipeline setup process and only occurs once.
    @note This method calls another method, self._register_services(), that provides drivers with the opportunity to
          register their services with the new pipeline. 
    
    @throws Raises PipelineAlreadyRegistered in the event that the user tries to register the same pipeline twice with
            the device.

    @param pipeline  The Pipeline to register with the device.
    """

    # Make sure the pipeline hasn't been registered yet
    if pipeline.id in self.associated_pipelines:
      raise PipelineAlreadyRegistered("The '"+pipeline.id+"' pipeline has already been registered with the '"+self.id+
                                      "' device.")

    # Register the pipeline
    self.associated_pipelines[pipeline.id] = pipeline

    # Call the service registration callback
    self._register_services(pipeline)

  def reserve_device(self):
    """ Reserves the device for a pipeline usage session.

    This method tries to acquire the device lock and raises an exception if it can't. However, if the device is
    configured for concurrent access it will simply increment the use counter and return.
    
    @note Pipelines will typically use this method to reserve their constituent devices when a session begins. This will
          prevent two different pipelines from accidentally using the same device at the same time. If the device is 
          configured to allow concurrent access, pipelines will always be able to reserve the device. 
    
    @throw Throws DeviceInUse if the device has already been reserved by another pipeline.
    """
    
    # Check if the device allows concurrent use
    if not self.allow_concurrent_use:
      # Check if the device is currently reserved
      if self.is_locked:
        raise DeviceInUse("The requested device has already been reserved and can't be used again until it has been "+
                          "freed.")

      self._locked = True

    self._use_count += 1;
  
  def free_device(self):
    """ Frees up the driver reservation.

    This method frees the driver for use by other pipelines. If the driver is configured for concurrent access, then
    this method will just decrement the usage count.
    
    @note Any pipelines that are currently using this driver will automatically call this method during the session 
          cleanup process.
    """
    
    # Un-reserve the device if it does not allow for concurrent access
    if not self.allow_concurrent_use:
      self._locked = False

    self._use_count = 0 if (self._use_count-1 < 0) else (self._use_count-1) 

  def _register_services(self, pipeline):
    """ Allows the driver to register any services that it may provide with its pipelines.
    
    This callback is called whenever a new pipeline is registered with the driver and gives the driver an opportunity to 
    register any services that it may offer with the pipeline.

    @param pipeline  A pipeline that was just registered with the device.
    """

    return

  @property
  def is_active(self):
    """ Indicates if the driver is active or not.

    This method is used to determine if the driver is active or not. That is to say, if it is currently being used by 
    any pipeline. 
    
    @note Even if a driver has many pipelines registered with it, it may not be active. A driver is considered active 
          when at least one of its pipelines is active (i.e. being used by a session).

    @return Returns True if the driver is active (in use), and False otherwise.
    """ 

    if self._use_count != 0:
      return True

    return False

  @property
  def is_locked(self):
    """ Indicates if the driver has been locked or not.

    This property is used to determine if the driver is currently locked or not. A driver is "locked" if a pipeline 
    has successfully called Driver.lock_device() on it and if it does not allow for concurrent access. When a driver is 
    locked, other pipelines won't be able to use the device.

    @note Devices configured for concurrent access can not be locked because, by definition, they can always be accessed
          by multiple pipelines at the same time. If you wish to check if a driver is actively being used by any 
          pipeline, use Driver.is_active().
    
    @return Returns True if the driver has been locked and False otherwise.
    """

    return self._locked

class HardwareDriver(Driver):
  """ The base hardware driver interface.

  This class provides the base driver interface that must be implemented when developing physical hardware device
  drivers for the hardware manager.
  """

  def __init__(self, device_configuration, command_parser):
    """ Sets up the physical hardware driver.

    @param device_configuration  A dictionary containing the device configuration (from the devices.yml configuration
                                 file).
    @param command_parser        A reference to the active CommandParser instance. Drivers may use this to execute
                                 commands at any time during a session.
    """

    # Call the base driver constructor
    super(HardwareDriver,self).__init__(device_configuration, command_parser)

class VirtualDriver(Driver):
  """ Defines the base driver used for virtual devices.
  """

  def __init__(self, device_configuration, command_parser):
    """ Sets up the virtual device driver.

    @param device_configuration  A dictionary containing the device configuration (from the devices.yml configuration
                                 file).
    @param command_parser        A reference to the active CommandParser instance. Drivers may use this to execute
                                 commands at any time during a session.
    """

    # Call the base driver constructor
    super(VirtualDriver,self).__init__(device_configuration, command_parser)

# Define custom driver exceptions
class DriverError(Exception):
  pass
class PipelineAlreadyRegistered(DriverError):
  pass
class PipelineNotRegistered(DriverError):
  pass
class StateNotDefined(DriverError):
  pass
class CommandHandlerNotDefined(DriverError):
  pass
class DeviceInUse(DriverError):
  pass
  