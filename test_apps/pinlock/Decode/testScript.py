#!/usr/bin/python

import time
import serial
import sys
import thread
import struct
import getopt


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
    print 'Khaled Saab'
    print 'Script to automate Application #1'
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
            if (c == '\n'):
                print "[%7s] %s" % (threadName, s)
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
    baudrate = 9600

  
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
    relock = 0			#condition to relock system    

    # message to make sure sync takes place between pyterm and application
    logd("Application must start in 0 to 5 seconds\n")
    time.sleep(6); #6 sec delay 

    while 1 :
        try:
            
	    if (relock == 1) : 
		serial.write(lock)	#relock system
	  	relock = 0         	#dont relock after
		time.sleep(1)
		continue

            if (count == k) :
                count = 0       #reset count
		k = k + 1       #increment k
                failures = 0    #reset failure
                delay = 0	#reset delay
                relock = 1      #relock after
		serial.write(pin) #unlock

	    else :
                failures = failures + 1
		serial.write(wrong_pin) #incorrect pin
           
            
	    count = count + 1
            
            
	    # determining delay, always 2 more than application to insure sync
	    if (failures == 6) :
            	delay = 7  
            if (failures == 7) :
		delay = 12
	    if (failures == 8) :
		delay = 22
	    if (failures == 9) :
		delay = 42
	    if (failures == 10) :
		delay = 82
	    if (failures > 10) :
		delay = 100000   #lockout

            
	    time.sleep(delay)
	    time.sleep(1)    #always have 1 second delay to make sure of sync

        except KeyboardInterrupt:
            print
            logd("Keyboard interrupt") 
            break
        except Exception, err:
            logd("Exception")
            print sys.exc_info()[0]
            print err
            break

'''
    while 1 :
        try:
            logd("Enter a number: ", False)
            inStr = raw_input() 
            try:
                inFloat = float(inStr)
                inHex = double_to_hex(inFloat)
                #printHex(inHex)
                sendHex(inHex) 

            except ValueError:
               logd("Enter a proper number!")

            time.sleep(1)

        except KeyboardInterrupt:
            print
            logd("Keyboard interrupt") 
            break
        except Exception, err:
            logd("Exception")
            print sys.exc_info()[0]
            print err
            break

'''

