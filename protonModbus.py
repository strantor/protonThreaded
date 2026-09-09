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
        self.wordsInLength = 100
        self.wordsOutStartingAddr = 1
        self.wordsOutLength = 100
        self.slMiniDict = {}
        self.dgkDict = {}
        self.slMiniLogOptions = []
        self.runs = 0
        self.errors = 0
        with open("logOptions.txt", "r") as restText:
            for line in restText.readlines():
                L, R = line.split(":")
                R = R.strip()
                if R in ["yes", "true", "1", "y", "Y", "True", "TRUE", "t", "T", "Yes"]:
                    self.slMiniLogOptions.append(L)
        self.dgkLogOptions = []
        with open("logOptions2.txt", "r") as restText:
            for line in restText.readlines():
                L, R = line.split(":")
                R = R.strip()
                if R in ["yes", "true", "1", "y", "Y", "True", "TRUE", "t", "T", "Yes"]:
                    self.dgkLogOptions.append(L)
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
            self.wordsIn = self.c.read_input_registers(self.wordsInStartingAddr - 1, self.wordsInLength)
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
                newlist = []
                for word in self.wordsIn:
                    # For some reason the Proton machine reports reversed bytes
                    bytes_val = word.to_bytes(2, byteorder='big')
                    reversed_bytes = int.from_bytes(bytes_val, byteorder='little')
                    # print(word, reversed_bytes)
                    newlist.append(reversed_bytes)
                self.wordsIn = newlist
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

    def parseDgkOutput(self):
        err = 0
        self.wordsInLength = 73
        if self.readInputRegisters() == True:
            deviceHealth = 0
            # DW0
            self.dgkDict['Measurement Mode'] = (self.wordsIn[0] >> 0) & 0b111
            self.dgkDict['Unit'] = (self.wordsIn[0] >> 3) & 1
            self.dgkDict['Shrinkage mode'] = (self.wordsIn[0] >> 4) & 1
            self.dgkDict['High Resolation for Diameter'] = (self.wordsIn[0] >> 5) & 1
            self.dgkDict['Over average upper limit'] = (self.wordsIn[0] >> 6) & 1
            self.dgkDict['Under average lower limit'] = (self.wordsIn[0] >> 7) & 1
            self.dgkDict['Over X upper limit'] = (self.wordsIn[0] >> 8) & 1
            self.dgkDict['Under X lower limit'] = (self.wordsIn[0] >> 9) & 1
            self.dgkDict['Over Y upper limit'] = (self.wordsIn[0] >> 10) & 1
            self.dgkDict['Under Y lower limit'] = (self.wordsIn[0] >> 11) & 1
            self.dgkDict['Over Z upper limit'] = (self.wordsIn[0] >> 12) & 1
            self.dgkDict['Under Z lower limit'] = (self.wordsIn[0] >> 13) & 1
            self.dgkDict['Over ovality upper limit'] = (self.wordsIn[0] >> 14) & 1
            self.dgkDict['Under ovality lower limit'] = (self.wordsIn[0] >> 15) & 1
            # DW1
            self.dgkDict['Res'] = (self.wordsIn[1] >> 0) & 1
            self.dgkDict['No reading'] = (self.wordsIn[1] >> 1) & 1
            self.dgkDict['No object'] = (self.wordsIn[1] >> 2) & 1
            self.dgkDict['Window dirty'] = (self.wordsIn[1] >> 3) & 1
            self.dgkDict['Line speed too low in helix mode'] = (self.wordsIn[1] >> 4) & 1
            self.dgkDict['Line speed too high in helix mode'] = (self.wordsIn[1] >> 5) & 1
            self.dgkDict['Gauge too hot'] = (self.wordsIn[1] >> 6) & 1
            self.dgkDict['External Alarm 1'] = (self.wordsIn[1] >> 8) & 1
            self.dgkDict['External Alarm 2'] = (self.wordsIn[1] >> 9) & 1
            if self.wordsIn[1] > 0: deviceHealth += 1
            self.dgkDict['Average diameter/Envelop'] = ((self.wordsIn[3] << 16) | self.wordsIn[2]) / 100
            self.dgkDict['X diameter'] = ((self.wordsIn[5] << 16) | self.wordsIn[4]) / 100
            self.dgkDict['Y diameter'] = ((self.wordsIn[7] << 16) | self.wordsIn[6]) / 100
            self.dgkDict['Z diameter'] = ((self.wordsIn[9] << 16) | self.wordsIn[8]) / 100
            self.dgkDict['Ovality'] = ((self.wordsIn[11] << 16) | self.wordsIn[10]) / 100
            self.dgkDict['Average error/Envelop Error'] = ((self.wordsIn[13] << 16) | self.wordsIn[12]) / 100
            self.dgkDict['X error'] = ((self.wordsIn[15] << 16) | self.wordsIn[14]) / 100
            self.dgkDict['Y error'] = ((self.wordsIn[17] << 16) | self.wordsIn[16]) / 100
            self.dgkDict['Z error'] = ((self.wordsIn[19] << 16) | self.wordsIn[18]) / 100
            self.dgkDict['Ovality error'] = ((self.wordsIn[21] << 16) | self.wordsIn[20]) / 100
            self.dgkDict['Latest lump value'] = ((self.wordsIn[23] << 16) | self.wordsIn[22]) / 100
            self.dgkDict['Latest lump positon'] = ((self.wordsIn[25] << 16) | self.wordsIn[24]) / 1000
            self.dgkDict['Latest neck value'] = ((self.wordsIn[27] << 16) | self.wordsIn[26]) / 100
            self.dgkDict['Latest neck position'] = ((self.wordsIn[29] << 16) | self.wordsIn[28]) / 100
            self.dgkDict['Lump count'] = self.wordsIn[30]
            self.dgkDict['Neck count'] = self.wordsIn[31]
            self.dgkDict['Running maximum diameter'] = ((self.wordsIn[33] << 16) | self.wordsIn[32]) / 100
            self.dgkDict['Running minimum diameter'] = ((self.wordsIn[35] << 16) | self.wordsIn[34]) / 100
            self.dgkDict['Running average diameter'] = ((self.wordsIn[37] << 16) | self.wordsIn[36]) / 100
            self.dgkDict['Cable position on X axis'] = self.wordsIn[38]
            self.dgkDict['Cable position on Y axis'] = self.wordsIn[39]
            self.dgkDict['Cable position on Z axis'] = self.wordsIn[40]
            self.dgkDict['Line speed'] = self.wordsIn[41] / 10
            self.dgkDict['Length'] = ((self.wordsIn[43] << 16) | self.wordsIn[42]) / 100
            self.dgkDict['Normal distribution'] = (self.wordsIn[44] >> 0) & 1
            self.dgkDict['Not used'] = (self.wordsIn[44] >> 1) & 1
            self.dgkDict['SPC is available'] = (self.wordsIn[44] >> 2) & 1
            self.dgkDict['Statistics remain time'] = self.wordsIn[45]
            self.dgkDict['Standard deviation'] = ((self.wordsIn[47] << 16) | self.wordsIn[46]) / 100
            self.dgkDict['Maximum diameter'] = ((self.wordsIn[49] << 16) | self.wordsIn[48]) / 100
            self.dgkDict['Minimum diameter'] = ((self.wordsIn[51] << 16) | self.wordsIn[50]) / 100
            self.dgkDict['Mean diameter'] = ((self.wordsIn[53] << 16) | self.wordsIn[52]) / 100
            self.dgkDict['Chi of normal distribution'] = self.wordsIn[54]
            self.dgkDict['Cp'] = self.wordsIn[55]
            self.dgkDict['Cpk'] = self.wordsIn[56]
            self.dgkDict['FFT remain time'] = self.wordsIn[57]
            self.dgkDict['Control status'] = self.wordsIn[58]
            if self.wordsIn[58] not in [1,3]: deviceHealth += 1
            self.dgkDict['Control output'] = self.wordsIn[59] / 100
            self.dgkDict['Communication Bus Type'] = self.wordsIn[62]
            self.dgkDict['Res'] = self.wordsIn[63]
            myStr = str((self.wordsIn[65] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[65] & 0x00FF)) + "."
            myStr += str((self.wordsIn[64] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[64] & 0x00FF))
            self.dgkDict['IP address for ETH'] = myStr
            myStr = str((self.wordsIn[67] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[67] & 0x00FF)) + "."
            myStr += str((self.wordsIn[66] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[66] & 0x00FF))
            self.dgkDict['IP address for iBUS'] = myStr
            myStr = str((self.wordsIn[69] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[69] & 0x00FF)) + "."
            myStr += str((self.wordsIn[68] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[68] & 0x00FF))
            self.dgkDict['Sub net Mask'] = myStr
            myStr = str((self.wordsIn[71] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[71] & 0x00FF)) + "."
            myStr += str((self.wordsIn[70] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[70] & 0x00FF))
            self.dgkDict['Gateway'] = myStr
            self.dgkDict['Gauge temperature'] = self.wordsIn[72]
            if self.wordsIn[72]>80: deviceHealth += 1
            # pprint.pprint(self.dgkDict)
            self.dgkDict['deviceHealth'] = deviceHealth
            for k, v in self.dgkDict.items():
                if k in self.dgkLogOptions:
                    self.logDict[k] = self.dgkDict[k]

    def parseSlMiniOutput(self):
        err = 0
        self.wordsInLength = 40
        deviceHealth = 0
        if self.readInputRegisters() == True:
            # DW0
            self.slMiniDict['Measurement mode'] = (self.wordsIn[0] >> 0) & 1
            self.slMiniDict['Resolution of length output'] = (self.wordsIn[0] >> 1) & 1
            self.slMiniDict['Speed reponse for pulse and analogue output'] = (self.wordsIn[0] >> 2) & 1
            self.slMiniDict['Measured length > Preset1'] = (self.wordsIn[0] >> 8) & 1
            self.slMiniDict['Measured length > Preset2'] = (self.wordsIn[0] >> 9) & 1
            self.slMiniDict['Laser Status'] = (self.wordsIn[0] >> 11) & 1
            if self.slMiniDict['Laser Status'] !=1: deviceHealth +=1
            self.slMiniDict['Speed reading valid'] = (self.wordsIn[0] >> 12) & 1
            if self.slMiniDict['Speed reading valid'] != 1: deviceHealth += 1
            self.slMiniDict['Object detected'] = (self.wordsIn[0] >> 13) & 1
            if self.slMiniDict['Object detected'] != 1: deviceHealth += 1
            self.slMiniDict['Good reading status'] = (self.wordsIn[0] >> 14) & 1
            if self.slMiniDict['Good reading status'] != 0: deviceHealth += 1
            # DW1
            self.slMiniDict['Gauge OK'] = (self.wordsIn[1] >> 0) & 1
            self.slMiniDict['Laser temperature too high'] = (self.wordsIn[1] >> 1) & 1
            self.slMiniDict['Laser temperature too low'] = (self.wordsIn[1] >> 2) & 1
            self.slMiniDict['Case temperature too high'] = (self.wordsIn[1] >> 3) & 1
            self.slMiniDict['Case temperature too low'] = (self.wordsIn[1] >> 4) & 1
            self.slMiniDict['Light reflection too strong'] = (self.wordsIn[1] >> 5) & 1
            self.slMiniDict['Gauge too hot'] = (self.wordsIn[1] >> 6) & 1
            if self.wordsIn[1] != 1: deviceHealth += 1
            self.slMiniDict['Averaged speed'] = ((self.wordsIn[3] << 16) | self.wordsIn[2]) / 1000  # DW2+3
            self.slMiniDict['Instant speed'] = ((self.wordsIn[5] << 16) | self.wordsIn[4]) / 1000  # DW4+5
            self.slMiniDict['Total length'] = ((self.wordsIn[7] << 16) | self.wordsIn[6]) / 10000  # DW6+7
            self.slMiniDict['Batch length'] = ((self.wordsIn[9] << 16) | self.wordsIn[8]) / 10000  # DW8+9
            self.slMiniDict['Last length before reset'] = ((self.wordsIn[11] << 16) | self.wordsIn[
                10]) / 10000  # DW10+11
            self.slMiniDict['Reel number'] = (self.wordsIn[13] << 16) | self.wordsIn[12]  # DW12+13
            self.slMiniDict['Batch number'] = self.wordsIn[14]  # DW14
            self.slMiniDict['Good reading'] = self.wordsIn[15]  # DW15
            self.slMiniDict['SNR'] = self.wordsIn[16]
            self.slMiniDict['SLX current height'] = self.wordsIn[17]
            self.slMiniDict['DW18'] = self.wordsIn[18]
            self.slMiniDict['DW19'] = self.wordsIn[19]
            # DW20
            self.slMiniDict['LIN1 status'] = (self.wordsIn[20] >> 0) & 1
            self.slMiniDict['LIN2 status'] = (self.wordsIn[20] >> 1) & 1
            self.slMiniDict['LIN3 status'] = (self.wordsIn[20] >> 2) & 1
            self.slMiniDict['Length reset'] = (self.wordsIn[20] >> 4) & 1
            if self.slMiniDict['Length reset'] != 0: deviceHealth += 1
            self.slMiniDict['Length hold'] = (self.wordsIn[20] >> 5) & 1
            if self.slMiniDict['Length hold'] != 0: deviceHealth += 1
            self.slMiniDict['Display hold'] = (self.wordsIn[20] >> 6) & 1
            if self.slMiniDict['Display hold'] != 0: deviceHealth += 1
            self.slMiniDict['Speed hold'] = (self.wordsIn[20] >> 7) & 1
            if self.slMiniDict['Speed hold'] != 0: deviceHealth += 1
            self.slMiniDict['Length counting direction'] = (self.wordsIn[20] >> 10) & 1

            self.slMiniDict['DW21'] = self.wordsIn[21]
            self.slMiniDict['Measurement Unit'] = self.wordsIn[22]
            self.slMiniDict['DW23'] = self.wordsIn[23]
            self.slMiniDict['DW24'] = self.wordsIn[24]
            self.slMiniDict['DW25'] = self.wordsIn[25]
            self.slMiniDict['DW26'] = self.wordsIn[26]
            self.slMiniDict['DW27'] = self.wordsIn[27]
            self.slMiniDict['DW28'] = self.wordsIn[28]
            self.slMiniDict['DW29'] = self.wordsIn[29]
            self.slMiniDict['Communication Bus Type'] = self.wordsIn[30]
            self.slMiniDict['DW31'] = self.wordsIn[31]

            myStr = str((self.wordsIn[33] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[33] & 0x00FF)) + "."
            myStr += str((self.wordsIn[32] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[32] & 0x00FF))
            self.slMiniDict['IP address for ETH'] = myStr
            myStr = str((self.wordsIn[35] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[35] & 0x00FF)) + "."
            myStr += str((self.wordsIn[34] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[34] & 0x00FF))
            self.slMiniDict['IP address for iBUS'] = myStr
            myStr = str((self.wordsIn[37] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[37] & 0x00FF)) + "."
            myStr += str((self.wordsIn[36] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[36] & 0x00FF))
            self.slMiniDict['Sub net Mask for ETH'] = myStr
            myStr = str((self.wordsIn[39] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[39] & 0x00FF)) + "."
            myStr += str((self.wordsIn[38] & 0xFF00) >> 8) + "."
            myStr += str((self.wordsIn[38] & 0x00FF))
            self.slMiniDict['Gateway for ETH'] = myStr
            for k, v in self.slMiniDict.items():
                if k in self.slMiniLogOptions:
                    self.logDict[k] = self.slMiniDict[k]
            self.slMiniDict['deviceHealth'] = deviceHealth


