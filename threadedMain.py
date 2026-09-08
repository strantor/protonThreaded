# Requirements: Python 3.8.5 (SPECIFICALLY - NOT the latest version available) 32 bit (NOT 64 bit)
import pprint
from datetime import datetime, timedelta
import subprocess
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore
from PyQt5.QtGui import QKeySequence
import time
import traceback, sys
# see comment in __init__ of class importedGUI(QtWidgets.QMainWindow, myGUI):
from MainScreen import Ui_MainWindow as myGUI
from PyQt5 import sip
import shutil
import protonModbus
import csv
from pathlib import Path
import usbCheck


# The following 17 new lines of code captures all print() commands and prepends a timestamp onto them
# for assistance in debugging
old_f = sys.stdout
class F:
    nl = True
    logLine = ""
    maxLines = 9999
    logLineNo = maxLines + 1 # to force the creation of a new logfile on first run
    logFilePath = "logs//"
    logFileName = "LogFile " + time.strftime("%Y_%m_%d_%H_%M_%S") + ".txt"
    def write(self, x):
        tm = str(time.strftime('%Y-%m-%d %H:%M:%S'))
        ms = str(time.time() * 1000).split(".")[1].ljust(4, "0")
        timeStamp = "[" + tm + "." + ms + "]    "
        if x == '\n':
            #old_f.write("A")
            self.logLine += (x)
            old_f.write(x)
            self.logMe(self.logLine)
            self.logLine = ""
            self.nl = True
        elif self.nl:
            #old_f.write("B")
            self.logLine += (timeStamp + x)
            old_f.write(timeStamp + x)
            self.nl = False
        else:
            self.logLine += (x)
            #old_f.write("C")
            old_f.write(x)

    def logMe(self,x):
        try:
            if self.logLineNo < self.maxLines:
                self.logLineNo += 1
                logFile = open((self.logFilePath + self.logFileName), "a+")
                logFile.write(str(self.logLineNo).zfill(4) + " " + x)
                logFile.close()
            else:
                self.logFileName = "LogFile " + time.strftime("%Y_%m_%d_%H_%M_%S") + ".txt"
                self.logLineNo = 1
                logFile = open((self.logFilePath + self.logFileName), "w+")
                logFile.write(str(self.logLineNo).zfill(4) + " " + x)
                logFile.close()
        # except:
        #     pass
        except Exception as e:
            print(e)


    def flush(self):
        pass
sys.stdout = F()
# Threading with an imported PyQt5 GUI:
# https://kushaldas.in/posts/pyqt5-thread-example.html
# QRunnable threading in PyQt5:
# https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/

# the following two classes enable us to use the integrated threading function provided in PyQt5, which should
# theoretically be simpler to implement than Python's own threading function, which requires much attention to the
# handling/joining/termination of threads and the specification of thread types and many other considerations. PyQt5
# should be able to handle all of that for us. These two classes simplify the implementation of PyQt5 threads and
# give us easy to use functions to call, and all the magic happens in the background.



class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread. Supported signals are:
    finished: No data
    error: `tuple` (exctype, value, traceback.format_exc() )
    result: `object` data returned from processing, anything
    progress: `int` indicating % progress
    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    outputData = pyqtSignal(list)


class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        # For some reason, in order to get data FROM a threaded function, you must first pass an argument TO
        # the function, in order for it to pass the signal back.
        self.kwargs['outputData'] = self.signals.outputData

    @pyqtSlot()
    def run(self):

        # Initialise the runner function with passed args, kwargs.
        # Retrieve args/kwargs here; and fire processing using them
        if sip.isdeleted(self.signals):
            raise Exception ("The wrapped C/C++ wrapper crash was just narrowly avoided")
        else:
            try:
                result = self.fn(*self.args, **self.kwargs)
            except:
                traceback.print_exc()
                exctype, value = sys.exc_info()[:2]
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            else:
                self.signals.result.emit(result)  # Return the result of the processing
            finally:
                self.signals.finished.emit()  # Done

# The following class is the meat & potatoes of the program. It is where we import the GUI and where we run all the
# functions of the program. We call our functions from the class handling the GUI (PyQt) so that we can make use of
# the PyQt threading functions.



