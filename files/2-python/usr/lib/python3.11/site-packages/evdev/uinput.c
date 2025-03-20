#include <Python.h>

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#ifdef __FreeBSD__
#include <dev/evdev/input.h>
#include <dev/evdev/uinput.h>
#else
#include <linux/input.h>
#include <linux/uinput.h>
#endif

#ifndef input_event_sec
#define input_event_sec time.tv_sec
#define input_event_usec time.tv_usec
#endif

// Workaround for installing on kernels newer than 4.4.
#ifndef FF_MAX_EFFECTS
#define FF_MAX_EFFECTS FF_GAIN;
#endif

int _uinput_close(int fd)
{
    if (ioctl(fd, UI_DEV_DESTROY) < 0) {
        int oerrno = errno;
        close(fd);
        errno = oerrno;
        return -1;
    }

    return close(fd);
}


static PyObject *
uinput_open(PyObject *self, PyObject *args)
{
    const char* devnode;

    int ret = PyArg_ParseTuple(args, "s", &devnode);
    if (!ret) return NULL;

    int fd = open(devnode, O_RDWR | O_NONBLOCK);
    if (fd < 0) {
        PyErr_SetString(PyExc_OSError, "could not open uinput device in write mode");
        return NULL;
    }

    return Py_BuildValue("i", fd);
}


static PyObject *
uinput_set_phys(PyObject *self, PyObject *args)
{
    int fd;
    const char* phys;

    int ret = PyArg_ParseTuple(args, "is", &fd, &phys);
    if (!ret) return NULL;

    if (ioctl(fd, UI_SET_PHYS, phys) < 0)
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}

static PyObject *
uinput_set_prop(PyObject *self, PyObject *args)
{
    int fd;
    uint16_t prop;

    int ret = PyArg_ParseTuple(args, "ih", &fd, &prop);
    if (!ret) return NULL;

    if (ioctl(fd, UI_SET_PROPBIT, prop) < 0)
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}

static PyObject *
uinput_get_sysname(PyObject *self, PyObject *args)
{
    int fd;
    char sysname[64];

    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    #ifdef UI_GET_SYSNAME
    if (ioctl(fd, UI_GET_SYSNAME(sizeof(sysname)), &sysname) < 0)
        goto on_err;

    return Py_BuildValue("s", &sysname);
    #endif

    on_err:
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}

// Different kernel versions have different device setup methods. You can read
// more about it here:
// https://github.com/torvalds/linux/commit/052876f8e5aec887d22c4d06e54aa5531ffcec75

// Setup function for kernel >= v4.5
#if defined(UI_DEV_SETUP) && defined(UI_ABS_SETUP)
static PyObject *
uinput_setup(PyObject *self, PyObject *args) {
    int fd, len, i;
    uint16_t vendor, product, version, bustype;
    uint32_t max_effects;

    PyObject *absinfo = NULL, *item = NULL;

    struct uinput_abs_setup abs_setup;

    const char* name;
    int ret = PyArg_ParseTuple(args, "isHHHHOI", &fd, &name, &vendor,
                               &product, &version, &bustype, &absinfo, &max_effects);
    if (!ret) return NULL;

    // Setup absinfo:
    len = PyList_Size(absinfo);
    for (i=0; i<len; i++) {

        // item -> (ABS_X, 0, 255, 0, 0, 0, 0)
        item = PyList_GetItem(absinfo, i);

        memset(&abs_setup, 0, sizeof(abs_setup)); // Clear struct
        abs_setup.code = PyLong_AsLong(PyList_GetItem(item, 0));
        abs_setup.absinfo.value = PyLong_AsLong(PyList_GetItem(item, 1));
        abs_setup.absinfo.minimum = PyLong_AsLong(PyList_GetItem(item, 2));
        abs_setup.absinfo.maximum = PyLong_AsLong(PyList_GetItem(item, 3));
        abs_setup.absinfo.fuzz = PyLong_AsLong(PyList_GetItem(item, 4));
        abs_setup.absinfo.flat = PyLong_AsLong(PyList_GetItem(item, 5));
        abs_setup.absinfo.resolution = PyLong_AsLong(PyList_GetItem(item, 6));

        if(ioctl(fd, UI_ABS_SETUP, &abs_setup) < 0)
            goto on_err;
    }

    // Setup evdev:
    struct uinput_setup usetup;

    memset(&usetup, 0, sizeof(usetup));
    strncpy(usetup.name, name, sizeof(usetup.name) - 1);
    usetup.id.vendor  = vendor;
    usetup.id.product = product;
    usetup.id.version = version;
    usetup.id.bustype = bustype;
    usetup.ff_effects_max = max_effects;

    if(ioctl(fd, UI_DEV_SETUP, &usetup) < 0)
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}

