# To Test:
# - Resource: Send simply successful command (e.g. system time)
# - Resource: POST command and analyze response (submit error command, so doesn't depend on handler)
# - Parser: Send command with invalid device ID (no device)

# Import required modules
import logging, time, json
from pkg_resources import Requirement, resource_filename
from twisted.trial import unittest
from twisted.test import proto_helpers
from hwm.core.configuration import *
from hwm.network.command import parser, command, connection
from hwm.network.command.handlers import system as command_handler

class TestCommandInfrastructure(unittest.TestCase):
  """ This test suite tests the functionality of the command parser (CommandParser), Command class, and command Resource
  individually and holistically. The functionality of individual commands (including system commands) is tested in the
  test suite for the appropriate command handler.
  """
  
  def setUp(self):
    # Set a local reference to Configuration (how other modules should typically access Config)
    self.config = Configuration
    self.config.verbose_startup = False
    
    # Set the source data directory
    self.source_data_directory = resource_filename(Requirement.parse("Mercury2HWM"),"hwm")
    
    # Disable logging for most events
    logging.disable(logging.CRITICAL)
  
    # Initialize the command parser with the system command handler
    self.command_parser = parser.CommandParser(command_handler.SystemCommandHandler())
  
    # Create a new Site factory
    #self.command_factory_test = DummySite(command_connection.CommandResource(self.command_parser))
    
    #self.protocol.rawDataReceived('TEST DATA RECEIVED')
    #self.assertEqual(self.transport.value(), 'test')
  
  def tearDown(self):
    # Reset the recorded configuration values
    self.config.options = {}
    self.config.user_options = {}
    
    # Reset the object references
    self.config = None
    self.command_parser = None
  
  def test_parser_unrecognized_command(self):
    """ This test ensures that the command parser correctly rejects unrecognized commands. In addition, it verifies the 
    functionality of the optional CommandError exception which allows additional meta-data to be embedded with the 
    error.
    """
    
    # Define a callback to test the parser results
    def parsing_complete(command_results):
      json_response = json.loads(command_results['response'])
      
      self.assertEqual(json_response['status'], 'error', 'The parser did not return an error response.')
      self.assertEqual(json_response['result']['invalid_command'], 'nonexistent_command', 'The error response returned by the parser was incorrect (did not contain \'invalid_command\' field).')
    
    # Send an unrecognized command the to parser
    test_deferred = self.command_parser.parse_command("{\"command\":\"nonexistent_command\",\"parameters\":{\"test_parameter\":5}}")
    test_deferred.addCallback(parsing_complete)
    
    return test_deferred
  
  def test_parser_malformed(self):
    """ This test verifies that CommandParser correctly returns an error response when a malformed command is submitted 
    to it.
    """
    
    # Define a callback to test the parser results
    def parsing_complete(command_results):
      json_response = json.loads(command_results['response'])
      
      self.assertEqual(json_response['status'], 'error', 'The parser did not return an error response.')
      self.assertNotEqual(json_response['result']['error_message'].find('malformed'), -1, 'The parser did not return the correct error response (response did not contain \'malformed\').')
    
    # Send a malformed command the to parser
    test_deferred = self.command_parser.parse_command("{\"invalid_json\":true,invalid_element}")
    test_deferred.addCallback(parsing_complete)
    
    return test_deferred
  
  def test_parser_invalid_schema(self):
    """ This test verifies that CommandParser correctly returns the correct error response when a malformed command is 
    submitted to it.
    """
    
    # Define a callback to test the parser results
    def parsing_complete(command_results):
      json_response = json.loads(command_results['response'])
      
      self.assertEqual(json_response['status'], 'error')
    
    # Parse a malformed command the to parser
    test_deferred = self.command_parser.parse_command("{\"invalid_json\":true,invalid_element}")
    test_deferred.addCallback(parsing_complete)
    
    return test_deferred
  
  def test_command_malformed(self):
    """ Verifies that the Command class validator correctly rejects malformed commands (i.e. commands that aren't valid
    JSON.
    """
    
    # Create a new malformed command
    test_command = command.Command(None, time.time(), "{\"invalid_json\":true,invalid_element}")
    
    test_deferred = test_command.validate_command()
    
    return self.assertFailure(test_deferred, command.CommandMalformed)
  
  def test_command_invalid_schema(self):
    """ Verifies that the Command class validator correctly rejects a command that does not conform to the JSON schema.
    """
    
    # Create a new malformed command
    test_command = command.Command(None, time.time(), "{\"message\": \"This schema is invalid\"}")
    
    test_deferred = test_command.validate_command()
    
    return self.assertFailure(test_deferred, command.CommandInvalidSchema)
  
  def test_command_valid_schema(self):
    """ This test verifies that the Command class correctly parses a valid schema and updates the Command attributes. In
    addition, it verifies that the build_command_response method works as intended. 
    """
    
    # Create a valid command
    test_command = command.Command(None, time.time(), "{\"command\":\"test_command\",\"parameters\":{\"test_parameter\":5}}")
    
    # Define a callback to verify the Command after validation is complete
    def validation_complete(validation_results):
      # Verify that the command attributes have correctly been saved in the Command attributes
      attribute_error_message = "One of the Command convenience attributes was incorrect."
      self.assertEqual(test_command.command, "test_command", attribute_error_message)
      self.assertEqual(test_command.device_id, None, attribute_error_message)
      self.assertEqual(test_command.parameters['test_parameter'], 5, attribute_error_message)
      
      # Build and test the command response
      response_error_message = "The generated command response was invalid."
      test_command_response = test_command.build_command_response(True, {"test_result": 10})
      self.assertEqual(test_command_response['request'], None, response_error_message)
      
      json_response = json.loads(test_command_response['response'])
      self.assertEqual(json_response['status'], 'okay', response_error_message)
      self.assertEqual(json_response['result']['test_result'], 10, response_error_message)
      self.assertNot('device_id' in json_response)
    
    test_deferred = test_command.validate_command()
    test_deferred.addCallback(validation_complete)
    
    return test_deferred