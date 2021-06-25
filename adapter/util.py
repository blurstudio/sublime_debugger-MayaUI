
from os.path import abspath, join, dirname, basename, split
from datetime import datetime
from threading import Thread
import json
import sys

# Import correct Queue
if (sys.version_info[0] == 3):
    from queue import Queue
else:  # Python 2
    from multiprocessing import Queue

#  Debugging this adapter
debug = True
log_file = abspath(join(dirname(__file__), 'log.txt'))

if debug:
    open(log_file, 'w+').close()  # Creates and/or clears the file

debugpy_path = join(abspath(dirname(__file__)), "python")


# --- Utility functions --- #

def log(msg, json_msg=None):
    if debug:

        if json_msg:
            msg += '\n' + json.dumps(json.loads(json_msg), indent=4)

        with open(log_file, 'a+') as f:
            f.write('\n' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " - " + msg + '\n')


def run(func, args=()):
    Thread(target=func, args=args).start()


# --- Resources --- #

# Own constants
ATTACH_TEMPLATE = """
import sys
debugpy_module = r"{debugpy_path}"
if debugpy_module not in sys.path:
    sys.path.insert(0, debugpy_module)

# import debugpy
import ptvsd

try:
    # debugpy.configure(python=r"{interpreter}")
    # debugpy.listen(("{hostname}",{port}))
    ptvsd.enable_attach(address=("{hostname}",{port}))
except Exception as e:
    sys.stderr.write("\\n\\nAn error occurred while trying to connect to Sublime Text 4:\\n" + str(e))
else:
    sys.stderr.write("\\n\\nConnection to Sublime Debugger is active.\\n\\n")
"""

CONTENT_HEADER = "Content-Length: "

INITIALIZE_RESPONSE = """{
    "request_seq": 1,
    "body": {
        "supportsModulesRequest": true,
        "supportsConfigurationDoneRequest": true,
        "supportsDelayedStackTraceLoading": true,
        "supportsDebuggerProperties": true,
        "supportsEvaluateForHovers": true,
        "supportsSetExpression": true,
        "supportsGotoTargetsRequest": true,
        "supportsExceptionOptions": true,
        "exceptionBreakpointFilters": [
            {
                "filter": "raised",
                "default": false,
                "label": "Raised Exceptions"
            },
            {
                "filter": "uncaught",
                "default": true,
                "label": "Uncaught Exceptions"
            }
        ],
        "supportsCompletionsRequest": true,
        "supportsExceptionInfoRequest": true,
        "supportsLogPoints": true,
        "supportsValueFormattingOptions": true,
        "supportsHitConditionalBreakpoints": true,
        "supportsSetVariable": true,
        "supportTerminateDebuggee": true,
        "supportsConditionalBreakpoints": true
    },
    "seq": 1,
    "success": true,
    "command": "initialize",
    "message": "",
    "type": "response"
}"""

ATTACH_ARGS = """{{
    "name": "Nuke Python Debugger : Remote Attach",
    "type": "python",
    "request": "attach",
    "port": {port},
    "host": "{hostname}",
    "pathMappings": [
        {{
            "localRoot": "{dir}",
            "remoteRoot": "{dir}"
        }}
    ]
}}"""

PAUSE_REQUEST = """{{
    "command": "pause",
    "arguments": {{
        "threadId": 1
    }},
    "seq": {seq},
    "type": "request"
}}"""

# DISCONNECT_RESPONSE = """{{
#     "request_seq": {req_seq},
#     "body": {{}},
#     "seq": {seq},
#     "success": true,
#     "command": "disconnect",
#     "message": "",
#     "type": "response"
# }}"""

