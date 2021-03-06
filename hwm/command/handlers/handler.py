""" @package hwm.command.handlers.handler
Contains the base command handler interfaces and abstract classes that all system and device command handlers should
implement.
"""

class CommandHandler(object):
  """ The base command handler interface.

  This class defines the base command handler interface that all system and device command handlers should extend.
  Command handlers are responsible for responding to commands that control the behavior of the hardware manager. These 
  commands can be submitted manually by users during their reservations, or automatically in the case of pipeline and 
  session setup commands (which both run before any session begins).

  Every command response method is prefixed with "command_" and will be called by the command parser when it receives a
  raw command request for that command. Command methods can also have a sibling "settings_" method which returns a 
  standardized dictionary containing information about the command such as what parameters it accepts. The user
  interface uses this command metadata to keep track of what commands are available and to build appropriate forms for 
  each command. If a command does not define a "settings_" method, it will not be included in the user interface.

  For system commands that require an active session, the individual command methods must perform any necessary 
  validations on the session to determine if the command should be executed. For device commands that require an active 
  session, the command parser will ensure that the command method only gets called if the user has an active session 
  with a pipeline that contains that hardware device (although the Session reference will still be passed to the
  command method to allow for additional checks if needed).

  @note Commands will be executed asynchronously and, as a result, must not block. If one of the handler's commands 
        needs to make a blocking system call (such as querying a network device), it should use defer.deferToThread to 
        make the action non-blocking and return a deferred that will eventually be fired with the command results.
    
  @note The rationale behind specifying the command meta-data at this level is so that command handlers (system or 
  	    device) can be developed and installed without requiring any changes to the user interface (unless you want 
  	    custom command forms). 
  """

  def __init__(self, command_handler_name):
    """ Initializes the command handler.
    
    This constructor initializes the command handler by setting some common attributes.

    @param command_handler_name  The name of the command handler. If the command handler is a system level command 
                                 handler, this will be the destination for this handler's commands.
    """

    # Set the command handler attributes
    self.name = command_handler_name

class DeviceCommandHandler(CommandHandler):
  """ The base interface class for device command handlers.
  
  This class defines the base command handler interface for device command handlers. Device command handlers differ from
  system command handlers in that they provide command response methods for a single physical or virtual device. 
  """

  def __init__(self, driver):
    """ Sets up the device command handler.

    @param driver  The Driver instance that offers this command handler.
    """

    # Set the command handler attributes
    self.name = driver.id 
    self.driver = driver
