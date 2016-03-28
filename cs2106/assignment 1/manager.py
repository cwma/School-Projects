#!/usr/bin/env python
# for python 2.7.x   
# A011937E Chia Wei Meng Alexander

from sys import argv
from os import path

class ReadyList(object):
    """
    Data structure used to hold the contents of the ReadyList.
    implemented using an array of 3 arrays to represent a priorityqueue like structure.
    """
    def __init__(self):
        "initialize a new readylist"
        self.queue = [[],[],[]]

    def put(self, pcb):
        "insers item to end of the appropriate sub-queue based on object's priority"
        self.queue[pcb.priority].insert(0, pcb)

    def get(self):
        "gets the highest priority item, removes it from the queue and returns it"
        pcb = self.peek()
        self.remove(pcb)
        return pcb

    def peek(self):
        "returns highest priority item by checking the queue in descending order and returns the last item of the first non-empty sub-queue"
        for q in self.queue[::-1]:
            if q: return q[-1]

    def remove(self, pcb):
        "removes the item from its sub-queue"
        self.queue[pcb.priority].remove(pcb)

    def info(self):
        "returns a string description of the current instance of readylist"
        return "Readylist contains the following processes:\n" + "".join(
            ["".join(["PID: %s, Priority: %s\n" % (pcb.pid, pcb.priority) for pcb in q]) for q in self.queue])

    def __repr__(self):
        return "readylist"

class PCB(object): 
    """
    data structure used to represent the state of a process control block.
    """
    def __init__(self, pid, _list, priority, parent=None):
        """
        initializes a process control block.
        if the parent variable is provided it adds its own instance to the parents list of children in its creation tree.
        """
        self.pid = pid
        self.status = {"type": "ready", "list": _list} # _list can be an instance of ReadyList or RCB
        self.creation_tree = {"parent": parent, "children": []}
        self.other_resources = {} # a dictionary representing resources allocated to this instance of pcb, eg. {"R1": {rid: rcb, "size": size}}
        self.priority = priority
        if parent: parent.creation_tree["children"].append(self) # append self to parent creation tree children list

    def info(self):
        "returns a string description of the current instance of the process control block"
        return "\n\tProcess: %s\n\tStatus type: %s\n\tStatus list: %s\n\tPriority: %s\n\tParent: %s\n\tChildren:%s\n\tResources:%s\n" % (self.pid,
            self.status["type"], self.status["list"], self.priority, self.creation_tree["parent"], "".join([" %s" % c for c in self.creation_tree["children"]]),
            ''.join([" %s(%s)" % (rid, self.other_resources[rid]["size"]) for rid in self.other_resources.keys()]))

    def __repr__(self):
        return self.pid

class RCB(object):
    """
    data structure used to represent the state of a resource control block.
    methods incorporated are used to facilitate the manipulation of its waitinglist and inventory.
    error checking for illegal operations is handled by the Manager not the RCB.
    """
    def __init__(self, rid, size):
        "initializes a resource control block"
        self.rid = rid
        self.inventory = {"current": size, "max": size}
        self.waitinglist = [] # a list of dictionary containing 2 fields {pid: pcb, "size": size}

    def wait(self, req):
        "adds a request of dict type containing 2 fields, {pid: pcb, 'size': size} to the waitinglist"
        self.waitinglist.insert(0, req)

    def remove(self, pcb):
        "removes all entries in the waitinglist that matches the provided pcb object regardless of the size field"
        r = [req for req in self.waitinglist if req["pcb"] is pcb]
        [self.waitinglist.remove(req) for req in r]

    def allocate(self, size, process):
        "allocates resource inventory based on provided size to the provided pcb object"
        self.inventory["current"] -= size # decrement inventory
        if self.rid in process.other_resources: # if the process has been allocated units from this resource
            process.other_resources[self.rid]["size"] += size # increase the allocation
        else:
            process.other_resources[self.rid] = {"size": size, "rcb": self} # create new allocation for the process

    def unallocate(self, size, process):
        "unallocates resource inventory based on provided size to the provided pcb object"
        process.other_resources[self.rid]["size"] -= size # removes allocation from process
        self.inventory["current"] += size # increments inventory
        if process.other_resources[self.rid]["size"] == 0 : # if all units of inventory are removed from the process
            process.other_resources.pop(self.rid) # remove the reference to the resource completely

    def allocatewaitingprocess(self):
        "checks the waitinglist and allocates resource to the pcb next in line if there is sufficient inventory to do so"
        if self.waitinglist and self.waitinglist[-1]["size"] <= self.inventory["current"]:
            req = self.waitinglist.pop()
            self.allocate(req["size"], req["pcb"])
            return req["pcb"] # returns the process that was allocated a resource so the Manager can perform housekeeping
        return None

    def info(self):
        "returns a string description of the current instance of the resource control block"
        return "\n\tResource: %s\n\tInventory: %s/%s\n\tWaiting List:%s\n" % (self.rid, self.inventory["current"], self.inventory["max"], 
            "".join([" %s(%s)" % (req["pcb"].pid, req["size"]) for req in self.waitinglist[::-1]]))

    def __repr__(self):
        return self.rid

