# This module is a placeholder / redirector to allow old code and plugins
# to continue to function until such time that they are updated to use the
# newer modules and methods.

from Screens.Information import CommitLogInformation, MemoryInformation


class CommitInfo(CommitLogInformation):  # Entry point for legacy code that is yet to be updated.
	def __init__(self, session):
		CommitLogInformation.__init__(self, session)


class MemoryInfo(MemoryInformation):  # Entry point for legacy code that is yet to be updated.
	def __init__(self, session):
		CommitLogInformation.__init__(self, session)
