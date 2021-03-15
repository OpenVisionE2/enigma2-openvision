from Screens.Information import CommitLogInformation, MemoryInformation


class CommitInfo(CommitLogInformation):  # Entry point for legacy code that is yet to be updated.
	def __init__(self, session):
		CommitLogInformation.__init__(self, session)



class MemoryInfo(MemoryInformation):  # Entry point for legacy code that is yet to be updated.
	def __init__(self, session):
		CommitLogInformation.__init__(self, session)
