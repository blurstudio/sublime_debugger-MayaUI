"""
Maya Threaded Server

Modified from: https://gist.github.com/Meatplowz/154fb17487e9ce0c0e8b362262a2d8a4
"""

import logging
import socket
import threading

import maya.cmds as cmds
import maya.utils as maya_utils

from PySide2.QtWidgets import QMessageBox

HOST = "localhost"
PORT = 8890
CONNECTIONS = 5


def function_to_process(data):
    """
    Maya function
    :param data: incoming data to process
    :return:
    """

    logging.info("Debug Server, Process Function: {}".format(data))
    cmds.headsUpMessage("Processing incoming data: {}".format(data), time=3.0)

    exec(data)


def process_update(data):
    """
    Process incoming data, run this in the Maya main thread
    :param data:
    :return:
    """

    try:
        maya_utils.executeInMainThreadWithResult(function_to_process, data)
    except Exception as e:
        cmds.error("Debug Server, Exception processing Function: {}".format(e))


def maya_server(host=HOST, port=PORT, connections=CONNECTIONS):
    """
    Maya server
    :param host: Host IP or localhost
    :param port: Integer
    :param connections: Integer Number of connections to handle
    :return:
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except Exception as socket_error:
        msg = "Debug Server, Failed to open port: {}".format(socket_error)
        logging.error(msg)
        cmds.error(msg)
        return

    sock.listen(connections)
    logging.info("Starting Debug Server: {}".format(port))
    while True:
        client, address = sock.accept()
        data = client.recv(1024)
        if data:
            if data == "#Shutdown#":
                break
            else:
                logging.info("Debug Server, Data Received: {}".format(data))
                process_update(data)
        try:
            client.close()
        except Exception as client_error:
            logging.info("Debug Server, Error Closing Client Socket: {}".format(client_error))

    logging.info("Debug Server, Shutting Down.")
    try:
        sock.close()
    except Exception as close_error:
        logging.info("Debug Server, Error Closing Socket: {}".format(close_error))


def start():
    logging.basicConfig(level=logging.DEBUG)
    threading.Thread(target=maya_server).start()

    QMessageBox.information(None, 'Server is ready', 'Sublime debugger can now attach to Maya for UI debugging.')
