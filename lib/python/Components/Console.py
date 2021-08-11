from os import waitpid

from enigma import eConsoleAppContainer


class ConsoleItem:
	def __init__(self, containers, cmd, callback, extraArgs):
		self.containers = containers
		if isinstance(cmd, str):  # Until .execute supports a better API.
			cmd = [cmd]
		self.callback = callback
		self.extraArgs = extraArgs
		name = str(cmd)
		if name in self.containers:
			name = "%s@%s" % (name, hex(id(self)))  # Create a unique name.
		self.containers[name] = self
		self.name = name
		self.container = eConsoleAppContainer()
		if callback is not None:  # If the caller isn't interested in our results, we don't need to store the output either.
			self.appResults = []
			self.container.dataAvail.append(self.dataAvailCB)
		self.container.appClosed.append(self.appClosedCB)
		if len(cmd) > 1:
			print("[Console] Processing command '%s' with arguments '%s'." % (cmd[0], "', '".join(cmd[1:])))
		else:
			print("[Console] Processing command line '%s'." % cmd[0])
		retVal = self.container.execute(*cmd)
		if retVal:
			self.appClosedCB(retVal)
		if callback is None:
			try:
				pid = self.container.getPID()
				print("[Console] Waiting for command (PID %d) to finish." % pid)
				pid, exitVal = waitpid(pid, 0)
			except (IOError, OSError) as err:
				print("[Console] Error %s: Wait for command to terminate failed!  (%s)" % (err.errno, err.strerror))

	def dataAvailCB(self, data):
		self.appResults.append(data)

	def appClosedCB(self, retVal):
		print("[Console] Command '%s' finished with exit status of %d." % (self.name, retVal))
		del self.containers[self.name]
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		self.container = None
		if self.callback is not None:
			appResults = b"".join(self.appResults)
			self.callback(appResults, retVal, self.extraArgs)


class Console(object):
	def __init__(self):
		# Still called appContainers because Network.py, SoftwareTools.py
		# and WirelessLan/Wlan.py accesses it to know if there's still
		# stuff running.
		self.appContainers = {}

	def ePopen(self, cmd, callback=None, extra_args=None):
		return ConsoleItem(self.appContainers, cmd, callback, extra_args)

	def eBatch(self, cmds, callback, extra_args=None, debug=False):
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retVal, extraArg):
		(cmds, callback, extraArgs) = extraArg
		if self.debug:
			print("[Console] eBatch DEBUG: retVal=%s, cmds left=%d, data:\n%s" % (retVal, len(cmds), data))
		if cmds:
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extraArgs])
		else:
			callback(extraArgs)

	def kill(self, name):
		if name in self.appContainers:
			print("[Console] Killing command '%s'." % name)
			self.appContainers[name].container.kill()

	def killAll(self):
		for name, item in self.appContainers.items():
			print("[Console] Killing all commands '%s'." % name)
			item.container.kill()
