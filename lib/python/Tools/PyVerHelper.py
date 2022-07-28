from sys import version_info


def getPyVS():
	PyVS = "%s" % (version_info.major) #Example: 2
	return int(PyVS)


def getPyVerSt():
	PyVerSt = "%s.%s" % (getPyVS(), version_info.minor) #Example: 2.7
	return PyVerSt


def getPythonVersionString():
	PythonVersionString = "%s.%s" % (getPyVerSt(), version_info.micro) #Example: 2.7.18
	return PythonVersionString


def getPyExt():
	if getPyVS() == "2":
		PyExt = "pyo"
	else:
		PyExt = "pyc"
	return PyExt


def getPyPath():
	PyPath = "python%s" % (getPyVerSt()) #Example: python2.7
	return PyPath
