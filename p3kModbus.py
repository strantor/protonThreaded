# temp script for logging from lappytoppy

from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils
from datetime import datetime
import time

# import board
# import neopixel
# from gpiozero import Button
import pprint


# import usbCheck

# class ioController():
#
#     def __init__(self):
#         self.lineRunning = Button(26)
#         self.pixels1 = neopixel.NeoPixel(board.D18, 1, brightness=1)
#         self.pixels2 = neopixel.NeoPixel(board.D21, 1, brightness=1)
#
#     def setLED1color(self, color=(0, 255, 0)):
#         self.pixels1.fill(color)
#
#     def setLED2color(self, color=(0, 255, 0)):
#         self.pixels2.fill(color)


class protonModbus():

    def __init__(self, ip="192.168.50.196", port=502, timeout=5):
        self.ip = ip
        self.c = ModbusClient(host=ip, port=port, unit_id=1, auto_open=True, timeout=timeout)
        # self.c.host(ip)
        # self.c.port(port)
        # self.c.timeout(timeout)
        self.wordsIn = []
        self.wordsOut = []
        self.wordsInStartingAddr = 1  # 201 = (400201)
        self.wordsInLength = 10
        self.wordsOutStartingAddr = 1
        self.wordsOutLength = 10
        self.slMiniDict = {}
        self.dgkDict = {}
        self.slMiniLogOptions = []
        self.runs = 0
        self.errors = 0

        self.logDict = {}

    def start(self):
        self.success = self.c.open()
        # print(self.success)
        if self.success == True:
            return True
        else:

            #return False
            errStr = "Failed to connect to Modbus TCP device at " + self.ip
            raise Exception(errStr)


    def readInputRegisters(self):  # Read the Proton SLMini's OUTPUT parameters
        err = 0
        self.runs += 1
        #print("self.runs:", self.runs)

        # self.wordsIn = self.c.read_holding_registers(self.wordsInStartingAddr-1, self.wordsInLength)


        for i in range(0,5): # This became necessary after importing the script into PyQt threaded app. For some reason
            # after the first call, the device will thereafter return nothing on the next call. Then the 3rd will
            # contain data. 4th none. 5th data. and so on, every other call returns nothing. So this gives it 5 chances
            # to work properly.
            self.wordsIn = self.c.read_holding_registers(self.wordsInStartingAddr - 1, self.wordsInLength)
            #print(self.wordsIn)
            if self.wordsIn:
                break
        if self.wordsIn:
            # print(self.wordsIn)
            # print(len(self.wordsIn))
            if len(self.wordsIn) < self.wordsInLength:
                err = 1
                errStr = "Failed to read all words from Modbus TCP device at " + self.ip
                raise Exception(errStr)
            else:
                pass
                # newlist = []
                # for word in self.wordsIn:
                #     # For some reason the Proton machine reports reversed bytes
                #     bytes_val = word.to_bytes(2, byteorder='big')
                #     reversed_bytes = int.from_bytes(bytes_val, byteorder='little')
                #     # print(word, reversed_bytes)
                #     newlist.append(reversed_bytes)
                # self.wordsIn = newlist
        else:
            err = 1
            errStr = "No reply on readInputRegisters() from Modbus TCP device at " + self.ip
            raise Exception(errStr)
            #print(errStr)

        if err == 0:
            return True
        else:
            return False

    def writeSingleWord(self, which, val):
        if val <= 65535 and val >= 0:

            addr = self.wordsOutStartingAddr + which - 2
            success = self.c.write_single_register(addr, val)
            if success != True:
                errStr = "Failed to write single word to Modbus TCP device at " + self.ip
                raise Exception(errStr)


        else:
            raise Exception("Invalid value (", val, "). Unsigned single integers must be between 0 and 65535")

    def dateAndTime(self):
        now = datetime.now()  # current date and time
        y = int(now.strftime("%Y"))
        mo = int(now.strftime("%m"))
        d = int(now.strftime("%d"))
        h = int(now.strftime("%H"))
        mi = int(now.strftime("%M"))
        s = int(now.strftime("%S"))
        return (y, mo, d, h, mi, s)

    def closeConnection(self):
        if self.c.close() == True:
            return True
        else:
            raise Exception("No TCP connection exists to be closed")
            return False




if __name__ == "__main__":
    import csv
    from pathlib import Path

    testNo = 3

    if testNo == 3:
        maxlogsize = 1024  # kb
        logInterval = 1000  # mS
        comboLog = {}

        mySlMini = protonModbus(ip="192.168.1.2")
        mySlMini.start()
        file_size = 0
        runs = 0
        filename = "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
        gotime = time.time() + logInterval / 1000
        blinkTime = time.time() + 0.5
        blink = True
        while runs < 50000:
            if time.time() > gotime:
                timestamp1 = time.time()
                mySlMini.readInputRegisters()
                timestamp = str(time.strftime('%Y-%m-%d %H:%M:%S'))
                print(timestamp,mySlMini.wordsIn)


                if (file_size > maxlogsize) or (runs == 0):
                    filename = "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
                    with open(filename, mode="w", newline="", encoding="utf-8") as file:
                        header = "timestamp,old F2V, new F2V,EXT Spd ref,capstan tach, capstan spd ref\n"
                        file.write(header)
                        file_size = 0
                        print(1)
                else:
                    with open(filename, mode="a+", newline="", encoding="utf-8") as file:
                        nl = timestamp + ","

                        for word in mySlMini.wordsIn:
                            nl = nl + str(word) + ","
                        nl += "\n"
                        file.writelines(nl)
                        file_size = Path(filename).stat().st_size / 1024
                        #print(2)
                runs = runs + 1
                #print(time.time() - timestamp1, file_size, filename)
                gotime = time.time() + logInterval / 1000
        mySlMini.closeConnection()







    if testNo == 2:
        mySlMini = protonModbus(ip="192.168.50.196")
        mySlMini.start()
        myDgk = protonModbus(ip="192.168.50.196")
        myDgk.start()
        logInterval = 1000  # mS
        gotime = time.time() + logInterval / 1000
        runs = 0
        comboLog = {}
        while runs < 50:
            if time.time() > gotime:
                timestamp1 = time.time()
                comboLog['timestamp'] = str(time.strftime('%Y-%m-%d %H:%M:%S'))
                mySlMini.parseSlMiniOutput()
                for k, v in mySlMini.logDict.items():
                    comboLog["foot." + k] = v
                myDgk.parseDgkOutput()
                for k, v in myDgk.logDict.items():
                    comboLog["mic." + k] = v
                pprint.pprint(comboLog)
                runs = runs + 1
                gotime = time.time() + logInterval / 1000