class importedGUI(QtWidgets.QMainWindow, myGUI):

    def __init__(self, *args, **kwargs):
        # Rather than import the entire PyQt5 file and call its own native class, we import only the contents
        # of its UI_MainWindow class and use super() to run it as a new class with inheritance here, so that we can
        # append attributes and apply modifications that ordinarily would have to made in the GUI file.
        super(importedGUI, self).__init__(*args, **kwargs)
        #print("dict: ",self.__dict__)
        # compile the GUI as defined in the imported PyQt5 GUI file
        self.setupUi(self)
        self.show()
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        # add a couple of PyQt elements to our GUI (timer, counter, etc.)
        self.counter = 0
        self.loggingTimer = QTimer()
        self.loggingTimer.setInterval(1000)
        self.loggingTimer.timeout.connect(self.loggingTimerFn)
        self.loggingTimer.start()
        self.logicTimer = QTimer()
        self.logicTimer.setInterval(100)  # 100mS, 10x per second, updating the logic
        self.logicTimer.timeout.connect(self.logicTimerFn)
        self.logicTimer.start()
        #self.tabWidget.setStyleSheet("QTabBar::tab { height: 100px; width: 100px}")
        self.tabWidget.setStyleSheet("""
            QTabBar::tab {
                height: 50px;
                width: 200px;   
                font-size: 12pt;
                font-family: Arial;          
            }
            QTabBar::tab:selected {
                font-size: 14pt;
                font-weight: bold;
            }
        """)
        self.scriptPreviouslyRan = False
        self.initValues()
        self.loadSettings()
        self.loadContainer()
        self.startThreads()
        self.scriptPreviouslyRan = True
        #self.pb_Exit.clicked.connect(self.close)


    def startThreads(self):
        self.loggingTimer.setInterval(self.csvLogInterval)
        if self.usbExecute == "1":
            self.usbFn_Start()
        if self.threadedFunctionAExecute == "1":
            print("A")
            self.threadedFunctionA_Start()
        if self.slMiniExecute == "1":
            print("B")
            self.slMiniFn_Start()
        if self.dgkExecute == "1":
            print("C")
            self.dgkFn_Start()
        if self.serialDeviceExecute == "1":
            print("D")
            self.threadedFunctionC_Start()



    def initValues(self):
        self.pbReloadSettings.clicked.connect(self.loadSettings)
        self.pbRefreshValues.clicked.connect(self.refreshDataWidget)
        self.tabWidget.setCurrentIndex(0)
        self.treeWidget.setColumnCount(4)
        self.treeWidget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        #self.treeWidget.verticalScrollBar.setSingleStep(5)
        self.treeWidget.setHeaderLabels(["Tag Name","Data Type","Current Value","Tier"])
        self.treeWidget.setColumnWidth(0,400)
        self.treeWidget.setColumnWidth(1,200)
        self.treeWidget.setColumnWidth(2,300)
        self.treeWidget.setColumnWidth(3,50)
        self.treeWidget.setSortingEnabled(True)
        self.shortcut1 = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut1.activated.connect(self.kbdShortcutDisplayData)
        self.shortcut2 = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut2.activated.connect(self.loadSettings)
        # self.setMaximumHeight(1080)
        # self.setMaximumWidth(1920)
        # # Ensure Maximize button is explicitly requested
        # self.setWindowFlags(
        #     Qt.Window |
        #     Qt.WindowMinMaxButtonsHint |  # Enables both Min and Max buttons
        #     Qt.WindowCloseButtonHint
        # )
        # self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        #self.setMaximumSize(16777215, 16777215)



        # TEST FUNCTION
        # *args list passed to testThreadedFn
        # [A, B, C, D] A = has ran, B = print output, C = # times ran, D= multiplier
        print("initValues")
        self.threadedFunctionAHasRan = 0
        self.threadedFunctionAPrintOutput = 1
        self.threadedFunctionATimesRan = 0
        self.threadedFunctionAMultiplier = 2.5
        # Gui variables associated with testThreadedFn
        self.testThreadedFnTimeFirstRan = 0
        self.threadedFunctionAErrors = 0

        # SL Mini (footage counter) Function
        self.csvLogDict = {}
        self.deviceDataDict = {}
        self.slMiniRuns = 0

        # DGK (laser micrometer) function
        self.dgkRuns = 0
        self.connectedToDgk = False
        self.dgkObject = 0
        self.lastDgkCall = 0
        self.file_size = 0
        self.filename = "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
        self.csvLogPath = ""
        self.csvLogPathLast = ""
        self.csvLogLineCount = 0

        # USB function
        self.usbObject = 0
        self.usbReady = False
        self.lastDgkCall = 0
        self.usbRuns = 0
        self.usbMountPoint = None
        self.usbHasRan = False


        # logic/other
        # self.revNo = str(subprocess.check_output(["git", "describe", "--always"]).strip()).lstrip("b'").rstrip("'") + "  ("
        # self.revNo += str(subprocess.check_output(["git", "show", "-s", "--format=%ci"]).strip()).lstrip("b'").rstrip("'") + ")"
        # print("ThreadedApp rev#",self.revNo)
        self.connectedToSlMini = False
        self.slMiniObject = 0
        self.lastSlMiniCall = 0
        self.connectedToSerialDevice = False
        self.serialDeviceObject = 0
        self.serialDeviceReadFails = 0




    def loadContainer(self):
        # for reading in bools as txt
        def str2bool(val):
            if val in ["True", "1"]:
                val = True
            elif val in ["False", "0"]:
                val = False
            else:
                raise Exception("non-binary number loaded on init")
            return val

        # format values read in from container
        try:
            # if the script is terminated while the saveToContainer() function is executing, it will wipe out the
            # container file. Then upon re-launch of the script, it will throw an exception on the following lines
            # (before it gets to the part about overwriting the backup file with the current (fucked) file). If no
            # exception is thrown, then current is copied to backup, and the show goes on. If exception IS thrown, then
            # we load from backup instead. This backup data is only ever written on _init_ of the script, so if the
            # script ran for days or weeks before it was restarted, then this data may be old AF and they might have to
            # run a cleanout or something. Tough shit. Run your cleanout and move on, the data will work itself out.
            #TODO: get rid of this and saveToContainer all varaibles as a dict and read them back in upon relaunch as
            # a dict with ast.literal
            containerFile = open('container', 'r')
            for line in containerFile:
                if ':' in line:
                    parameter, value = line.split('::')
                    garbage, parameter = parameter.split('[')
                    value, garbage = value.split(']')
                    try:
                        newvalue = str2bool(value)
                        value = newvalue
                    except:
                        try:
                            newvalue = int(value)
                            value = newvalue
                        except:
                            pass
                    print("self." + parameter + " ==", value, type(value))
                    setattr(self, parameter, value)  # this assigns new attributes to the importedGUI class
            containerFile.close()
            shutil.copyfile('container',
                            'containerBackup')
        except:
            print("container file was corrupted on last exit. loading container from backup file instead...")
            containerFile = open('containerBackup', 'r')
            for line in containerFile:
                if ':' in line:
                    parameter, value = line.split('::')
                    garbage, parameter = parameter.split('[')
                    value, garbage = value.split(']')
                    print("self." + parameter + " ==", value)
                    setattr(self, parameter, value)  # this assigns new attributes to the importedGUI class
            containerFile.close()
            self.izarDayLastRebooted = int(self.izarDayLastRebooted)
        # if "parameterA" not in self.__dict__:
        #     self.parameterA = True
        # if "parameterB" not in self.__dict__:
        #     self.parameterB = "True"
        # if "parameterC" not in self.__dict__:
        #     self.parameterC = 50
        # if "parameterD" not in self.__dict__:
        #     self.parameterD = None
        # if "parameterE" not in self.__dict__:
        #     self.parameterE = 500.17
        self.parameterB = str(self.parameterB)
        self.parameterC = int(self.parameterC)
        self.parameterE = float(self.parameterE)


    def loadSettings(self):
        try:
            print("reloading settings...")
            # Import settings from settings File
            settingsFile = open('settings.txt','r')
            for line in settingsFile:
                if ':' in line:
                    parameter,value = line.split('::')
                    parameter = parameter.split('[')[1]
                    value  = value.split(']')[0]
                    if parameter == 'csvLogInterval':
                        value = int(value)
                    if parameter == "csvLogMaxSize":
                        value = int(value)*1024
                    if parameter == "csvLogMaxLineCount":
                        value = int(value)
                    print("self." + parameter + " ==",value, type(value))
                    setattr(self,parameter,value) # this assigns new attributes to the importedGUI class
            settingsFile.close()
            self.allDataTabVisible = True
            print("settings loaded successfully")

            #self.startThreads()
        except Exception:
            print(traceback.format_exc(),"_G")

    def kbdShortcutDisplayData(self):
        if self.allDataTabVisible == True:
            self.tabWidget.setTabVisible(6, False)
            self.allDataTabVisible = False
        elif self.allDataTabVisible == False:
            self.tabWidget.setTabVisible(6, True)
            self.allDataTabVisible = True


    def refreshDataWidget(self):
        if self.allDataTabVisible == True:
            self.treeWidget.clear()
            self.printTree(self.__dict__, self.treeWidget)
            self.treeWidget.sortItems(0,Qt.AscendingOrder)




    def printTree(self,input,whichWidget):
        hasprinted = []#False
        maxTier = 8
        excludeList = ["password","clientSecret","sensitiveInfo"]
        print("2")
        def recursDict(parent,data):
            tier = int(parent.text(3))
            if tier < maxTier:
                for k,v in data.items():
                    #print(k)
                    if str(k) not in excludeList:
                        a = QTreeWidgetItem([str(k), str(type(v)),"",str(tier+1)])
                        parent.addChild(a)
                        #parent.setExpanded(True)
                        if isinstance(v,dict):  # [list,dict,tuple]:
                            recursDict(a, v)
                        elif isinstance(v, list):
                            recursList(a, v)
                        else:
                            if hasattr(v, '__dict__'):
                                recursDict(a, v.__dict__)
                            else:
                                a.setText(2, str(v))
            else:
                if "false" not in hasprinted:
                    txt = parent.text(0)
                    newparent = parent
                    #txt += parent.text(0)
                    for i in range(0,maxTier):
                        txt = newparent.text(0) + "\\" + txt
                        newparent = newparent.parent()
                    txt = "max tier exceeded:" + txt
                    print(txt,"_H")
                    hasprinted.append("false")
        def recursList(parent,data):
            tier = int(parent.text(3))
            if tier < maxTier:
                for v in data:

                    k = "List item of [" + parent.text(0) + "]"
                    a = QTreeWidgetItem([str(k), str(type(v)),str(v),str(tier+1)])
                    parent.addChild(a)
                    #parent.setExpanded(True)
                    if isinstance(v,dict):  # [list,dict,tuple]:
                        recursDict(a, v)
                    elif isinstance(v,list):
                        recursList(a,v)
                    else:
                        if hasattr(v, '__dict__'):
                            recursDict(a, v.__dict__)
                        else:
                            a.setText(2, str(v))
            else:
                if "false" not in hasprinted:
                    txt = parent.text(0)
                    newparent = parent
                    #txt += parent.text(0)
                    for i in range(0,maxTier):
                        txt = newparent.text(0) + "\\" + txt
                        newparent = newparent.parent()
                    txt = "max tier exceeded:" + txt
                    print(txt,"_I")
                    hasprinted.append("false")


        for k,v in input.items():
            try:
                if str(k) not in excludeList:
                    a = QTreeWidgetItem([str(k), str(type(v)),"","1"])
                    whichWidget.addTopLevelItem(a)
                    if isinstance(v,dict):#[list,dict,tuple]:
                        recursDict(a,v)
                    elif isinstance(v, list):
                        recursList(a, v)
                    else:
                        if hasattr(v,'__dict__'):
                            recursDict(a, v.__dict__)
                        else:
                            a.setText(2, str(v))
                            #a.setText(3, "1")
            except Exception as e:
                print(k,v,e,"_L")



    def logicTimerFn(self):
        if self.usbReady == True:
            self.csvLogPath = self.usbMountPoint
        else:
            self.csvLogPath = "//home//proton//csvLogs//"
        # if self.csvLogPath == self.csvLogPathLast:
        #     print("self.csvLogPath = None")
        # Establish logical conditions for operation
        # Only instant operations here (logic state changes, label text changes, etc.), no timed operations or threaded
        # operations, or operations that take time, because this function is called on a timer every 100mS
        vars2save = {}
        try:
            vars2save["parameterA"] = self.parameterA
            vars2save["parameterB"] = self.parameterB
            vars2save["parameterC"] = self.parameterC
            vars2save["parameterD"] = self.parameterD
            vars2save["parameterE"] = self.parameterE
        except Exception as e:
            print(e)
        self.saveMultiToContainter(vars2save)




    def saveMultiToContainter(self, inpDict):
        containerFile = open('container', 'r')
        linelist = containerFile.readlines()
        containerFile.close()
        for varname, val in inpDict.items():
            if "self." in varname:
                varname = varname.split("self.")[1]
            searchterm = "[" + varname + "::"
            i = 0
            hits = 0
            for line in linelist:
                i += 1
                if searchterm in line:
                    hits += 1
                    # print("old line", line)
                    left, right = line.split(searchterm)
                    rightlist = right.split(']')
                    oldval, post = rightlist[0], rightlist[1]
                    newline = left + searchterm + str(val) + "]" + post
                    # print("new line:",newline)
                    linelist[i - 1] = newline
            if hits == 0:
                newline = "\n" + searchterm + str(val) + "]"
                linelist.append(newline)
                print("new variable saved to container:",newline)
        containerFile = open('container', 'w')
        containerFile.writelines(linelist)
        containerFile.close()


    def threadedFunctionA_Start(self):
        if self.threadedFunctionAExecute:
            #print("AAAAAAAAAA")
            # Pass the function to execute
            # *args list passed to test function
            threadedFunctionAInputData = [self.threadedFunctionAHasRan,
                                       self.threadedFunctionAPrintOutput,
                                       self.threadedFunctionATimesRan,
                                       self.threadedFunctionAMultiplier]
            worker = Worker(self.threadedFunctionA, threadedFunctionAInputData)  # Any other args, kwargs are passed to the run function
            worker.signals.outputData.connect(self.threadedFunctionA_HandleOutputs)
            worker.signals.result.connect(self.threadedFunctionA_Result)
            worker.signals.finished.connect(self.threadedFunctionA_Finished)
            worker.signals.error.connect(self.threadedFunctionA_Error)
            # Execute
            self.threadpool.start(worker)

    def threadedFunctionA(self, inputData, outputData):

        # WE CANNOT DIRECTLY INFLUENCE THE GUI FROM THIS FUNCTION OR ANY FUNCTION THAT IT CALLS, BECAUSE IT (AND
        # ANY IT CALLS) RUNS IN A SEPARATE THREAD. INSTEAD WE MUST USE SIGNALS TO PASS DATA BACK TO THE UI THREAD,
        # AND FUNCTIONS RUNNING IN THE UI THREAD TO CHANGE VALUES IN THE UI

        # Example of collecting input data passed to the thread as arguments, and sending data out by emitting signals
        #print("running threadedFunctionA")
        hasran = inputData[0]
        printOutput = inputData[1]
        timesran = inputData[2]
        multiplier = inputData[3]
        if hasran == 0:
            outputData.emit(["First Run", time.time()])
        else:
            outputData.emit(["subsequent run", time.time()])
        if timesran < 3:
            for n in range(0, 5):
                outputData.emit(["math",(timesran+1)*n*multiplier])
                time.sleep(1)
        # else:
        #     outputData.emit(["math", 1/0]) # deliberately create an error

        #err = 8/0
        return "all done"

    def threadedFunctionA_Result(self, s):
        #print("Result:", s)
        pass

    def threadedFunctionA_Finished(self):
        self.threadedFunctionAHasRan = 1
        self.threadedFunctionATimesRan += 1
        #print("THREAD COMPLETE!")
        self.threadedFunctionA_Start()

    def threadedFunctionA_HandleOutputs(self, n):
        # this gets called (in the main GUI thread) at various points during the execution of the threaded
        # function. The threaded function emits a list, with item[0] being an identifier so we know WHAT
        # information is being relayed to us, followed by the data.
        #print(n,"_J")

        if n[0] == "First Run":
            self.testThreadedFnTimeFirstRan = n[1]
            print("testThreadedFn is on its first run, time: ",self.testThreadedFnTimeFirstRan)
        elif n[0] == "subsequent run":
            timethisrun = str(n[1])
            #print("testThreadedFn starting another run, time: ", timethisrun)
        elif n[0] == "math":
            math = str(n[1])
            #print(math,"_K")


    def threadedFunctionA_Error(self, error):
        # Reset everything on error
        self.threadedFunctionAHasRan = 0
        self.threadedFunctionAErrors += 1
        self.threadedFunctionATimesRan = 0
        #self.testThreadedFn_Start()
        print("Error in testThreadedFn!:", error)



    # this function gets called each time the QTimer() times out, and increments the display count. Since the QTimer()
    # is a PyQt5 function, it seems to follow its own native threading provision and does not block the execution of
    # the GUI like using time.sleep(1) would.

    def loggingTimerFn(self):
        self.counter += 1
        timestamp1 = time.time()
        self.csvLogDict['timestamp'] = str(time.strftime('%Y-%m-%d %H:%M:%S'))
        fieldnames = self.csvLogDict.keys()

        #print(fieldnames)

        # if ((self.file_size > self.csvLogMaxSize) or\
        #         (self.dgkRuns == 0) or\
        #         (self.slMiniRuns == 0) or\
        #         (self.csvLogLineCount > self.csvLogMaxLineCount)):
        #     print("gothere")
        newFile = False
        if (self.csvLogPath != self.csvLogPathLast):
            print("(self.csvLogPath != self.csvLogPathLast)")
            newFile = True
            self.csvLogPathLast = self.csvLogPath
        if (self.file_size > self.csvLogMaxSize):
            print("newFile = True (self.file_size > self.csvLogMaxSize)")
            newFile = True
        if (self.dgkRuns == 1):
            print("newFile = True (self.dgkRuns == 1)")
            newFile = True
        if (self.slMiniRuns == 1):
            print("newFile = True (self.slMiniRuns == 1)")
            newFile = True
        if (self.csvLogLineCount > self.csvLogMaxLineCount):
            print("newFile = True (self.csvLogLineCount > self.csvLogMaxLineCount)")
            newFile = True
        if newFile:
            self.filename = self.csvLogPath + "LOG_" + str(time.strftime('%Y.%m.%d.%H.%M.%S')) + '.csv'
            print("Now logging to",self.filename)
            with open(self.filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(self.csvLogDict)
                self.file_size = 0
                self.csvLogLineCount = 0
        else:
            with open(self.filename, mode="a+", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writerow(self.csvLogDict)
                self.file_size = Path(self.filename).stat().st_size / 1024
                file.seek(0) #go to beginning of file so we can count the lines
                self.csvLogLineCount = sum(1 for line in file)
        #print(time.time() - timestamp1, self.file_size, self.filename,self.csvLogLineCount)





    def usbFn_Start(self):
        if self.usbExecute == "1":
            if self.usbReady == False:
                self.lbl_usbReady.setText("USB Thumb drive ready?: NO")
                self.lbl_usbReady.setStyleSheet('background-color : red')
                self.lbl_logLoc.setText("CSV Log Location: "+self.filename)
            else:
                self.lbl_usbReady.setText("USB Thumb drive ready?: YES")
                self.lbl_usbReady.setStyleSheet('background-color : green')
            usbFnInputData = [self.usbReady,
                              self.usbObject,
                              self.usbHasRan]
            worker = Worker(self.usbFn, usbFnInputData)  # Any other args, kwargs are passed to the run function
            worker.signals.outputData.connect(self.usbFn_HandleOutputs)
            worker.signals.result.connect(self.usbFn_Result)
            worker.signals.finished.connect(self.usbFn_Finished)
            worker.signals.error.connect(self.usbFn_Error)
            self.threadpool.start(worker)

    def usbFn(self, inputData, outputData):
        usbReady = inputData[0]
        usbObject = inputData[1]
        usbHasRan = inputData[2]

        if usbHasRan == False:
            print("Instantiating USBWatcher")
            watcher = usbCheck.USBWatcher()
            outputData.emit(["usbHasRan", True])
        else:
            watcher = usbObject
        watcher.check_existing_drives()
        watcher.usbMounted
        watcher.mountPoint
        # watcher.start_listening()
        outputData.emit(["mountPoint", watcher.mountPoint])
        outputData.emit(["usbObject", watcher])
        outputData.emit(["usbReady", watcher.usbMounted])

    def usbFn_Result(self, s):
        pass

    def usbFn_Finished(self):
        self.usbFn_Start()

    def usbFn_HandleOutputs(self, n):
        if n[0] == "usbReady":
            self.usbReady = n[1]
        elif n[0] == "usbObject":
            self.usbObject = n[1]
        elif n[0] == "mountPoint":
            self.usbMountPoint = n[1]
        elif n[0] == "usbHasRan":
            self.usbHasRan = n[1]

    def usbFn_Error(self, error):
        # Reset everything on error
        self.usbReady = False
        print("Error in usbFn!:", error)
        

    def slMiniFn_Start(self):
        if self.slMiniExecute == "1":
            # print("slMiniFn_Started")
            # At the start of the function we evaluate all the data set from the last running of the function, form
            # our arguments for the next run, and begin the next run passing those arguments in.
            
            # from here we can manipulate the UI but not from within the threaded function

            if self.connectedToSlMini == False:
                self.lbl_conn2SlMini.setText("Connected to SL Mini Footage Counter?: NO")
                self.lbl_conn2SlMini.setStyleSheet('background-color : red')
            else:
                self.lbl_conn2SlMini.setText("Connected to SL Mini Footage Counter?: Yes")
                self.lbl_conn2SlMini.setStyleSheet('background-color : green')
            # Pass the function to execute
            # *args list passed to test function

            slMiniFnInputData = [self.connectedToSlMini,
                               self.slMiniObject,
                               self.lastSlMiniCall,
                               self.slMiniIP,
                               self.csvLogInterval]
            worker = Worker(self.slMiniFn, slMiniFnInputData)  # Any other args, kwargs are passed to the run function
            worker.signals.outputData.connect(self.slMiniFn_HandleOutputs)
            worker.signals.result.connect(self.slMiniFn_Result)
            worker.signals.finished.connect(self.slMiniFn_Finished)
            worker.signals.error.connect(self.slMiniFn_Error)
            # Execute

            self.threadpool.start(worker)


    def slMiniFn(self, inputData, outputData):

        # WE CANNOT DIRECTLY INFLUENCE THE GUI FROM THIS FUNCTION OR ANY FUNCTION THAT IT CALLS, BECAUSE IT (AND
        # ANY IT CALLS) RUNS IN A SEPARATE THREAD. INSTEAD WE MUST USE SIGNALS TO PASS DATA BACK TO THE UI THREAD,
        # AND FUNCTIONS RUNNING IN THE UI THREAD TO CHANGE VALUES IN THE UI
        # We are operating inside a separate thread so it's OK to waste time here, but nowhere else
        # We don't want to incorporate any error handling here [try:, except:] because we want the worker class
        # to emit the error signal so we can handle it in another function
        # THERE CAN BE NO "SELF.SOMETHING" IN THIS FUNCTION BECAUSE THAT REFERS TO THE GUI WHICH IS RUNNING IN
        # A SEPARATE THREAD. WE MUST USE SIGNALS TO GET THAT DATA BACK TO THE GUI
        # Example of collecting input data passed to the thread as arguments, and sending data out by emitting signals
        connectedToSlMini = inputData[0]
        slMiniObject = inputData[1]
        lastSlMiniCall = inputData[2]
        slMiniIP = inputData[3]
        csvLogInterval = inputData[4]
        #print("running slMiniFn")
        if time.time() > lastSlMiniCall:

            if connectedToSlMini == False:
                print("not connected to SL Mini. attempting connection")
                # Now that we are creating the SL Mini object inside a thread that will terminate and not be reused, we
                # will lose the mySL Mini object, along with its tokens, sessions, everything, which would cause us to
                # have to  re-negotiate a new secure session every time we re-run the function (which is continuously
                # re-ran), so to get around this obstacle, we create the object/session/token once, and then we emit the
                # mySL Mini object as a signal back to the GUI thread for safekeeping, and it will pass that object back as
                # an argument to this function on the next go-round.
                mySlMini = protonModbus.protonModbus(ip=slMiniIP)
                mySlMini.start()
                mySlMini.parseSlMiniOutput()
                outputData.emit(["result", mySlMini.logDict])
                outputData.emit(["wholeDict", [mySlMini.slMiniDict,mySlMini.slMiniLogOptions]])
                outputData.emit(["slMiniObject", mySlMini])
                outputData.emit(["connectedToSlMini", 1])
                lastSlMiniCall = time.time() + (csvLogInterval/1000)
                outputData.emit(["lastSlMiniCall", lastSlMiniCall])
                #print("success1")
            else:
                #print("run2")
                mySlMini = slMiniObject
                mySlMini.parseSlMiniOutput()
                outputData.emit(["result", mySlMini.logDict])
                outputData.emit(["wholeDict", [mySlMini.slMiniDict,mySlMini.slMiniLogOptions]])
                outputData.emit(["slMiniObject", mySlMini])
                lastSlMiniCall = time.time() + (csvLogInterval/1000)
                outputData.emit(["lastSlMiniCall", lastSlMiniCall])
                #print("success2")

    def slMiniFn_Result(self, s):
        pass

    def slMiniFn_Finished(self):
        self.slMiniFn_Start()

    def slMiniFn_HandleOutputs(self, n):
        # this gets called (in the main GUI thread) at various points during the execution of the threaded
        # function. The threaded function emits a list, with item[0] being an identifier so we know WHAT
        # information is being relayed to us, followed by the data.
        # print(n)
        if n[0] == "connectedToSlMini":
            self.connectedToSlMini = n[1]
        elif n[0] == "slMiniObject":
            self.slMiniObject = n[1]
        elif n[0] == "lastSlMiniCall":
            self.lastSlMiniCall = n[1]
        elif n[0] == "result":
            result = n[1]
            self.slMiniRuns += 1
            #print("slminiruns: ", self.slMiniRuns)
            if type(result) == dict:
                for k, v in result.items():
                    self.csvLogDict["foot." + k] = v
                #pprint.pprint(self.csvLogDict)
        elif n[0] == "wholeDict":
            result,yesNos = n[1]
            if type(result) == dict:

                # 1. Clear existing items from grid layouts (Optional but recommended)
                for layout in (self.gridLayout_33, self.gridLayout_32,self.gridLayout_30):
                    while layout.count():
                        item = layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()

                # 2. Iterate and populate labels
                LIGHT_STYLE = "background-color: #f9f9f9; color: #333333;"
                DARK_STYLE = "background-color: #e0e0e0; color: #111111;"
                for row, (key, value) in enumerate(result.items()):
                    current_style = LIGHT_STYLE if row % 2 == 0 else DARK_STYLE
                    # Create key label -> gridLayout_8
                    key_label = QLabel(str(key))
                    key_label.setStyleSheet(current_style)
                    self.gridLayout_33.addWidget(key_label, row, 0)
                    # Create value label -> gridLayout_7
                    value_label = QLabel(str(value))
                    value_label.setStyleSheet(current_style)
                    self.gridLayout_32.addWidget(value_label, row, 0)
                    if key in yesNos:
                        thirdColumn = "Yes"
                    else:
                        thirdColumn = "No"
                    yesNo_label = QLabel(thirdColumn)
                    yesNo_label.setStyleSheet(current_style)
                    self.gridLayout_30.addWidget(yesNo_label, row, 0)


    def slMiniFn_Error(self, error):
        # Reset everything on error
        self.connectedToSlMini = False
        #self.fWebFn_Start()
        print("Error in slMiniFn!:", error)







    def dgkFn_Start(self):
        if self.dgkExecute == "1":
            # print("dgkFn_Started")
            # At the start of the function we evaluate all the data set from the last running of the function, form
            # our arguments for the next run, and begin the next run passing those arguments in.

            # from here we can manipulate the UI but not from within the threaded function

            if self.connectedToDgk == False:
                self.lbl_conn2Dgk.setText("Connected to DGK Laser Micrometer?: NO")
                self.lbl_conn2Dgk.setStyleSheet('background-color : red')
            else:
                self.lbl_conn2Dgk.setText("Connected to DGK Laser Micrometer?: Yes")
                self.lbl_conn2Dgk.setStyleSheet('background-color : green')
            # Pass the function to execute
            # *args list passed to test function

            dgkFnInputData = [self.connectedToDgk,
                               self.dgkObject,
                               self.lastDgkCall,
                               self.dgkIP,
                               self.csvLogInterval]
            worker = Worker(self.dgkFn, dgkFnInputData)  # Any other args, kwargs are passed to the run function
            worker.signals.outputData.connect(self.dgkFn_HandleOutputs)
            worker.signals.result.connect(self.dgkFn_Result)
            worker.signals.finished.connect(self.dgkFn_Finished)
            worker.signals.error.connect(self.dgkFn_Error)
            # Execute

            self.threadpool.start(worker)

    def dgkFn(self, inputData, outputData):
        # WE CANNOT DIRECTLY INFLUENCE THE GUI FROM THIS FUNCTION OR ANY FUNCTION THAT IT CALLS, BECAUSE IT (AND
        # ANY IT CALLS) RUNS IN A SEPARATE THREAD. INSTEAD WE MUST USE SIGNALS TO PASS DATA BACK TO THE UI THREAD,
        # AND FUNCTIONS RUNNING IN THE UI THREAD TO CHANGE VALUES IN THE UI
        # We are operating inside a separate thread so it's OK to waste time here, but nowhere else
        # We don't want to incorporate any error handling here [try:, except:] because we want the worker class
        # to emit the error signal so we can handle it in another function
        # THERE CAN BE NO "SELF.SOMETHING" IN THIS FUNCTION BECAUSE THAT REFERS TO THE GUI WHICH IS RUNNING IN
        # A SEPARATE THREAD. WE MUST USE SIGNALS TO GET THAT DATA BACK TO THE GUI
        # Example of collecting input data passed to the thread as arguments, and sending data out by emitting signals
        connectedToDgk = inputData[0]
        dgkObject = inputData[1]
        lastDgkCall = inputData[2]
        dgkIP = inputData[3]
        csvLogInterval = inputData[4]
        # print("running dgkFn")
        if time.time() > lastDgkCall:

            if connectedToDgk == False:
                print("not connected to DGK. attempting connection")
                # Now that we are creating the DGK object inside a thread that will terminate and not be reused, we
                # will lose the myDGK object, along with its tokens, sessions, everything, which would cause us to
                # have to  re-negotiate a new secure session every time we re-run the function (which is continuously
                # re-ran), so to get around this obstacle, we create the object/session/token once, and then we emit the
                # myDGK object as a signal back to the GUI thread for safekeeping, and it will pass that object back as
                # an argument to this function on the next go-round.
                myDgk = protonModbus.protonModbus(ip=dgkIP)
                myDgk.start()
                myDgk.parseDgkOutput()
                outputData.emit(["result", myDgk.logDict])
                outputData.emit(["wholeDict", [myDgk.dgkDict, myDgk.dgkLogOptions]])
                outputData.emit(["dgkObject", myDgk])
                outputData.emit(["connectedToDgk", 1])
                lastDgkCall = time.time() + (csvLogInterval/1000)
                outputData.emit(["lastDgkCall", lastDgkCall])
                # print("success1")
            else:
                # print("run2")
                myDgk = dgkObject
                myDgk.parseDgkOutput()
                outputData.emit(["result", myDgk.logDict])
                outputData.emit(["wholeDict", [myDgk.dgkDict, myDgk.dgkLogOptions]])
                outputData.emit(["dgkObject", myDgk])
                lastDgkCall = time.time() + (csvLogInterval/1000)
                outputData.emit(["lastDgkCall", lastDgkCall])
                # print("success2")

    def dgkFn_Result(self, s):
        pass

    def dgkFn_Finished(self):
        self.dgkFn_Start()

    def dgkFn_HandleOutputs(self, n):
        # this gets called (in the main GUI thread) at various points during the execution of the threaded
        # function. The threaded function emits a list, with item[0] being an identifier so we know WHAT
        # information is being relayed to us, followed by the data.
        # print(n)
        if n[0] == "connectedToDgk":
            self.connectedToDgk = n[1]
        elif n[0] == "dgkObject":
            self.dgkObject = n[1]
        elif n[0] == "lastDgkCall":
            self.lastDgkCall = n[1]
        elif n[0] == "result":
            result = n[1]
            self.dgkRuns += 1
            # print("dgkRuns: ", self.dgkRuns)
            if type(result) == dict:
                for k, v in result.items():
                    self.csvLogDict["mic." + k] = v
                # pprint.pprint(self.csvLogDict)
        elif n[0] == "wholeDict":
            result, yesNos = n[1]
            if type(result) == dict:

                # 1. Clear existing items from grid layouts (Optional but recommended)
                for layout in (self.gridLayout_25, self.gridLayout_26, self.gridLayout_27):
                    while layout.count():
                        item = layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()

                # 2. Iterate and populate labels
                LIGHT_STYLE = "background-color: #f9f9f9; color: #333333;"
                DARK_STYLE = "background-color: #e0e0e0; color: #111111;"
                for row, (key, value) in enumerate(result.items()):
                    current_style = LIGHT_STYLE if row % 2 == 0 else DARK_STYLE
                    # Create key label -> gridLayout_8
                    key_label = QLabel(str(key))
                    key_label.setStyleSheet(current_style)
                    self.gridLayout_26.addWidget(key_label, row, 0)
                    # Create value label -> gridLayout_7
                    value_label = QLabel(str(value))
                    value_label.setStyleSheet(current_style)
                    self.gridLayout_27.addWidget(value_label, row, 0)
                    if key in yesNos:
                        thirdColumn = "Yes"
                    else:
                        thirdColumn = "No"
                    yesNo_label = QLabel(thirdColumn)
                    yesNo_label.setStyleSheet(current_style)
                    self.gridLayout_25.addWidget(yesNo_label, row, 0)

    def dgkFn_Error(self, error):
        # Reset everything on error
        self.connectedToDgk = False
        # self.fWebFn_Start()
        print("Error in dgkFn!:", error)





    def threadedFunctionC_Start(self):
        if self.serialDeviceExecute == "1":
            # Pass the function to execute
            # *args list passed to test function
            threadedFunctionCInputData = [self.connectedToSerialDevice,
                                 self.serialDeviceObject,
                                 self.serialDeviceCOMport,
                                 self.serialDeviceBaud,
                                 self.serialDeviceReadFails]
            worker = Worker(self.threadedFunctionC, threadedFunctionCInputData)  # Any other args, kwargs are passed to the run function
            worker.signals.outputData.connect(self.threadedFunctionC_HandleOutputs)
            worker.signals.result.connect(self.threadedFunctionC_Result)
            worker.signals.finished.connect(self.threadedFunctionC_Finished)
            worker.signals.error.connect(self.threadedFunctionC_Error)
            # Execute
            self.threadpool.start(worker)

    def threadedFunctionC(self, inputData, outputData):
        #time.sleep(1)
        # WE CANNOT DIRECTLY INFLUENCE THE GUI FROM THIS FUNCTION OR ANY FUNCTION THAT IT CALLS, BECAUSE IT (AND
        # ANY IT CALLS) RUNS IN A SEPARATE THREAD. INSTEAD WE MUST USE SIGNALS TO PASS DATA BACK TO THE UI THREAD,
        # AND FUNCTIONS RUNNING IN THE UI THREAD TO CHANGE VALUES IN THE UI
        # We are operating inside a separate thread so it's OK to waste time here, but nowhere else
        # We don't want to incorporate any error handling here [try:, except:] because we want the worker class
        # to emit the error signal so we can handle it in another function
        # THERE CAN BE NO "SELF.SOMETHING" IN THIS FUNCTION BECAUSE THAT REFERS TO THE GUI WHICH IS RUNNING IN
        # A SEPARATE THREAD. WE MUST USE SIGNALS TO GET THAT DATA BACK TO THE GUI
        # Example of collecting input data passed to the thread as arguments, and sending data out by emitting signals
        connectedToSerialDevice = inputData[0]
        serialDeviceObject = inputData[1]
        serialDeviceCOMport = inputData[2]
        serialDeviceBaud = inputData[3]
        serialDeviceReadFails = inputData[4]
        print("running threadedFunctionC")
        if connectedToSerialDevice == False:
            time.sleep(2)

            # Due to the way the serial module is handled, on the first scan the COM port is opened and remains open.
            # Future attempts to reestablish serial comms with the module (if lost) result in a permission error.
            # To avoid this we must detect if the COM port has previously been opened, and if so, close it, delete the
            # mySerialDevice object, create a new one, and reopen the COM port

            # Firstly, detect if the serialDeviceObject(*) exists as an actual object, or as an integer 0.

            # (*) We address the serialDevice object as serialDeviceObject instead of mySerialDevice, because that is the format
            # in which it has been passed into this thread/function from the main GUI thread. Later, once integrity of
            # the provided serialDevice object has been verified, we will create an object named mySerialDevice and assign
            # serialDeviceObject to it. Or, if integrity has been lost, we will destroy the old serialDevice object (serialDeviceObject)
            # and create a new serialDevice object (myserialDevice). In any case, the serialDevice object (whether it be an
            # integer 0 or a real object) is passed into this thread/function under the name serialDeviceObject, while it's
            # here it goes by mySerialDevice, and turns back into serialDeviceObject on its way out.

            if serialDeviceObject == 0:
                print("not connected to serialDevice. attempting connection")
                mySerialDevice = serialDevice.connect(serialDeviceCOMport)
                bailOut = False
                # we have to use a try/except here because for some reason the timeout-on-ping exception does not seem to
                # fully propagate up to this thread. When the timeout-on-ping happens, it terminates the thread but the
                # mySerialDevice object stays in memory, waiting on a ping response, while the serialDevice thread gets
                # re-queued in the thread pool and when it runs again, there are two mySerialDevice objects trying to
                # access the same com port, resulting in a perpetual PermissionError(13, \'Access is denied.\', None, 5)
                # .  and
                try:
                    confirmation = mySerialDevice.ping()
                    if confirmation == True:
                        connectedToSerialDevice = True
                        print("Successfully connected to serialDevice")
                        outputData.emit(["serialDeviceObject", mySerialDevice])
                        outputData.emit(["connectedToSerialDevice", connectedToSerialDevice])
                    else:
                        bailOut = True

                except Exception as e:
                    print(e,"_C")
                    bailOut = True
                if bailOut == True:
                    print("No response to serialDevice Ping")
                    mySerialDevice.serialDeviceSerial.close()
                    del mySerialDevice
                    outputData.emit(["serialDeviceObject", 0])
                    outputData.emit(["connectedToSerialDevice", 0])

            else:
               #print("serialDeviceObject was not 0.")
                try:
                    #print("serialDevice connection status:", serialDeviceObject.serialDeviceSerial.isOpen())
                    #print("Attempting to close serialDevice connection")
                    serialDeviceObject.serialDeviceSerial.close()
                    #print("serialDeviceObject.serialDeviceSerial.close() seems to have worked")
                    if serialDeviceObject.serialDeviceSerial.isOpen():
                        print("Failed to close connection")
                        # if the serialDevice connection refuses to close, pass the serialDeviceObject back to the GUI thread so
                        # that we can try again next time. We only want to destroy the serialDeviceObject when we know for
                        # sure that the connection has been closed, otherwise the serial port will be permanently
                        # locked and we'll get the perpetual permissionError Exception
                        outputData.emit(["serialDeviceObject", serialDeviceObject])
                        outputData.emit(["connectedToSerialDevice", 0])
                    else:
                        print("successfully closed the connection")
                        del serialDeviceObject
                        outputData.emit(["serialDeviceObject", 0])
                        outputData.emit(["connectedToSerialDevice", 0])
                    print("COM port was open, now it's closed")
                except Exception as e:
                    print("Failed to close COM port:", e)
        else:
            #print("Already connected to serialDevice. attempting to retrieve data")
            mySerialDevice = serialDeviceObject
            confirmation = mySerialDevice.pingPrinter()
            if confirmation == True:
                try:
                    mySerialDevice.getMessage(1)
                    mySerialDevice.getMessage(2)
                    currentMessage1 = mySerialDevice.currentMessage1
                    currentMessage2 = mySerialDevice.currentMessage2
                    # if we get to this point, we successfuly read the data from the serial device
                    serialDeviceReadFails = 0
                    outputData.emit(["serialDeviceReadFails", 0])
                    outputData.emit(["currentMessage1", currentMessage1])
                    outputData.emit(["currentMessage2", currentMessage2])
                    outputData.emit(["connectedToSerialDevice", confirmation])

                except Exception as e:
                    serialDeviceReadFails += 1
                    #print("serialDevice printer failed to read current printer messages " + str(serialDeviceReadFails) + " times in a row, with the following error:" + str(e))
                    outputData.emit(["serialDeviceReadFails", serialDeviceReadFails])
                    if serialDeviceReadFails > 10:
                        outputData.emit(["currentMessage1", ""])
                        outputData.emit(["currentMessage2", ""])
                        outputData.emit(["connectedToSerialDevice", 0])
                        raise Exception(e)
            outputData.emit(["serialDeviceObject", mySerialDevice])





    def threadedFunctionC_Result(self, s):
        pass
        #print("Result:", s)

    def threadedFunctionC_Finished(self):
        #print("THREAD COMPLETE!")
        self.threadedFunctionC_Start()

    def threadedFunctionC_HandleOutputs(self, n):
        # this gets called (in the main GUI thread) at various points during the execution of the threaded
        # function. The threaded function emits a list, with item[0] being an identifier so we know WHAT
        # information is being relayed to us, followed by the data.
        #print(n)
        #print("serialDevice handleoutputs")
        if n[0] == "connectedToSerialDevice":
            self.connectedToSerialDevice = n[1]
            #print("serialDeviceFn is on its first run, time")
        elif n[0] == "serialDeviceObject":
            self.serialDeviceObject = n[1]
            #print("received serialDevice object")
        elif n[0] == "currentMessage1":
            self.currentMessage1 = n[1]
        elif n[0] == "currentMessage2":
            self.currentMessage2 = n[1]
        elif n[0] == "msgChangeSuccessful":
            self.permsissionToAlterStencil = False
        elif n[0] == "serialDeviceReadFails":
            self.serialDeviceReadFails = n[1]


    def threadedFunctionC_Error(self, error):
        # Reset everything on error
        #print(error)
        self.connectedToSerialDevice = False
        #self.serialDeviceFn_Start()
        print("Error in serialDeviceFn! :", error)




    def crashDummy(self):
        # intentionally crash python for testing
        import ctypes
        p = ctypes.pointer(ctypes.c_char.from_address(5))
        p[0] = b'x'


    def pullCord(self):
        print("pullcord()")


def main():
    app = QApplication([])
    window = importedGUI()
    # enable this to send QT GUI to second monitor
    # monitor = QDesktopWidget().screenGeometry(1)
    # window.move(monitor.left(), monitor.top())
    #window.show()
    #window.showFullScreen()
    window.showMaximized()
    app.aboutToQuit.connect(lambda: window.pullCord())
    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")


if __name__ == '__main__':
    main()