// Fallback setup function (Linux <= 4.5 and FreeBSD).
#else
static PyObject *
uinput_setup(PyObject *self, PyObject *args) {
    int fd, len, i, abscode;
    uint16_t vendor, product, version, bustype;
    uint32_t max_effects;

    PyObject *absinfo = NULL, *item = NULL;

    struct uinput_user_dev uidev;
    const char* name;

    int ret = PyArg_ParseTuple(args, "isHHHHOI", &fd, &name, &vendor,
                               &product, &version, &bustype, &absinfo, &max_effects);
    if (!ret) return NULL;

    memset(&uidev, 0, sizeof(uidev));
    strncpy(uidev.name, name, sizeof(uidev.name) - 1);
    uidev.id.vendor  = vendor;
    uidev.id.product = product;
    uidev.id.version = version;
    uidev.id.bustype = bustype;
    uidev.ff_effects_max = max_effects;

    len = PyList_Size(absinfo);
    for (i=0; i<len; i++) {
        // item -> (ABS_X, 0, 255, 0, 0, 0, 0)
        item = PyList_GetItem(absinfo, i);
        abscode = (int)PyLong_AsLong(PyList_GetItem(item, 0));

        /* min/max/fuzz/flat start from index 2 because index 1 is value */
        uidev.absmin[abscode]  = PyLong_AsLong(PyList_GetItem(item, 2));
        uidev.absmax[abscode]  = PyLong_AsLong(PyList_GetItem(item, 3));
        uidev.absfuzz[abscode] = PyLong_AsLong(PyList_GetItem(item, 4));
        uidev.absflat[abscode] = PyLong_AsLong(PyList_GetItem(item, 5));
    }

    if (write(fd, &uidev, sizeof(uidev)) != sizeof(uidev))
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}
#endif


static PyObject *
uinput_create(PyObject *self, PyObject *args)
{
    int fd;

    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    if (ioctl(fd, UI_DEV_CREATE) < 0)
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}


static PyObject *
uinput_close(PyObject *self, PyObject *args)
{
    int fd;

    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    if (_uinput_close(fd) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    Py_RETURN_NONE;
}


static PyObject *
uinput_write(PyObject *self, PyObject *args)
{
    int fd, type, code, value;

    int ret = PyArg_ParseTuple(args, "iiii", &fd, &type, &code, &value);
    if (!ret) return NULL;

    struct input_event event;
    struct timeval tval;
    memset(&event, 0, sizeof(event));
    gettimeofday(&tval, 0);
    event.input_event_usec = tval.tv_usec;
    event.input_event_sec = tval.tv_sec;
    event.type = type;
    event.code = code;
    event.value = value;

    if (write(fd, &event, sizeof(event)) != sizeof(event)) {
        // @todo: elaborate
        // PyErr_SetString(PyExc_OSError, "error writing event to uinput device");
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    Py_RETURN_NONE;
}


static PyObject *
uinput_enable_event(PyObject *self, PyObject *args)
{
    int fd;
    uint16_t type, code;
    unsigned long req;

    int ret = PyArg_ParseTuple(args, "ihh", &fd, &type, &code);
    if (!ret) return NULL;

    switch (type) {
        case EV_KEY: req = UI_SET_KEYBIT; break;
        case EV_ABS: req = UI_SET_ABSBIT; break;
        case EV_REL: req = UI_SET_RELBIT; break;
        case EV_MSC: req = UI_SET_MSCBIT; break;
        case EV_SW:  req = UI_SET_SWBIT;  break;
        case EV_LED: req = UI_SET_LEDBIT; break;
        case EV_FF:  req = UI_SET_FFBIT;  break;
        case EV_SND: req = UI_SET_SNDBIT; break;
        default:
            errno = EINVAL;
            goto on_err;
    }

    if (ioctl(fd, UI_SET_EVBIT, type) < 0)
        goto on_err;

    if (ioctl(fd, req, code) < 0)
        goto on_err;

    Py_RETURN_NONE;

    on_err:
        _uinput_close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}

int _uinput_begin_upload(int fd, struct uinput_ff_upload *upload)
{
    return ioctl(fd, UI_BEGIN_FF_UPLOAD, upload);
}

int _uinput_end_upload(int fd, struct uinput_ff_upload *upload)
{
    return ioctl(fd, UI_END_FF_UPLOAD, upload);
}

int _uinput_begin_erase(int fd, struct uinput_ff_erase *upload)
{
    return ioctl(fd, UI_BEGIN_FF_ERASE, upload);
}

int _uinput_end_erase(int fd, struct uinput_ff_erase *upload)
{
    return ioctl(fd, UI_END_FF_ERASE, upload);
}


static PyMethodDef MethodTable[] = {
    { "open",  uinput_open, METH_VARARGS,
      "Open uinput device node."},

    { "setup",  uinput_setup, METH_VARARGS,
      "Set an uinput device up."},

    { "create",  uinput_create, METH_VARARGS,
      "Create an uinput device."},

    { "close",  uinput_close, METH_VARARGS,
      "Destroy uinput device."},

    { "write",  uinput_write, METH_VARARGS,
      "Write event to uinput device."},

    { "enable", uinput_enable_event, METH_VARARGS,
      "Enable a type of event."},

    { "set_phys", uinput_set_phys, METH_VARARGS,
      "Set physical path"},

    { "get_sysname", uinput_get_sysname, METH_VARARGS,
      "Obtain the sysname of the uinput device."},

    { "set_prop", uinput_set_prop, METH_VARARGS,
      "Set device input property"},

    { NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_uinput",
    "Python bindings for parts of linux/uinput.c",
    -1,          /* m_size */
    MethodTable, /* m_methods */
    NULL,        /* m_reload */
    NULL,        /* m_traverse */
    NULL,        /* m_clear */
    NULL,        /* m_free */
};

static PyObject *
moduleinit(void)
{
    PyObject* m = PyModule_Create(&moduledef);
    if (m == NULL) return NULL;

    PyModule_AddIntConstant(m, "maxnamelen", UINPUT_MAX_NAME_SIZE);
    return m;
}

PyMODINIT_FUNC
PyInit__uinput(void)
{
    return moduleinit();
}
