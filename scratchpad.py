def usbFn_Start(self):
    if self.usbExecute == "1":
        if self.usbReady == False:
            self.lbl_usbReady.setText("USB Thumb drive ready?: NO")
            self.lbl_usbReady.setStyleSheet('background-color : red')
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
    #watcher.start_listening()
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