if __name__ == "__main__":
    import csv
    from pathlib import Path

    testNo = 2

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


    if testNo == 1:
        # watcher = usbCheck.USBWatcher()
        # watcher.start_listening()
        myIo = ioController()
        maxlogsize = 1024  # kb
        logInterval = 1000  # mS
        comboLog = {}

        mySlMini = protonModbus(ip="192.168.50.196")
        mySlMini.start()
        myDgk = protonModbus(ip="192.168.50.196")
        myDgk.start()
        file_size = 0
        runs = 0
        filename = "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
        gotime = time.time() + logInterval / 1000
        blinkTime = time.time() + 0.5
        blink = True
        while runs < 500:
            if time.time() > blinkTime:
                if blink:
                    blink = False
                else:
                    blink = True
                blinkTime = time.time() + 0.5
            if blink:
                if myIo.lineRunning.is_pressed:
                    # myIo.setLEDcolor((200, 200, 0)) #green
                    # myIo.setLEDcolor((52, 55, 235)) #dark blue
                    # myIo.setLEDcolor((0,0,255)) #blue
                    myIo.setLED2color((255, 255, 0))  # yellow
                    myIo.setLED1color((0, 255, 0))  # green
                else:
                    myIo.setLED2color((50, 70, 215))  # light blue
                    myIo.setLED1color((255, 0, 0))  # red
            else:
                myIo.setLED1color((0, 0, 0))
                myIo.setLED2color((0, 0, 0))
            if time.time() > gotime:
                timestamp1 = time.time()
                comboLog['timestamp'] = str(time.strftime('%Y-%m-%d %H:%M:%S'))
                mySlMini.parseSlMiniOutput()
                for k, v in mySlMini.logDict.items():
                    comboLog["foot." + k] = v
                myDgk.parseDgkOutput()
                for k, v in myDgk.logDict.items():
                    comboLog["mic." + k] = v
                fieldnames = comboLog.keys()

                if (file_size > maxlogsize) or (runs == 0):
                    filename = "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
                    with open(filename, mode="w", newline="", encoding="utf-8") as file:
                        writer = csv.DictWriter(file, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerow(comboLog)
                        file_size = 0
                        print(1)
                else:
                    with open(filename, mode="a+", newline="", encoding="utf-8") as file:
                        writer = csv.DictWriter(file, fieldnames=fieldnames)
                        writer.writerow(comboLog)
                        # writer.writerows(comboLog)
                        file_size = Path(filename).stat().st_size / 1024
                        #print(2)
                runs = runs + 1
                #print(time.time() - timestamp1, file_size, filename)
                gotime = time.time() + logInterval / 1000
        mySlMini.closeConnection()
        myDgk.closeConnection()