class Manager(object):
    """
    Manager class that acts as an instance of a process and resource management with methods that emulate process calls.
    """
    def __init__(self):
        "initializes the Manager"
        self.readylist = ReadyList() # intialize new ReadyList data structure
        self.process = PCB("init", self.readylist, 0) # this variable holds the current running process, at this point being init
        self.processes = {"init": self.process} # creates a dictionary of all process instances
        self.resources = {"R1": RCB("R1", 1), "R2": RCB("R2", 2), "R3": RCB("R3", 3), "R4": RCB("R4", 4)} # creates a dictionary of predetermined resources 
        self.readylist.put(self.process) # adds init to readylist
        self._scheduler() 

    def create(self, pid, priority):
        "creates a new process based on provided pid and priority"
        if pid in self.processes: # if pid is in use raise error
            raise ValueError("Error: process with pid: %s already exists." % pid)
        if priority < 1 or priority > 2: # if invalid priority is provided raise error
            raise ValueError("Error: invalid priority for a process.")
        pcb = PCB(pid, self.readylist, priority, self.process) # create new pcb
        self.readylist.put(pcb) 
        self.processes[pid] = pcb 
        return self._scheduler() 

    def request(self, rid, size):
        "request resources for current running process"
        if self.process.pid == "init": # if init tries to request resource raise error
            raise ValueError("Error: init cannot request resources.")
        if rid not in self.resources: # if an invalid resource is requested raise error
            raise ValueError("Error: specified resource does not exist.")
        rcb = self.resources[rid] # retrieve rcb object 
        # check if requesting process already owns units of requested resource and ensure sum of request and already owned units does not exceed what the resource has
        if rcb.rid in self.process.other_resources and self.process.other_resources[rcb.rid]["size"] + size > rcb.inventory["max"]:
            raise ValueError("Error: sum of requested resource units and already allocated units exceeds resource maximum inventory.")
        if size > rcb.inventory["max"]: # if requested resource exceeds resource inventory raise error
            raise ValueError("Error: requested resource units exceeds resource maximum inventory.")
        if rcb.inventory["current"] >= size: # if resource has the requested amount available 
            rcb.allocate(size, self.process) # allocate it
        else: # if not, process is blocked and added to waitinglist
            self.process.status["type"] = "blocked"
            self.process.status["list"] = rcb
            self.readylist.remove(self.process)
            rcb.wait({"size": size, "pcb": self.process})
        return self._scheduler()

    def release(self, rid, size, destroyed=False):
        "release resources for current running process"
        callingprocess = self.process
        if destroyed: callingprocess = destroyed # if destroyed argument is provided, use that as the calling process
        if rid not in self.resources: # check if resource exists if not raise error
            raise ValueError("Error: specified resource does not exist.")
        rcb = self.resources[rid]
        if rcb.rid not in callingprocess.other_resources: # if calling process does not own the resource raise error
            raise ValueError("Error: cannot release resources current process does not own.")
        elif size > callingprocess.other_resources[rcb.rid]["size"]: # if process owns less units than requested to be released raise error
            raise ValueError("Error: cannot release more resource units than current units you own.") 
        rcb.unallocate(size, callingprocess)
        while True:  # if the unallocation of resources allowed a waiting process to be allocated resources, handle appropriate request housekeeping, else proceed
            pcb = rcb.allocatewaitingprocess()
            if not pcb: break
            self.readylist.put(pcb)
            pcb.status["type"] = "ready"
            pcb.status["list"] = self.readylist
        return self._scheduler()

    def _isparentorself(self, pcb):
        "private method used by Manager.destroy to check if requesting process is a parent or self of target process to be destroyed"
        if self.process is pcb: return True # if self
        elif pcb.creation_tree["parent"]: return self._isparentorself(pcb.creation_tree["parent"]) # recursively move up the creation tree 
        return False # return False if self not found in process ancestors

    def destroy(self, pid):
        "method used to destroy a process"
        if pid == "init": # if process is init raise error
            raise ValueError("Error: init cannot destroy itself.")
        if pid not in self.processes: # if process does not exist raise error
            raise ValueError("Error: no such process exists.")
        pcb = self.processes[pid]
        if(self._isparentorself(pcb)): # check if current process is parent or self
            self._destroy(pcb) # call recursive _destroy method to destroy target process and all its children
            if pcb.creation_tree["parent"]: # removes the destroyed process child entry in its parents creation tree
                pcb.creation_tree["parent"].creation_tree["children"].remove(pcb)
            return self._scheduler()
        else:
            raise ValueError("Error: current process is not a parent or ancestor.")

    def _destroy(self, pcb):
        "private method used Manager.destroy to recursively destroy a process and all its children"
        if(pcb):
            if pcb.other_resources: [self.release(rid, pcb.other_resources[rid]["size"], pcb) for rid in pcb.other_resources.keys()] # release all resources 
            if self.process is pcb: self.process = None # if the process is running remove its reference
            pcb.status["list"].remove(pcb) # remove process reference from status list (readylist or rcb)
            self.processes.pop(pcb.pid) # remove process reference from process dictionary
            [self._destroy(child) for child in pcb.creation_tree["children"]] # recursively call this method on all child processes

    def timeout(self):
        "method used to simulate timeout"
        pcb = self.readylist.get()
        pcb.status["type"] = "ready"
        self.readylist.put(pcb)
        return self._scheduler()

    def _scheduler(self):
        """
        private method called after every Manager call used to perform scheduling.
        returns the pid of the running process.
        """
        priorityprocess = self.readylist.peek()
        if self.process is not priorityprocess: # if running process no longer has priority or has been destroyed
            if self.process is not None and self.process.status["type"] != "blocked": # set to ready if not blocked
                self.process.status["type"] = "ready"
            self.process = priorityprocess
        self.process.status["type"] = "running"
        return self.process.pid

    def _enumeratedict(self, items):
        "private method for listing of process or resources"
        _str = "-"*35
        for pid in items.keys():
            _str += items[pid].info()
        return _str + "-"*35

    def listprocesses(self):
        "list all processes"
        return self._enumeratedict(self.processes)

    def listresources(self):
        "list all resources"
        return self._enumeratedict(self.resources)

