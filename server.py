'''
 * Program to control passerelle between Android application and micro-controller through USB tty
 * USB tty -> /dev/tty.usbmodem14102
'''

'''
A supprimer ?
from os import wait
import time
import argparse
import signal
import sys
import socket
'''
import socketserver
import serial
import threading
import sqlite3

HOST           = "0.0.0.0"
UDP_PORT       = 10000
MICRO_COMMANDS = ["TL" , "LT"]
FILENAME        = "values.txt"
LAST_VALUE      = "deadbeef"

SERIALPORT = "/dev/tty.usbmodem14102"
BAUDRATE = 115200
ser = serial.Serial()

# -------------------- Class -------------------- #
class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        socket = self.request[1]
        current_thread = threading.current_thread()
        print(f"{current_thread.name}: client: {self.client_address}, wrote: {data}") # Modif a vérifier 1

        if data != "":
            if data.decode() in MICRO_COMMANDS:                         # Send message through UART
                sendUARTMessage(data)
            elif data.decode("UTF-8") == "getValues()":                 # Sent last value received from micro-controller
                socket.sendto(LAST_VALUE.encode(), self.client_address)    
            else:                                                       # Check errors 
                print(f"Unknown message: {data}")

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass

# -------------------- Functions -------------------- #
'''
 * init serial mode
'''
def initUART():        
    ser.port = SERIALPORT
    ser.baudrate = BAUDRATE
    ser.bytesize = serial.EIGHTBITS         # number of bits per bytes
    ser.parity = serial.PARITY_NONE         # set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE      # number of stop bits
    ser.timeout = None                      # block read
    ser.xonxoff = False                     # disable software flow control
    ser.rtscts = False                      # disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False                      # disable hardware (DSR/DTR) flow control
    
    try:
        ser.open()
        print("Starting Up Serial Monitor")
    except serial.SerialException:
        print(f"Serial {SERIALPORT} port not available")
        exit()


'''
 * send message to microcontroller with serial
'''
def sendUARTMessage(msg):
    ser.write(msg)
    print(f"Message <{msg.decode()}> sent to micro-controller") # Modif a tester 2

'''
 * database connection function
'''
def db_connect(sqlite_path):
    try:
        db = sqlite3.connect(sqlite_path)
        print(f"Base de données connecté {sqlite_path}")
        return db
    except sqlite3.Error as error:
        print(f"Erreur : {error}")

'''
 * database query executor function
'''
def query_executor(query):
    try:
        db = db_connect("/Users/alexis/iot.db")
        cursor = db.cursor()
        cursor.execute(query)
        db.commit()
        print(f"Record inserted successfully into SqliteDb_developers table. Added row : {cursor.rowcount}")
        cursor.close()
    except (sqlite3.Error, KeyboardInterrupt, SystemExit) as errors:
        print(f"Failed to insert data into sqlite table {errors}")
        cursor.close()
    finally:
        if db:
            db.close()
            print("The SQLite connection is closed")

'''
 * main program logic follows:
'''
if __name__ == '__main__':
    initUART()
    #f = open(FILENAME,"a")
    # query_executor("INSERT INTO 'values' (received_data) VALUES ('test')") # Modif a tester 3
    print ('Press Ctrl-C to quit.')

    server = ThreadedUDPServer((HOST, UDP_PORT), ThreadedUDPRequestHandler)
    server_thread = threading.Thread(target = server.serve_forever)
    server_thread.daemon = True

    try:
        server_thread.start()
        print(f"Server started at {HOST} port {UDP_PORT}")
        data_str = ""
        while ser.isOpen() : 
            if (ser.inWaiting() > 0): # if incoming bytes are waiting 
                data_bytes = ser.read(ser.inWaiting()).decode("utf-8")
                data_str += data_bytes
                if "\t" in data_bytes:
                    data_str.replace("\t", "")
                    print(data_str)
                    query_executor("INSERT INTO 'values' (received_data) VALUES ('" + data_str + "')") # Modif a tester 3
                    # f.write(data_str)
                    # f.flush()
                    LAST_VALUE = data_str
                    data_str = ""
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        # f.close()
        ser.close()
        exit()