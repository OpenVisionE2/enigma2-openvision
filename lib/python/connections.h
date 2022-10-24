#ifndef __lib_python_connections_h
#define __lib_python_connections_h

#include <libsig_comp.h>

#include <lib/python/python.h>
#include <utility>

#include <Python.h>

class PSignal
{
protected:
	ePyObject m_list;
public:
	PSignal();
	~PSignal();
	void callPython(SWIG_PYOBJECT(ePyObject) tuple);
#ifndef SWIG
	PyObject *getSteal(bool clear=false);
#endif
	PyObject *get();
};

inline PyObject *PyFrom(int v)
{
	return PyInt_FromLong(v);
}

inline PyObject *PyFrom(const char *c)
{
	return PyString_FromString(c);
}
// Only used by console which might transfer binary data(screenshots). So use Bytes instead of Unicode
inline PyObject *PyFrom(std::pair<const char*, int>& p)
{
#if PY_MAJOR_VERSION < 3
	return PyString_FromStringAndSize(p.first, p.second);
#else
	return PyBytes_FromStringAndSize(p.first, p.second);
#endif
}

template <class R>
#if SIGCXX_MAJOR_VERSION == 3
class PSignal0: public PSignal, public sigc::signal<R()>
#else
class PSignal0: public PSignal, public sigc::signal0<R>
#endif
{
public:
	R operator()()
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(0);
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
#if SIGCXX_MAJOR_VERSION == 3
		return sigc::signal<R()>::operator()();
#else
		return sigc::signal0<R>::operator()();
#endif
	}
};

template <class R, class V0>
#if SIGCXX_MAJOR_VERSION == 3
class PSignal1: public PSignal, public sigc::signal<R(V0)>
#else
class PSignal1: public PSignal, public sigc::signal1<R,V0>
#endif
{
public:
	R operator()(V0 a0)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(1);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
#if SIGCXX_MAJOR_VERSION == 3
		return sigc::signal<R(V0)>::operator()(a0);
#else
		return sigc::signal1<R,V0>::operator()(a0);
#endif
	}
};

template <class R, class V0, class V1>
#if SIGCXX_MAJOR_VERSION == 3
class PSignal2: public PSignal, public sigc::signal<R(V0, V1)>
#else
class PSignal2: public PSignal, public sigc::signal2<R,V0,V1>
#endif
{
public:
	R operator()(V0 a0, V1 a1)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(2);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			PyTuple_SET_ITEM(pArgs, 1, PyFrom(a1));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
#if SIGCXX_MAJOR_VERSION == 3
		return sigc::signal<R(V0,V1)>::operator()(a0, a1);
#else
		return sigc::signal2<R,V0,V1>::operator()(a0, a1);
#endif
	}
};

template <class R, class V0, class V1, class V2>
#if SIGCXX_MAJOR_VERSION == 3
class PSignal3: public PSignal, public sigc::signal<R(V0, V1, V2)>
#else
class PSignal3: public PSignal, public sigc::signal3<R,V0,V1,V2>
#endif
{
public:
	R operator()(V0 a0, V1 a1, V2 a2)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(3);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			PyTuple_SET_ITEM(pArgs, 1, PyFrom(a1));
			PyTuple_SET_ITEM(pArgs, 2, PyFrom(a2));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
#if SIGCXX_MAJOR_VERSION == 3
		return sigc::signal<R(V0,V1,V2)>::operator()(a0, a1, a2);
#else
		return sigc::signal3<R,V0,V1,V2>::operator()(a0, a1, a2);
#endif
	}
};

#endif
