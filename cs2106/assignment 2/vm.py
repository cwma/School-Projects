#!/usr/bin/env python
# for python 2.7.x   
# A011937E Chia Wei Meng Alexander

from sys import argv
from os import path

class Vm:

	def __init__(self, _use_tlb=False):
		"initialize arrays representing physical memory, bitmap and tlb"
		self.pm = [0 for x in range(524288)]
		self.bitmap = [0 for x in range(1024)]
		self.bitmap[0] = 1
		self.tlb = [[x, 0, -1, -1] for x in range(4)]
		self.use_tlb = _use_tlb

	def _read_va(self, va):
		"parses integer into respective s, p, w and sp values"
		va = bin(va)[2::]
		(s, p, w, sp) = (va[0:-19], va[-19:-9], va[-9:], va[0:-9])
		return (s != '' and int(s,2) or 0, p != '' and int(p,2) or 0, w != '' and int(w,2) or 0, sp != '' and int(sp,2) or 0)

	def _update_bm(self, addr, is_pt=False):
		"fills in slots in bitmap given an address and if its a pt or not"
		self.bitmap[addr/512] = 1
		if is_pt: self.bitmap[addr/512 + 1] = 1

	def init_st(self, s, f):
		"initialize st values"
		self.pm[s] = f
		self._update_bm(f, True)
	
	def init_pt(self, p, s, f):
		"initialize pt values"
		self.pm[self.pm[s] + p] = f
		self._update_bm(f)


	def _allocate(self, is_pt=False):
		"locates free frames in bitmap to allocate"
		for x in range(len(self.bitmap)):
			if is_pt:
				if self.bitmap[x] == 0 and self.bitmap[x + 1] == 0:
					self.bitmap[x] = 1
					self.bitmap[x + 1] = 1
					return x * 512
			else:
				if self.bitmap[x] == 0:
					self.bitmap[x] = 1
					return x * 512

	def _check_tlb(self, _sp):
		"checks tlb for sp value"
		for n, lru, sp, f in self.tlb:
			if sp == _sp:
				return n
		return -1

	def _update_tlb(self, _n):
		"decrements all lru by 1 except given index"
		for n, lru, sp, f in self.tlb:
			if n != _n and lru != 0:
				self.tlb[n][1] -= 1

	def _update_tlb_match(self, _n):
		"increments the hit tlb's lru to 3"
		self.tlb[_n][1] = 3
		self._update_tlb(_n)

	def _update_tlb_miss(self, _sp, _f):
		"update tlb when a miss occured but a pa is determined"
		for n, lru, sp, f in self.tlb:
			if lru == 0:
				_n = 0
				break
		self.tlb[_n] = [_n, 3, _sp, _f]
		self._update_tlb(_n)

	def translate_va(self, va, write):
		"translates the va"
		(s, p, w, sp) = self._read_va(va) # gets the seperate va components
		if self.use_tlb: # checks tlb if enabled
			n = self._check_tlb(sp)
			if n != -1: # if match is found, update tlb and return pa
				self._update_tlb_match(n)
				return (self.tlb[n][3] + w, "h")
		st_entry = self.pm[s] # get st entry
		if st_entry == -1: return ("pf", "x") # page fault
		if st_entry == 0: 
			if(write): # make new pt
				st_entry = self._allocate(True)
				self.pm[s] = st_entry
			else: # if not write throw error
				return ("err", "x")
		pt_entry = self.pm[st_entry + p] # get pt entry
		if pt_entry == -1: return ("pf", "x") # page fault
		if pt_entry == 0:
			if(write): # make new page
				pt_entry = self._allocate()
				self.pm[st_entry + p] = pt_entry
			else: # if not write throw error
				return ("err", "x")
		if self.use_tlb: # if tlb is enabled update it
			self._update_tlb_miss(sp, pt_entry)
		return (pt_entry + w, "m")

def process_files(setupfile, translatefile):
	# driver method for handling 2 text file input and output
    if path.exists(setupfile) and path.exists(translatefile):
		# setup file inputs and output directories
        filepath = path.abspath(setupfile)
        filedir = path.dirname(filepath)
        output1 = path.join(filedir, "A0112937E1.txt")
        output2 = path.join(filedir, "A0112937E2.txt")
        # setup virtual memory, one with tlb one without
    	vm = Vm()
    	vmtlb = Vm(True)
    	# read setup file
        with open(setupfile, "r") as rsetupfile:
        	init_data = rsetupfile.readlines()
       	rsetupfile.close()
       	# formating input 
       	init_data = [x.rstrip("\n").rstrip("\r").rstrip("\r\n") for x in init_data]
       	init_st = [int(x) for x in init_data[0].split(" ")]
       	init_st = zip(init_st[0::2], init_st[1::2])
       	# putting st values into vm
       	for s, f in init_st:
       		vm.init_st(s, f)
       		vmtlb.init_st(s, f)
       	# formatting input
       	init_pt = [int(x) for x in init_data[1].split(" ")]
       	init_pt = zip(init_pt[0::3], init_pt[1::3], init_pt[2::3])
       	# putting pt values into vm
       	for p, s, f in init_pt:
       		vm.init_pt(p, s, f)
       		vmtlb.init_pt(p, s, f)
       	# open va file
        with open(translatefile, "r") as rtranslatefile:
        	trans_data = rtranslatefile.readlines()
       	rtranslatefile.close()
       	# formatting input
       	trans_data = [x.rstrip("\n").rstrip("\r").rstrip("\r\n") for x in trans_data]
       	trans_data = trans_data[0].split(" ")
       	trans_data = zip(trans_data[0::2], trans_data[1::2])
       	# write results to files
        with open(output1, "w") as writefile1:
        	with open(output2, "w") as writefile2:
       			for rw, va in trans_data:
       				rs1 = vm.translate_va(int(va), int(rw))
       				rs2 = vmtlb.translate_va(int(va), int(rw))
       				writefile1.write(str(rs1[0])+" ")
       				rs2 = (rs2[1] != "x" and str(rs2[1]) + " " or "") + str(rs2[0]) + " "
       				writefile2.write(rs2)
       		writefile2.close()  
       	writefile1.close()       	
    else:
        raise ValueError("Error: files do not exist.")

if __name__ == "__main__":
	process_files(argv[1], argv[2]) # handle text input files
