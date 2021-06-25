
from Debugger.modules.typecheck import *

# This import moves around based on the Debugger version being used
try:
	import Debugger.modules.debugger.adapter as adapter
except:
	import Debugger.modules.adapters.adapter as adapter

from os.path import abspath, join, dirname
from shutil import which
import platform
import socket
import os

from .util import debugpy_path, ATTACH_TEMPLATE, log as custom_log

import sublime

adapter_type = 'MayaUI'


class MayaUI(adapter.AdapterConfiguration):

	@property
	def type(self): return adapter_type

	async def start(self, log, configuration):
		"""
		start() is called when the play button is pressed in the debugger.
		
		The configuration is passed in, allowing you to get necessary settings
		to use when setting up the adapter as it starts up (such as getting the 
		desired host/port to connect to, show below)

		The configuration will be chosen by the user from the 
		configuration_snippets function below, and its contents are the contents 
		of "body:". However, the user can change the configurations manually so 
		make sure to account for unexpected changes. 
		"""

		# First check for the environment variable
		package_path = abspath(join(dirname(__file__), '..'))
		adapter_path = join(package_path, "adapter")

		module_path = join(adapter_path, 'resources', 'module')
		separator = ';' if platform.system() == 'Windows' else ':'

		if 'MAYA_MODULE_PATH' not in os.environ or module_path not in os.environ['MAYA_MODULE_PATH']:
			sublime.message_dialog(
				"The MAYA_MODULE_PATH environment variable was not found. "
				"Please create/modify it to contain\n\n \"{0}\" \n\n"
				"then restart both Maya and Sublime Text.".format(module_path + separator)
			)
			return adapter.SocketTransport(log, "0.0.0.0", 0)

		# Start by finding the python installation on the system
		python = configuration.get("pythonPath")

		if not python:
			if which("python3"):
				python = "python3"
			elif not (python := which("python")):
				raise Exception('No python installation found')
		
		custom_log(f"Found python install: {python}")
		
		# Get host/port from config
		host = configuration['host']
		if host == 'localhost':
			host = '127.0.0.1'
		port = int(configuration['port'])
		
		# Format the attach code with the config information
		attach_code = ATTACH_TEMPLATE.format(
			debugpy_path=debugpy_path,
			hostname=host,
			port=port,
			interpreter=python,
			log_dir=abspath(join(dirname(__file__), 'python', 'logs')),
		)

		# Create a socket and connect to server in Houdini
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.connect(("localhost", 8890))

		# Send the code directly to the server and close the socket
		client.send(attach_code.encode("UTF-8"))
		client.close()

		custom_log(f"Sent attach code:\n\n {attach_code}")

		custom_log(f"Connecting to {host}:{str(port)}")
		
		return adapter.SocketTransport(log, host, port)

	async def install(self, log): 
		package_path = abspath(join(dirname(__file__), '..'))
		adapter_path = join(package_path, "adapter")

		module_path = join(adapter_path, 'resources', 'module')
		separator = ';' if platform.system() == 'Windows' else ':'

		if 'MAYA_MODULE_PATH' not in os.environ or module_path not in os.environ['MAYA_MODULE_PATH']:
			sublime.message_dialog(
				"Thanks for installing the Maya UI debug adapter!\n"
				"Because this is your first time using the adapter, a one-time "
				"setup must be performed: Please create or modify the "
				"MAYA_MODULE_PATH environment variable to contain\n\n \"{0}\" \n\n"
				"then restart both Maya and Sublime Text.".format(module_path + separator)
			)

	@property
	def installed_version(self) -> Optional[str]:
		# The version is only used for display in the UI
		return '0.0.1'

	@property
	def configuration_snippets(self) -> Optional[list]:
		# You can have several configurations here depending on your adapter's offered functionalities,
		# but they all need a "label", "description", and "body"
		return [
			{
				"label": "Maya: Custom UI Debugging",
				"description": "Debug Custom UI Components/Functions in Maya",
				"body": {
					"name": "Maya: Custom UI Debugging",
					"type": adapter_type,
					"request": "attach",  # can only be attach or launch
					"pythonPath": "",
					"host": "localhost",
					"port": 7005,
				}
			},
		]

	@property
	def configuration_schema(self) -> Optional[dict]:
		return None

	async def configuration_resolve(self, configuration):
		return configuration