def processfile(filename):
    "function used to process commands from a text file and write an output file into the same directory, filename hardcoded to authors matric id."
    if path.exists(filename):
        filepath = path.abspath(filename)
        filedir = path.dirname(filepath)
        outputfilename = path.join(filedir, "A0112937E.txt")
        with open(filename, "r") as readfile:
            with open(outputfilename, "w") as writefile:
                def _callback(_str, format=True):
                    if format: writefile.write(" "+_str)
                    else: writefile.write(" error") # extra commands for shell interpretor returns an error instead here
                manager = Manager()
                writefile.write("init")
                for line in readfile:
                    if line.rstrip("\n").rstrip("\r").rstrip("\r\n") == "init":
                        manager = Manager()
                        _callback("\n\ninit")
                    elif line.rstrip("\n").rstrip("\r").rstrip("\r\n") == "...":
                        _callback("...")
                    else:
                        try:
                            _options(line, manager, _callback)
                        except Exception, e:
                            writefile.write(" error") # writes error instead of full error message
            writefile.close()
        readfile.close()
    else:
        raise ValueError("Error: file does not exist.")

def shell():
    "function used to start an interpretive shell session with descriptive output."
    def _callback(_str, format=True):
        if format: print "Process %s is currently running" % _str
        else: print _str 
    manager = Manager()
    _callback("init")
    while True: # main loop
        cmd = raw_input("Shell> ")
        if cmd == "quit": 
            break
        elif cmd == "init":
            manager = Manager()
            _callback("init")
        else:
            try:
                _options(cmd, manager, _callback)
            except Exception, e:
                print e.args[0]

def _options(cmd, manager, callback):
    """
    helper function used by either the shell function or for processing of commands from a text file.
    output is returned through a provided callback function from the calling function.
    extra functions are available for the shell function only, and would otherwise return errors when processing from a file.
    rl : enumerate ready list
    lp : enumerate all processes
    p [pid] : show process info
    lr : enumerate all resources
    r [rid] : show resource info
    """
    cmd = cmd.split()
    if len(cmd) == 0:
        pass
    elif cmd[0] == "cr" and len(cmd) == 3 and cmd[2].isdigit():
        callback(manager.create(cmd[1], int(cmd[2])))
    elif cmd[0] == "de" and len(cmd[0]) == 2:
        callback(manager.destroy(cmd[1]))
    elif cmd[0] == "req" and len(cmd) == 3 and cmd[2].isdigit():
        callback(manager.request(cmd[1], int(cmd[2])))
    elif cmd[0] == "rel" and len(cmd) == 3 and cmd[2].isdigit():
        callback(manager.release(cmd[1], int(cmd[2])))
    elif cmd[0] == "to":
        callback(manager.timeout())
    elif cmd[0] == "rl":
        callback(manager.readylist.info(), False)
    elif cmd[0] == "lp":
        callback(manager.listprocesses(), False)
    elif cmd[0] == "p" and cmd[1] in manager.processes:
        callback(manager.processes[cmd[1]].info(), False)
    elif cmd[0] == "lr":
        callback(manager.listresources(), False)
    elif cmd[0] == "r" and cmd[1] in manager.resources:
        callback(manager.resources[cmd[1]].info(), False)
    else:
        raise ValueError("Error: invalid command.")

if __name__ == "__main__":
    if len(argv) > 1:
        processfile(argv[1]) # handle text input file
    else:
        shell() # start shell interpretor