# -*- coding: utf-8 -*-
from os import remove
from os.path import isfile
from threading import Thread, current_thread
from sys import _current_frames
from traceback import extract_stack
from time import sleep
from Components.config import config


class StackTracePrinter(Thread):
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		print("[StackTrace] initializing StackTracePrinter")
		StackTracePrinter.instance = self
		Thread.__init__(self)
		self.__running = False

	def activate(self, MainThread_ident):
		print("[StackTrace] activating StackTracePrinter")
		self.MainThread_ident = MainThread_ident
		if not self.__running:
			self.__running = True
			self.start()

	def run(self):
		while (self.__running == True):
			if (isfile("/tmp/doPythonStackTrace")):
				remove("/tmp/doPythonStackTrace")
				if config.crash.pythonStackOnSpinner.value:
					print("[StackTrace] StackTrace")
					code = []
					code.append("========== Stacktrace of active Python threads ===========")
					for threadId, stack in _current_frames().items():
						if (threadId != current_thread().ident):
							if (threadId == self.MainThread_ident):
								code.append("========== MainThread 0x%08x =========================" % threadId)
							else:
								code.append("========== Thread ID  0x%08x =========================" % threadId)
							for filename, lineno, name, line in extract_stack(stack):
								code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
								if line:
									code.append("  %s" % (line.strip()))
					del stack
					code.append("========== Stacktrace end ================================")
					for line in code:
						print(line)
			sleep(1)
		Thread.__init__(self)

	def deactivate(self):
		print("[StackTrace] deactivating StackTracePrinter")
		self.__running = False
