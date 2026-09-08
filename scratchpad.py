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

        fWebFnInputData = [self.connectedToDgk,
                           self.dgkObject,
                           self.lastDgkCall,
                           self.dgkIP,
                           self.csvLogInterval]
        worker = Worker(self.dgkFn, fWebFnInputData)  # Any other args, kwargs are passed to the run function
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
            lastDgkCall = time.time() + csvLogInterval
            outputData.emit(["lastDgkCall", lastDgkCall])
            # print("success1")
        else:
            # print("run2")
            myDgk = dgkObject
            myDgk.parseDgkOutput()
            outputData.emit(["result", myDgk.logDict])
            outputData.emit(["wholeDict", [myDgk.dgkDict, myDgk.dgkLogOptions]])
            outputData.emit(["dgkObject", myDgk])
            lastDgkCall = time.time() + csvLogInterval
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

