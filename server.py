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

'''
Modif a tester :
1   -> encryptage des données vers le microcontroleur en serial 
        (a voir avec eriau, quand on envoie TL ou LT par android le serial doit envoyer les données au microbit connecté en usb)
    -> encryptage des données vers l'application android

2   -> les données sont elles envoyées dans la base de données

3   -> la dernière données est restitué à l'application android quand on fait un getValues()

'''

'''
 * variables for script
'''
HOST            = "0.0.0.0"
UDP_PORT        = 10000
MICRO_COMMANDS  = ["TL" , "LT"]
FILENAME        = "values.txt"
LAST_VALUE      = "deadbeef"
SERIALPORT      = "/dev/tty.usbmodem14102"
BAUDRATE        = 115200
ENCRYPT         = 3

ser = serial.Serial()

# -------------------- Class -------------------- #
class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        socket = self.request[1]
        current_thread = threading.current_thread()
        print(f"{current_thread.name}: client: {self.client_address}, wrote: {data}")
        # Modif a tester 1 -> vérifier tous les decrypt
        if data != "":
            if decrypt(data.decode(), ENCRYPT) in MICRO_COMMANDS:                         # Send message through UART
                sendUARTMessage(data)
            elif decrypt(data.decode("UTF-8"), ENCRYPT) == "getValues()":                 # Sent last value received from micro-controller
                last_value = query_select_one_executor("SELECT received_data FROM message ORDER BY id DESC LIMIT 1") # Modif a tester 3
                socket.sendto(encrypt(last_value, ENCRYPT).encode(), self.client_address) # Modif a tester 1
            else:                                                                         # Check errors 
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
    print(f"Message <{msg.decode()}> sent to micro-controller")

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
 * database query insert executor function
'''
def query_insert_executor(query):
    try:
        db = db_connect("/Users/alexis/iot.db")
        cursor = db.cursor()
        cursor.execute(query)
        db.commit()
        print(f"Record inserted successfully -> added row : {cursor.rowcount}")
        cursor.close()
    except (sqlite3.Error, KeyboardInterrupt, SystemExit) as errors:
        print(f"Failed to insert data into sqlite table {errors}")
        cursor.close()
    finally:
        if db:
            db.close()
            print("The SQLite connection is closed")

'''
 * get last inserted row
'''
def query_select_one_executor(query):
    try:
        db = db_connect("/Users/alexis/iot.db")
        cursor = db.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]
    except (sqlite3.Error, KeyboardInterrupt, SystemExit) as errors:
        print(f"Failed to execute query {errors}")
        cursor.close()
    finally:
        if db:
            cursor.close()
            db.close()
            print("The SQLite connection is closed")

'''
 * function that encrypts the sent data
'''
def encrypt(msg, shiftPattern):
    res = ""
    for i in range(len(msg)):
        res += chr(ord(msg[i]) + shiftPattern)
    return res

'''
 * function that encrypts the received data
'''
def decrypt(msg, shiftPattern):
    res = ""
    for i in range(len(msg)):
        res += chr(ord(msg[i]) - shiftPattern)
    return res

'''
 * main program logic follows:
'''
if __name__ == '__main__':
    initUART()
    #f = open(FILENAME,"a")
    '''query_insert_executor("INSERT INTO message (received_data) VALUES ('l:59,t:31')")
    test = query_select_one_executor("SELECT received_data FROM message ORDER BY id DESC LIMIT 1")
    print(test)'''
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
                data_bytes = ser.read(ser.inWaiting()).decode("UTF-8")
                data_str += data_bytes
                if "\t" in data_bytes:
                    data_str.replace("\t", "")
                    print(data_str)
                    query_insert_executor("INSERT INTO message (received_data) VALUES ('" + data_str + "')") # Modif a tester 2
                    # f.write(data_str)
                    # f.flush()
                    # LAST_VALUE = data_str
                    data_str = ""
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        # f.close()
        ser.close()
        exit()