#!/usr/bin/env python3

"""Main."""

import sys
from cpu import CPU

cpu = CPU()

ls8filename = sys.argv[1]

cpu.load(ls8filename)
cpu.run()