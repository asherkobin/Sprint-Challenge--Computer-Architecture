"""CPU functionality."""

import sys

""" Implments single-byte addressable guarded memory """
class Memory():
  def __init__(self, size):
    self.size = size
    self.clear()

  def clear(self):
    self.internal_memory = [0] * self.size

  def read_byte(self, address):
    if address < 0 or address > self.size - 1:
      raise ReferenceError("Out of bounds memory reference")
    return self.internal_memory[address]

  def write_byte(self, address, data):
    if address < 0 or address > self.size - 1:
      raise ReferenceError("Out of bounds memory reference")
    try:
      real_byte = int(data)
      if real_byte > 0xFF:
        raise TypeError("Integer overflow")
      if real_byte < 0:
        raise TypeError("Integer underflow")
      self.internal_memory[address] = real_byte
    except TypeError:
      raise TypeError("Data must be an 8-bit number")

""" Virtual CPU """
class CPU:
  def __init__(self):
    # spec limits memory to 256 bytes
    self.MAX_MEM = 256
    self.ram = Memory(self.MAX_MEM)

    # trace will print the history up to 5 lines
    self.trace_history = []
    
    # supported instructions
    HLT  = 0x01
    PUSH = 0x45
    POP  = 0x46
    PRN  = 0x47
    JMP  = 0x54
    JNE  = 0x55
    JEQ  = 0x56
    LDI  = 0x82
    MUL  = 0xA2
    CMP  = 0xA7
  
    # this table maps an instruction to its implementation
    self.dispatch_table = {
      HLT:  self.HLT,
      PRN:  self.PRN,
      LDI:  self.LDI,
      PUSH: self.PUSH,
      POP:  self.POP,
      MUL:  self.MUL,
      CMP:  self.CMP,
      JMP:  self.JMP,
      JEQ:  self.JEQ,
      JNE:  self.JNE
    }

    # general purpose registers
    self.gp_registers = Memory(8)
    self.gp_registers.write_byte(7, 0xF4) # R7 = SP

    # special purpose registers
    self.PC = 0 # program counter (aka instruction pointer)
    self.IR = 0 # instruction register (the currently executing instruction)

    # flags register (each bit is a flag, up to 8)
    self.FL = 0x00

    # list of flag masks indicating their position within the FLAGS register
    self.FLAG_RUNNING = 0b10000000
    self.FLAG_LESS    = 0b00000100
    self.FLAG_GREATER = 0b00000010
    self.FLAG_EQUAL   = 0b00000001

  def get_SP(self):
    return self.gp_registers.read_byte(7)

  def set_SP(self, value):
    self.gp_registers.write_byte(7, value)

  def load(self, ls8_file):
    self.ram.clear()
    address = 0

    with open(ls8_file) as f:
      for line in f:
        line = line.split("#")

        try:
          data = int(line[0], 2)
        except ValueError:
          continue

        self.ram_write(address, data)
        address += 1

  def ram_read(self, address):
    return self.ram.read_byte(address)

  def ram_write(self, address, value):
    self.ram.write_byte(address, value)

  def trace(self):
    # header
    print("PC | IN P1 P2 |", end='')

    for i in range(8):
      print(" R%X" % i, end='')

    print(" | FL", end='')
    print()

    # splitter
    print("--------------------------------------------")

    # cpu state
    trace_info = f"%02X | %02X %02X %02X |" % (
      self.PC,
      self.ram_read(self.PC),
      self.ram_read(self.PC + 1),
      self.ram_read(self.PC + 2))

    for i in range(8):
      trace_info += " %02X" % self.gp_registers.read_byte(i)

    trace_info += " | %02X" % self.FL

    self.trace_history.append(trace_info)

    last_5_traces = self.trace_history[-5:]

    for line in last_5_traces:
      print(line, end='')
      print()

    print()

  def run(self):
    self.FL |= self.FLAG_RUNNING # CPU ON
    
    while self.FL & self.FLAG_RUNNING == self.FLAG_RUNNING: # while CPU ON
      self.IR = self.ram_read(self.PC) # load instruction
      
      # self.trace()
      
      # decode the instruction

      num_ops = (self.IR & 0b11000000) >> 6
      use_alu = (self.IR & 0b00100000) >> 5
      sets_pc = (self.IR & 0b00010000) >> 4
      insr_id = (self.IR & 0b00001111) >> 0

      if use_alu:
        self.alu(self.IR, self.ram_read(self.PC + 1), self.ram_read(self.PC + 2))
      else:
        try:
          self.dispatch_table[self.IR]() # execute
        except KeyError:
          print(f"Unknown instruction 0x%02X at address 0x%02X" % (self.IR, self.PC))
          self.HLT()

      if not sets_pc:
        self.PC += (1 + num_ops)

  # Implementation of ALU
  
  def alu(self, op, reg_a, reg_b):
    try:
      self.dispatch_table[self.IR](reg_a, reg_b) # execute
    except KeyError:
      print(f"Unknown ALU instruction 0x%02X at address 0x%02X" % (self.IR, self.PC))
      self.HLT()

  # Implementation of CPU Instructions

  def HLT(self):
    self.FL &= ~self.FLAG_RUNNING

  def LDI(self):
    reg_num = self.ram_read(self.PC + 1)
    reg_val = self.ram_read(self.PC + 2)
    self.gp_registers.write_byte(reg_num, reg_val)

  def PRN(self):
    reg_num = self.ram_read(self.PC + 1)
    reg_val = self.gp_registers.read_byte(reg_num)
    print(reg_val)

  def PUSH(self):
    self.set_SP(self.get_SP() - 1)
    reg_num = self.ram_read(self.PC + 1)
    data = self.gp_registers.read_byte(reg_num)
    self.ram_write(self.get_SP(), data)

  def POP(self):
    reg_num = self.ram_read(self.PC + 1)
    data = self.ram_read(self.get_SP())
    self.gp_registers.write_byte(reg_num, data)
    self.set_SP(self.get_SP() + 1)

  def JMP(self):
    reg_num = self.ram_read(self.PC + 1)
    self.PC = self.gp_registers.read_byte(reg_num)

  def JEQ(self):
    if self.FL & self.FLAG_EQUAL == self.FLAG_EQUAL:
      self.JMP()
    else:
      self.PC += 2

  def JNE(self):
    if self.FL & self.FLAG_EQUAL == 0:
      self.JMP()
    else:
      self.PC += 2

# ALU instructions take up to two operands stored in registers
  
  def MUL(self, reg_a, reg_b):
    reg_a_val = self.gp_registers.read_byte(reg_a)
    reg_b_val = self.gp_registers.read_byte(reg_b)
    result = reg_a_val * reg_b_val
    self.gp_registers.write_byte(reg_a, result)
  
  def CMP(self, reg_a, reg_b):
    reg_a_val = self.gp_registers.read_byte(reg_a)
    reg_b_val = self.gp_registers.read_byte(reg_b)

    if reg_a_val == reg_b_val:
      self.FL |= self.FLAG_EQUAL   # set FLAG_EQUAL ON
    else:
      self.FL &= ~self.FLAG_EQUAL  # set FLAG_EQUAL OFF
    
    if reg_a_val < reg_b_val:
      self.FL |= self.FLAG_LESS
    else:
      self.FL &= ~self.FLAG_LESS
    
    if reg_a_val > reg_b_val:
      self.FL |= self.FLAG_GREATER
    else:
      self.FL &= ~self.FLAG_GREATER

# DEBUG

import sys
from cpu import CPU

cpu = CPU()

ls8filename = "sctest.ls8"

cpu.load(ls8filename)
cpu.run()