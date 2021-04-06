
"""

This script creates a connection between the Debugger and Foundry's Maya for debugging Python 2.

"""

from util import (Queue, log, run, dirname, debugpy_path, join, split,
                  basename, ATTACH_TEMPLATE, ATTACH_ARGS, 
                  INITIALIZE_RESPONSE, CONTENT_HEADER)
from interface import DebuggerInterface
from tempfile import gettempdir
import socket
import json

interface = None

processed_seqs = []
attach_code = ""

debugpy_send_queue = Queue()
debugpy_socket = None


def main():
    """
    Initializes a python script through Maya, starts the thread to send information to debugger,
    then remains in a loop reading messages from debugger.
    """

    global interface

    interface = DebuggerInterface(on_receive=on_receive_from_debugger)
    interface.start()


def on_receive_from_debugger(message):
    """
    Intercept the initialize and attach requests from the debugger
    while debugpy is being set up
    """

    contents = json.loads(message)

    log('Received from Debugger:', message)

    cmd = contents['command']
    
    if cmd == 'initialize':
        # Run init request once Maya connection is established and send success response to the debugger
        interface.send(json.dumps(json.loads(INITIALIZE_RESPONSE)))  # load and dump to remove indents
        processed_seqs.append(contents['seq'])
        # pass
    
    elif cmd == 'attach':
        # time to attach to Maya
        run(attach_to_maya, (contents,))

        # Change arguments to valid ones for debugpy
        config = contents['arguments']
        new_args = ATTACH_ARGS.format(
            dir=dirname(config['program']).replace('\\', '\\\\'),
            hostname=config['debugpy']['host'],
            port=int(config['debugpy']['port']),
            # filepath=config['program'].replace('\\', '\\\\')
        )

        contents = contents.copy()
        contents['arguments'] = json.loads(new_args)
        message = json.dumps(contents)  # update contents to reflect new args

        log("New attach arguments loaded:", new_args)

    # Then just put the message in the debugpy queue
    debugpy_send_queue.put(message)


def attach_to_maya(contents):
    """
    Defines commands to send to Maya, and sends the attach code to it.
    """

    global attach_code, Maya_path
    config = contents['arguments']

    # format attach code appropriately
    attach_code = ATTACH_TEMPLATE.format(
        debugpy_path=debugpy_path,
        hostname=config['debugpy']['host'],
        port=int(config['debugpy']['port']),
        interpreter=config['interpreter'],
    )

    # Copy code to temporary file and start a Maya console with it
    try: 
        send_code_to_maya(attach_code)
    except Exception as e:
        log("Exception occurred: \n\n" + str(e))
        import platform
        module_path = join(dirname(__file__), 'resources', 'module')
        separator = ';' if platform.system() == 'Windows' else ':'
        raise Exception(
            """
                              Could not connect to Maya.

                Please ensure Maya is running. If this is your first time
                using the debug adapter, ensure the MAYA_MODULE_PATH
                environment variable is set correctly (ie contains {0}), 
                           then restart Maya and try again.
            """.format(module_path + separator)
        )

    # Then start the Maya debugging threads
    run(start_debugging, ((config['debugpy']['host'], int(config['debugpy']['port'])),))


def send_code_to_maya(code):
    """
    Copies code to temporary file, formats execution template code with file location, 
    and sends execution code to Maya via socket connection.

    Inspired by send_to_Maya.py at https://github.com/tokejepsen/atom-foundry-Maya
    """

    filepath = join(gettempdir(), 'temp.py')
    with open(filepath, "w") as file:
        file.write(code)

    # throws error if it fails
    log("Sending code to Maya...")

    # cmd = Maya_CMD_TEMPLATE.format(filepath)

    ADDR = ("localhost", 8890)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)

    client.send(code.encode("UTF-8"))
    client.close()
    
    log("Success")


def start_debugging(address):
    """
    Connects to debugpy in Maya, then starts the threads needed to
    send and receive information from it
    """

    log("Connecting to " + address[0] + ":" + str(address[1]))

    global debugpy_socket
    debugpy_socket = socket.create_connection(address)

    log("Successfully connected to Maya for debugging. Starting...")

    run(debugpy_send_loop)  # Start sending requests to debugpy

    fstream = debugpy_socket.makefile()

    while True:
        try:
            content_length = 0
            while True:
                header = fstream.readline()
                if header:
                    header = header.strip()
                if not header:
                    break
                if header.startswith(CONTENT_HEADER):
                    content_length = int(header[len(CONTENT_HEADER):])

            if content_length > 0:
                total_content = ""
                while content_length > 0:
                    content = fstream.read(content_length)
                    content_length -= len(content)
                    total_content += content

                if content_length == 0:
                    message = total_content
                    on_receive_from_debugpy(message)

        except Exception as e:
            log("Failure reading Maya's debugpy output: \n" + str(e))
            debugpy_socket.close()
            break


def debugpy_send_loop():
    """
    The loop that waits for items to show in the send queue and prints them.
    Blocks until an item is present
    """

    while True:
        msg = debugpy_send_queue.get()
        if msg is None:
            return
        else:
            try:
                debugpy_socket.send('Content-Length: {}\r\n\r\n'.format(len(msg)).encode('UTF-8'))
                debugpy_socket.send(msg.encode('UTF-8'))
                log('Sent to debugpy:', msg)
            except OSError:
                log("Debug socket closed.")
                return
            except Exception as e:
                log("Error sending to debugpy: " + str(e))
                return


def on_receive_from_debugpy(message):
    """
    Handles messages going from debugpy to the debugger
    """

    c = json.loads(message)
    seq = int(c.get('request_seq', -1))  # a negative seq will never occur
    cmd = c.get('command', '')

    if cmd == 'configurationDone':
        # When Debugger & debugpy are done setting up, send the code to debug
        log('Received from debugpy:', message)
        interface.send(message)
        return

    # Send responses and events to debugger
    if seq in processed_seqs:
        # Should only be the initialization request
        log("Already processed, debugpy response is:", message)
    else:
        log('Received from debugpy:', message)
        interface.send(message)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(str(e))
        raise e
