""" @package hwm.network.command.parser
Parses system and hardware commands and passes them to the appropriate command handler.

This module contains a class that validates, parses, and delegates ground station commands to the appropriate handler 
as they're received. Once a command has been executed, it returns the results of the command.
"""

# Import required modules
import time, logging
from twisted.internet import defer, threads
from hwm.network.command import command

class CommandParser:
  """ Processes all commands received by the hardware manager.
  
  This class parses and performs validations on received commands, delegating them to the appropriate handler when
  appropriate.
  """
  
  def __init__(self, system_command_handler):
    """ Sets up the command parser instance.
    
    @param system_command_handler  A reference to the command handler that is responsible for handling system commands 
                                   (i.e. commands not addressed to a specific device).
    """
    
    # Set the class attributes
    self.system_handler = system_command_handler

  def parse_command(self, raw_command, request = None):
    """ Processes all commands received by the ground station.
    
    When a raw JSON command is passed to this function, it performs the following operations using a series of callbacks:
    * Validates command schema
    * Verifies that the command is valid (exists)
    * Checks that the user can execute the command
    * Executes the command in a new thread
    * Returns a deferred that will be fired with the results of the command
    
    @note In the event of an error with the command (e.g. invalid json or permission error), the error will be logged
          and an error response will be returned ready for transmission.
    @note Even if the command generates an error response, the returned deferred's callback chain will be called with
          the contents of the error (instead of the errback chain). 
    @note The callback chain from the deferred returned from this function will return a dictionary representing the 
          results of the command. The 'request' key will provide a reference to the HTTP request associated with the 
          command. The 'response' key will contain a JSON string with the results of the command.
    
    @param raw_command  A raw JSON string containing metadata about the command.
    @param request      The request object associated with the command, if any.
    @return Returns the results of the command (in JSON) using a deferred. May be the output of the command or an error 
            message.
    """
    
    time_command_received = time.time()
    new_command = None
    
    # Create the new command
    new_command = command.Command(request, time_command_received, raw_command)
    
    # Asynchronously validate the command (format and schema)
    validation_deferred = new_command.validate_command()
    
    # Add callbacks to handle validation results (_command_error added second so it can handle errors from _run_command)
    validation_deferred.addCallback(self._run_command, new_command)
    validation_deferred.addErrback(self._command_error, new_command)
    
    return validation_deferred
  
  def _run_command(self, validation_results, valid_command):
    """ Continues executing a command after it has been validated.
    
    This callback continues to validate and execute a command after it has passed preliminary format and schema 
    validations. 
    
    @note This callback returns a deferred which means that the parent deferred's callback chain will pause until the 
          returned deferred has been fired. This returned deferred's callbacks will then execute before the remaining 
          callbacks on the parent deferred.
    @note The actual command execution occurs in a new thread. Make sure that command code is thread safe!
    
    @throw This callback may throw several exceptions indicating errors about the command. These exceptions will 
           automatically be picked up by the errback chain on the parent deferred.
    
    @param validation_results  The validation results. Always true (because this is a callback and not an errback).
    @param valid_command       The Command object being executed.
    @return Returns a deferred that will eventually be fired with the results of executing the command in the 
            command handler.
    """
    
    # Pick a command handler
    if valid_command.device_id:
      print 'LOAD DEVICE COMMAND HANDLER'
    else:
      command_handler = self.system_handler
    
    # Verify that the command exists
    if not hasattr(command_handler, 'command_'+valid_command.command):
      if valid_command.device_id:
        handler_string = "'"+valid_command.device_id+"' device"
      else:
        handler_string = "system"
      
      raise command.CommandError("The received command could not be located in the "+handler_string+" command handler.", {"invalid_command": valid_command.command})
    
    # Check the user permissions
    # todo
    
    # Execute the command in a new thread
    command_deferred = threads.deferToThread(getattr(command_handler, 'command_'+valid_command.command), valid_command)
    command_deferred.addCallback(self._command_complete, valid_command)
    command_deferred.addErrback(self._command_error, valid_command) # Is this necessary or will it get picked up by parent?
    
    return command_deferred
  
  def _command_complete(self, command_results, successful_command):
    """ Builds a complete response for the successful command.
    
    This callback generates a successful command response. It is called after the command has been executed in a new
    thread. 
    
    @param command_results    A dictionary containing additional data to embed with the command response (in the
                              "result" field of the JSON response). This is returned by the individual command functions
                              in the command handlers.
    @param successful_command  The command that just completed.
    @return Returns the constructed command response dictionary. This dictionary is fed into following callbacks.
    """
    
    command_response = successful_command.build_command_response(True, command_results)
    
    return command_response
  
  def _command_error(self, failure, failed_command):
    """ Generates an appropriate error response for the failure.
    
    This errback generates an error response for the indicated failure, which it then returns (thus passing the request
    to the callback chain of the deferred returned from parse_command). If the failure is wrapping an exception of type
    CommandError then it may contain a dictionary with additional information about the error.
    
    @param failure         The Failure object representing the error.
    @param failed_command  The Command object of the failed command.
    @return Returns a dictionary containing information about the request.
    """
    
    # Set the error message
    error_message = {
      "error_message": str(failure.value)
    }
    
    # Check if there are any extra error parameters
    if hasattr(failure.value, 'error_parameters'):
      # Merge the parameter dictionaries
      error_results = dict(failure.value.error_parameters.items() + error_message.items())
    else:
      error_results = error_message
    
    # Build the response
    error_response = failed_command.build_command_response(False, error_results)
    
    # Log the error
    if failed_command.command:
      logging.error("A command ("+failed_command.command+") failed for the following reason: "+str(failure.value))
    else:
      logging.error("A command has failed for the following reason: "+str(failure.value))
    
    # Return the error response dictionary back into the callback chain
    return error_response