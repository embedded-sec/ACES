#!/usr/bin/python

import time
import serial
import sys
import thread
import struct
import getopt

#global variables
global relock			#condition to relock system 
global sendPin			#condition to send a pin

def hex_to_float(h):
    return struct.unpack('f', h)

def float_to_hex(f):
    return struct.pack('f', f)

def double_to_hex(d):
    return struct.pack('d', d)

def printHex(h):
    #print raw hex data
    hexData = ':'.join(x.encode('hex') for x in h)
    print hexData

def sendHex(h):
    serial.write(h)
    serial.write("\r") 

def logd(log, newline=True):
    tag = "sys"
    if (not newline):
        sys.stdout.write("[%.5f] %s" % (time.time() - t0 , log))
    else:
        print "[%.5f] %s" % (time.time() - t0 , log)

def welcomeMsg(): 
    print
    print 'Script to automate Pinlock'
    print 'Press Ctrl+c to quit'
    print

def initSerial(port, baudrate):
    # Serial port Configuration
    serial.port = "/dev/"+port
    serial.baudrate = baudrate
    serial.timeout = 1
    serial.writeTimeout = 1
    serial.open()
    serial.flush()

    logd( 'Opening port %s - %s' %(port, baudrate) )
    
    serial.isOpen()

    if serial.isOpen(): 
        logd('Success')
    else:
        logd('Failed')
        exit(2)

# Thread for printing data from serial
def readSerial(threadName, delay):
    s = ""
    while True:
        if serial.inWaiting() != 0:
            c = serial.read()

            if (c=='U'):
                global relock
                relock = 1
            if (c=='S' or c=='I'):
                global sendPin
                sendPin = 1

            if (c == '\n'):
                print "[%7s] %s" % (threadName, s)
#                if(s == "Enter Pin:"): 
#                    print "in sendpin"
#                    global sendPin
#                    sendPin = 1
                if(s == "Unlocked"):
                    print "In unlocked"
                    global relock
                    relock = 1
                s =""
            else:
                s += c
        else:
            time.sleep(0.01)


if __name__ == '__main__':
	welcomeMsg();
	t0 = time.time()
	serial = serial.Serial()
	port = "ttyUSB0"
	baudrate = 115200

  
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hp:b:",["port=","baudrate="])
	except getopt.GetoptError:
		print 'pyTerm.py -p <port> -b <baudrate>'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'pyTerm.py -p <port> -b <baudrate>'
			sys.exit()
		elif opt in ("-p", "--port"):
			port = arg
		elif opt in ("-b", "--baudrate"):
			baudrate = int(arg)
    
	initSerial(port, baudrate)

  

	thread.start_new_thread( readSerial , ("Discovery-Board", 2, ))

	pin = '1995\n'		#correct pin to unlock system
	wrong_pin = '1234\n'	#some incorrect pin 
	lock = '0\n'  		#key to lock system after unlock
	failures = 0		#counter for number of failures
	delay = 0                   #for failures delay
	count = 0			#count for after system is locked
	k = 0			#determines when to unlock
	global relock			#condition to relock system   
	relock = 0
	global sendPin
	sendPin = 0  


	while 1 :
		try:

			if (relock == 1):
				relock = 0         	#dont relock after 
				serial.write(lock)	#relock system
				continue

			if (sendPin == 1):  
				sendPin = 0        #reset send signal
				if (count % 2 == 0):
					serial.write(pin) #unlock
				else :
					serial.write(wrong_pin) #incorrect pin
				count = count + 1

			time.sleep(0.001)

		except KeyboardInterrupt:
			print
			logd("Keyboard interrupt") 
			break
		except Exception, err:
			logd("Exception")
			print sys.exc_info()[0]
			print err
			break


