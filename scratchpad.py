def neoFn_Start(self):
    if self.neoExecute == "1":
        if self.neoReady == False:
            self.lbl_lineRunning.setText("Line Running?: NO")
            self.lbl_lineRunning.setStyleSheet('background-color : red')
        else:
            self.lbl_lineRunning.setText("Line Running?: YES")
            self.lbl_lineRunning.setStyleSheet('background-color : green')
        neoFnInputData = [self.neoReady,
                           self.neoObject,
                           self.neoHasRan]
        worker = Worker(self.neoFn, neoFnInputData)  # Any other args, kwargs are passed to the run function
        worker.signals.outputData.connect(self.neoFn_HandleOutputs)
        worker.signals.result.connect(self.neoFn_Result)
        worker.signals.finished.connect(self.neoFn_Finished)
        worker.signals.error.connect(self.neoFn_Error)
        self.threadpool.start(worker)

def neoFn(self, inputData, outputData):
    neoReady = inputData[0]
    neoObject = inputData[1]
    neoHasRan = inputData[2]

    if neoHasRan == False:
        print("Instantiating Neo")
        myNeo = neo.ioController()
        outputData.emit(["neoHasRan", True])
    else:
        myNeo = neoObject
    myNeo.check_existing_drives()
    outputData.emit(["neoObject", myNeo])

def neoFn_Result(self, s):
    pass

def neoFn_Finished(self):
    self.neoFn_Start()

def neoFn_HandleOutputs(self, n):
    if n[0] == "neoReady":
        self.neoReady = n[1]
    elif n[0] == "neoObject":
        self.neoObject = n[1]
    elif n[0] == "neoHasRan":
        self.neoHasRan = n[1]

def neoFn_Error(self, error):
    # Reset everything on error
    self.neoReady = False
    print("Error in neoFn!:", error)

