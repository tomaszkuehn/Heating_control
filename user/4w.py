#!/usr/bin/env python

import os
import time
import sys
import serial
import binascii
import threading
from threading import Thread
import Queue

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')


temp_sensor1 = '/sys/bus/w1/devices/28-0000031bd290/w1_slave'
temp_sensor = '/sys/bus/w1/devices/28-0000031bc16f/w1_slave'
temp_on	 = 2000
temp_off = 2030
heating = 0
temp_1w = 0
periodic_run = 0

#serial port to send messages over wireless
ser = serial.Serial (
    port='/dev/ttyAMA0',
    baudrate = 9600,
    parity=serial.PARITY_EVEN,
    stopbits = serial.STOPBITS_TWO,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def temp_raw():
    try:
        f = open(temp_sensor, 'r')
    except IOError:
        time.sleep(0.1)
        lines = "   :"
        return lines
    lines = f.readlines()
    f.close()
    return lines


def read_temp(num, out_queue):

    lines = temp_raw()
    timeout = 0
    while ((timeout < 10) and (lines[0].strip()[-3:] != 'YES')):
        timeout = timeout + 1
        time.sleep(0.2)
        lines = temp_raw()

    temp_output = lines[1].find('t=')

    if temp_output != -1:
        temp_string = lines[1].strip()[temp_output+2:]
        temp_c = float(temp_string) / 1000.0
#        temp_f = temp_c * 9.0 / 5.0 + 32.0
        #return temp_c
	print "Read temp TC:%f\n" % temp_c
	out_queue.put(temp_c)
    

    
def heating_switch(heating):
	print "HSW:%d " % heating
#now send over serial
	packet = bytearray()
	if (heating == 1):
	    packet.append(0x01)
	    packet.append(0x05)
	    packet.append(0x00)
	    packet.append(0x00)
	    packet.append(0xFF)
	    packet.append(0x00)
	    packet.append(0x8C)
	    packet.append(0x3A)
	if (heating == 0):
	    packet.append(0x01)
	    packet.append(0x05)
	    packet.append(0x00)
	    packet.append(0x01)
	    packet.append(0xFF)
	    packet.append(0x00)
	    packet.append(0xDD)
	    packet.append(0xFA)

	print binascii.hexlify(packet)
	ser.write(packet)


#heating_switch(0)

#exit()



temp_arr     = [];
for i in range (0,720):
    temp_arr.append(0)
heat_arr     = [];
for i in range (0,720):
    heat_arr.append(0)

temp_avg_arr = []
for i in range (0,12):
    temp_avg_arr.append(0)

hour_arr = []
for i in range (0,24):
    hour_arr.append([1,0])


def read_hour_arr():
    f = open("/user/hour.txt","r")
    f1 = f.readlines()
    for x in f1:
        utime,uon,uoff = x.split(",") 
        hour_arr[int(utime)]=[int(uon), int(uoff)] 
    
    print hour_arr[7][0]," ",hour_arr[7][1]+1
    
    
read_hour_arr()
print hour_arr
time.sleep(5)
    
minute = 0
my_queue = Queue.Queue()
seconds = round(time.time())

while True:
    systime = time.localtime(time.time())
    print systime.tm_hour,':',systime.tm_min, " While loop..." 
    if systime.tm_min == 0:
        read_hour_arr()
    temp_on  = hour_arr[systime.tm_hour][0]
    temp_off = hour_arr[systime.tm_hour][1]
    print temp_on,"-",temp_off
#read 1-wire    
    t = Thread(target=read_temp, args=(1, my_queue))
    t.daemon = True
    t.start()
    t.join(2)
    if t.is_alive():
        print "Alive..."
        t1 = Thread(target=read_temp, args=(1, my_queue))
        t1.daemon = True
        t1.start()
        t1.join(2)
        if t1.is_alive():
            print "Alive2..."
            print threading.active_count()
#            continue
#        continue
#read until queue is empty
    while not my_queue.empty():
        tt = my_queue.get()
#current temp in tt
	if (tt < -1000):
	    tt = temp_avg_arr[0]
	if (tt > 4000):
	    tt = temp_avg_arr[0]
	print(tt)
#update avg temp array
	temp_avg_arr.pop(0)
	temp_avg_arr.append(tt)

	print temp_avg_arr

#calculate average temperature over last minute
	temp_avg = 0
	for i in range (0, 12):
	    temp_avg = temp_avg + temp_avg_arr[i]
	temp_avg = temp_avg/12
	temp_avg = temp_avg*100
	temp_avg = round(temp_avg)
	print("(%d): AVG: %d " % (round(time.time()),temp_avg))

#drive heating
	if temp_avg <= temp_on:
	    heating = 1

	if temp_avg >= temp_off:
	    heating = 0

#check heating rule to avoid continuous usage
	hh = 0
	if(heating - heat_arr[719] == 1): #heating switched on
	    for i in range (705,720):
		hh = hh + heat_arr[i]
		if ( hh > 0 ):
		    heating = 0
		    print("HH:%d Heating postponed - over usage\n" % hh)
	if( heat_arr[719] == 1):	#heating was on
	    for i in range (698,720):
		hh = hh + heat_arr[i]
		if ( hh > 19 ):
		    heating = 0
		    print("HH:%d Heating stopped - over usage\n" % hh)

#run every three hours
	hh = 0
	if(heating == 0):
	    for i in range (630,720):
		hh = hh + heat_arr[i]
	    if ( hh == 0 ):
		periodic_run = 1
	hh = 0
	if ( periodic_run == 1 ):
	    for i in range (714,720):
		hh = hh + heat_arr[i]
	    if ( hh >= 4 ):
		periodic_run = 0
	heating = heating | periodic_run

	heating_switch(heating)

	if minute == 12: #shift data in array
	    minute = 0
	    temp_arr.pop(0)
	    temp_arr.append(temp_avg)
	    heat_arr.pop(0)
	    if((heating!=0) and (heating!=1)):
		heating = 0
	    heat_arr.append(heating)

#create www
        ff = open("/var/www/html/temp.json","w+")
        ff.write("{\n")
        ff.write("\"TEMP_ARR\":[0")
        for item in temp_arr:
            ff.write(",%d" % item)
        ff.write("],")
        ff.write("\"HEAT_ARR\":[0")
        for item in heat_arr:
            ff.write(",%d" % item)
        ff.write("],")
        ff.write("\"LAST_AVG\":%d," % temp_avg)
        ff.write("\"HEAT_ON\":%d," % temp_on)
        ff.write("\"HEAT_OFF\":%d" % temp_off)
        ff.write("\n}\n")
        ff.write
        ff.close

	print "\n"
	sys.stdout.flush()
        
	while(round(time.time())-seconds<10):
	    time.sleep(1)
	seconds = round(time.time())
	minute = minute + 1



