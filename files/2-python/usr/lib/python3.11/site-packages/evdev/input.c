
/*
 * Python bindings to certain linux input subsystem functions.
 *
 * While everything here can be implemented in pure Python with struct and
 * fcntl.ioctl, imho, it is much more straightforward to do so in C.
 *
 */

#include <Python.h>

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#ifdef __FreeBSD__
#include <dev/evdev/input.h>
#else
#include <linux/input.h>
#endif

#ifndef input_event_sec
#define input_event_sec time.tv_sec
#define input_event_usec time.tv_usec
#endif

#define MAX_NAME_SIZE 256

extern char*  EV_NAME[EV_CNT];
extern int    EV_TYPE_MAX[EV_CNT];
extern char** EV_TYPE_NAME[EV_CNT];
extern char*  BUS_NAME[];


int test_bit(const char* bitmask, int bit) {
    return bitmask[bit/8] & (1 << (bit % 8));
}


// Read input event from a device and return a tuple that mimics input_event
static PyObject *
device_read(PyObject *self, PyObject *args)
{
    int fd;
    struct input_event event;

    // get device file descriptor (O_RDONLY|O_NONBLOCK)
    if (PyArg_ParseTuple(args, "i", &fd) < 0)
        return NULL;

    int n = read(fd, &event, sizeof(event));

    if (n < 0) {
        if (errno == EAGAIN) {
            Py_INCREF(Py_None);
            return Py_None;
        }

        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    PyObject* sec  = PyLong_FromLong(event.input_event_sec);
    PyObject* usec = PyLong_FromLong(event.input_event_usec);
    PyObject* val  = PyLong_FromLong(event.value);
    PyObject* py_input_event = NULL;

    py_input_event = Py_BuildValue("OOhhO", sec, usec, event.type, event.code, val);
    Py_DECREF(sec);
    Py_DECREF(usec);
    Py_DECREF(val);

    return py_input_event;
}


// Read multiple input events from a device and return a list of tuples
static PyObject *
device_read_many(PyObject *self, PyObject *args)
{
    int fd;

    // get device file descriptor (O_RDONLY|O_NONBLOCK)
    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    PyObject* event_list = PyList_New(0);
    PyObject* py_input_event = NULL;
    PyObject* sec  = NULL;
    PyObject* usec = NULL;
    PyObject* val  = NULL;

    struct input_event event[64];

    size_t event_size = sizeof(struct input_event);
    ssize_t nread = read(fd, event, event_size*64);

    if (nread < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        Py_DECREF(event_list);
        return NULL;
    }

    // Construct a list of event tuples, which we'll make sense of in Python
    for (unsigned i = 0 ; i < nread/event_size ; i++) {
        sec  = PyLong_FromLong(event[i].input_event_sec);
        usec = PyLong_FromLong(event[i].input_event_usec);
        val  = PyLong_FromLong(event[i].value);

        py_input_event = Py_BuildValue("OOhhO", sec, usec, event[i].type, event[i].code, val);
        PyList_Append(event_list, py_input_event);

        Py_DECREF(py_input_event);
        Py_DECREF(sec);
        Py_DECREF(usec);
        Py_DECREF(val);
    }

    return event_list;
}


// Get the event types and event codes that the input device supports
static PyObject *
ioctl_capabilities(PyObject *self, PyObject *args)
{
    int fd, ev_type, ev_code;
    char ev_bits[EV_MAX/8 + 1], code_bits[KEY_MAX/8 + 1];
    struct input_absinfo absinfo;

    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    // @todo: figure out why fd gets zeroed on an ioctl after the
    // refactoring and get rid of this workaround
    const int _fd = fd;

    // Capabilities is a mapping of supported event types to lists of handled
    // events e.g: {1: [272, 273, 274, 275], 2: [0, 1, 6, 8]}
    PyObject* capabilities = PyDict_New();
    PyObject* eventcodes = NULL;
    PyObject* evlong = NULL;
    PyObject* capability = NULL;
    PyObject* py_absinfo = NULL;
    PyObject* absitem = NULL;

    memset(&ev_bits, 0, sizeof(ev_bits));

    if (ioctl(_fd, EVIOCGBIT(0, sizeof(ev_bits)), ev_bits) < 0)
        goto on_err;

    // Build a dictionary of the device's capabilities
    for (ev_type=0 ; ev_type<EV_MAX ; ev_type++) {
        if (test_bit(ev_bits, ev_type)) {

            capability = PyLong_FromLong(ev_type);
            eventcodes = PyList_New(0);

            memset(&code_bits, 0, sizeof(code_bits));
            ioctl(_fd, EVIOCGBIT(ev_type, sizeof(code_bits)), code_bits);

            for (ev_code = 0; ev_code < KEY_MAX; ev_code++) {
                if (test_bit(code_bits, ev_code)) {
                    // Get abs{min,max,fuzz,flat} values for ABS_* event codes
                    if (ev_type == EV_ABS) {
                        memset(&absinfo, 0, sizeof(absinfo));
                        ioctl(_fd, EVIOCGABS(ev_code), &absinfo);

                        py_absinfo = Py_BuildValue("(iiiiii)",
                                                   absinfo.value,
                                                   absinfo.minimum,
                                                   absinfo.maximum,
                                                   absinfo.fuzz,
                                                   absinfo.flat,
                                                   absinfo.resolution);

                        evlong = PyLong_FromLong(ev_code);
                        absitem = Py_BuildValue("(OO)", evlong, py_absinfo);

                        // absitem -> tuple(ABS_X, (0, 255, 0, 0))
                        PyList_Append(eventcodes, absitem);

                        Py_DECREF(absitem);
                        Py_DECREF(py_absinfo);
                    }
                    else {
                        evlong = PyLong_FromLong(ev_code);
                        PyList_Append(eventcodes, evlong);
                    }

                    Py_DECREF(evlong);
                }
            }
            // capabilities[EV_KEY] = [KEY_A, KEY_B, KEY_C, ...]
            // capabilities[EV_ABS] = [(ABS_X, (0, 255, 0, 0)), ...]
            PyDict_SetItem(capabilities, capability, eventcodes);

            Py_DECREF(capability);
            Py_DECREF(eventcodes);
        }
    }

    return capabilities;

    on_err:
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}


// An all-in-one function for describing an input device
static PyObject *
ioctl_devinfo(PyObject *self, PyObject *args)
{
    int fd;

    struct input_id iid;
    char name[MAX_NAME_SIZE];
    char phys[MAX_NAME_SIZE] = {0};
    char uniq[MAX_NAME_SIZE] = {0};

    int ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    memset(&iid,  0, sizeof(iid));

    if (ioctl(fd, EVIOCGID, &iid) < 0)                 goto on_err;
    if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) < 0) goto on_err;

    // Some devices do not have a physical topology associated with them
    ioctl(fd, EVIOCGPHYS(sizeof(phys)), phys);

    // Some kernels have started reporting bluetooth controller MACs as phys.
    // This lets us get the real physical address. As with phys, it may be blank.
    ioctl(fd, EVIOCGUNIQ(sizeof(uniq)), uniq);

    return Py_BuildValue("hhhhsss", iid.bustype, iid.vendor, iid.product, iid.version,
                         name, phys, uniq);

    on_err:
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
}


static PyObject *
ioctl_EVIOCGABS(PyObject *self, PyObject *args)
{
    int fd, ev_code;
    struct input_absinfo absinfo;
    PyObject* py_absinfo = NULL;

    int ret = PyArg_ParseTuple(args, "ii", &fd, &ev_code);
    if (!ret) return NULL;

    memset(&absinfo, 0, sizeof(absinfo));
    ret = ioctl(fd, EVIOCGABS(ev_code), &absinfo);
    if (ret == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    py_absinfo = Py_BuildValue("(iiiiii)",
                               absinfo.value,
                               absinfo.minimum,
                               absinfo.maximum,
                               absinfo.fuzz,
                               absinfo.flat,
                               absinfo.resolution);
    return py_absinfo;
}


static PyObject *
ioctl_EVIOCSABS(PyObject *self, PyObject *args)
{
    int fd, ev_code;
    struct input_absinfo absinfo;

    int ret = PyArg_ParseTuple(args,
                               "ii(iiiiii)",
                               &fd,
                               &ev_code,
                               &absinfo.value,
                               &absinfo.minimum,
                               &absinfo.maximum,
                               &absinfo.fuzz,
                               &absinfo.flat,
                               &absinfo.resolution);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCSABS(ev_code), &absinfo);
    if (ret == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject *
ioctl_EVIOCGREP(PyObject *self, PyObject *args)
{
    int fd, ret;
    unsigned int rep[2] = {0};
    ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCGREP, &rep);
    if (ret == -1)
        return NULL;

    return Py_BuildValue("(ii)", rep[0], rep[1]);
}


static PyObject *
ioctl_EVIOCSREP(PyObject *self, PyObject *args)
{
    int fd, ret;
    unsigned int rep[2] = {0};

    ret = PyArg_ParseTuple(args, "iii", &fd, &rep[0], &rep[1]);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCSREP, &rep);
    if (ret == -1)
        return NULL;

    return Py_BuildValue("i", ret);
}


static PyObject *
ioctl_EVIOCGVERSION(PyObject *self, PyObject *args)
{
    int fd, ret, res;
    ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCGVERSION, &res);
    if (ret == -1)
        return NULL;

    return Py_BuildValue("i", res);
}


static PyObject *
ioctl_EVIOCGRAB(PyObject *self, PyObject *args)
{
    int fd, ret, flag;
    ret = PyArg_ParseTuple(args, "ii", &fd, &flag);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCGRAB, (intptr_t)flag);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject *
ioctl_EVIOCG_bits(PyObject *self, PyObject *args)
{
    int max, fd, evtype, ret;

    ret = PyArg_ParseTuple(args, "ii", &fd, &evtype);
    if (!ret) return NULL;

    switch (evtype) {
    case EV_LED:
        max = LED_MAX; break;
    case EV_SND:
        max = SND_MAX; break;
    case EV_KEY:
        max = KEY_MAX; break;
    case EV_SW:
        max = SW_MAX; break;
    default:
        return NULL;
    }

    char bytes[(max+7)/8];
    memset(bytes, 0, sizeof bytes);

    switch (evtype) {
    case EV_LED:
        ret = ioctl(fd, EVIOCGLED(sizeof(bytes)), &bytes);
        break;
    case EV_SND:
        ret = ioctl(fd, EVIOCGSND(sizeof(bytes)), &bytes);
        break;
    case EV_KEY:
        ret = ioctl(fd, EVIOCGKEY(sizeof(bytes)), &bytes);
        break;
    case EV_SW:
        ret = ioctl(fd, EVIOCGSW(sizeof(bytes)), &bytes);
        break;
    }

    if (ret == -1)
        return NULL;

    PyObject* res = PyList_New(0);
    for (int i=0; i<=max; i++) {
        if (test_bit(bytes, i)) {
            PyList_Append(res, Py_BuildValue("i", i));
        }
    }

    return res;
}


static PyObject *
ioctl_EVIOCGEFFECTS(PyObject *self, PyObject *args)
{
    int fd, ret, res;
    ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    ret = ioctl(fd, EVIOCGEFFECTS, &res);
    if (ret == -1)
        return NULL;

    return Py_BuildValue("i", res);
}

void print_ff_effect(struct ff_effect* effect) {
    fprintf(stderr,
            "ff_effect:\n"
            "  type: %d     \n"
            "  id:   %d     \n"
            "  direction: %d\n"
            "  trigger: (%d, %d)\n"
            "  replay:  (%d, %d)\n",
            effect->type, effect->id, effect->direction,
            effect->trigger.button, effect->trigger.interval,
            effect->replay.length, effect->replay.delay
        );


    switch (effect->type) {
    case FF_CONSTANT:
        fprintf(stderr, "  constant: (%d, (%d, %d, %d, %d))\n", effect->u.constant.level,
                effect->u.constant.envelope.attack_length,
                effect->u.constant.envelope.attack_level,
                effect->u.constant.envelope.fade_length,
                effect->u.constant.envelope.fade_level);
        break;
    case FF_RUMBLE:
        fprintf(stderr, "  rumble: (%d, %d)\n",
		effect->u.rumble.strong_magnitude,
		effect->u.rumble.weak_magnitude);
        break;
    }
}


static PyObject *
upload_effect(PyObject *self, PyObject *args)
{
    int fd, ret;
    PyObject* effect_data;
    ret = PyArg_ParseTuple(args, "iO", &fd, &effect_data);
    if (!ret) return NULL;

    void* data = PyBytes_AsString(effect_data);
    struct ff_effect effect = {};
    memmove(&effect, data, sizeof(struct ff_effect));

    // print_ff_effect(&effect);

    ret = ioctl(fd, EVIOCSFF, &effect);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return Py_BuildValue("i", effect.id);
}


static PyObject *
erase_effect(PyObject *self, PyObject *args)
{
    int fd, ret;
    PyObject* ff_id_obj;
    ret = PyArg_ParseTuple(args, "iO", &fd, &ff_id_obj);
    if (!ret) return NULL;

    long ff_id = PyLong_AsLong(ff_id_obj);
    ret = ioctl(fd, EVIOCRMFF, ff_id);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
ioctl_EVIOCGPROP(PyObject *self, PyObject *args)
{
    int fd, ret;

    ret = PyArg_ParseTuple(args, "i", &fd);
    if (!ret) return NULL;

    char bytes[(INPUT_PROP_MAX+7)/8];
    memset(bytes, 0, sizeof bytes);

    ret = ioctl(fd, EVIOCGPROP(sizeof(bytes)), &bytes);

    if (ret == -1)
        return NULL;

    PyObject* res = PyList_New(0);
    for (int i=0; i<INPUT_PROP_MAX; i++) {
        if (test_bit(bytes, i)) {
            PyList_Append(res, Py_BuildValue("i", i));
        }
    }

    return res;
}



static PyMethodDef MethodTable[] = {
    { "ioctl_devinfo",        ioctl_devinfo,        METH_VARARGS, "fetch input device info" },
    { "ioctl_capabilities",   ioctl_capabilities,   METH_VARARGS, "fetch input device capabilities" },
    { "ioctl_EVIOCGABS",      ioctl_EVIOCGABS,      METH_VARARGS, "get input device absinfo"},
    { "ioctl_EVIOCSABS",      ioctl_EVIOCSABS,      METH_VARARGS, "set input device absinfo"},
    { "ioctl_EVIOCGREP",      ioctl_EVIOCGREP,      METH_VARARGS},
    { "ioctl_EVIOCSREP",      ioctl_EVIOCSREP,      METH_VARARGS},
    { "ioctl_EVIOCGVERSION",  ioctl_EVIOCGVERSION,  METH_VARARGS},
    { "ioctl_EVIOCGRAB",      ioctl_EVIOCGRAB,      METH_VARARGS},
    { "ioctl_EVIOCGEFFECTS",  ioctl_EVIOCGEFFECTS,  METH_VARARGS, "fetch the number of effects the device can keep in its memory." },
    { "ioctl_EVIOCG_bits",    ioctl_EVIOCG_bits,    METH_VARARGS, "get state of KEY|LED|SND|SW"},
    { "ioctl_EVIOCGPROP",     ioctl_EVIOCGPROP,     METH_VARARGS, "get device properties"},
    { "device_read",          device_read,          METH_VARARGS, "read an input event from a device" },
    { "device_read_many",     device_read_many,     METH_VARARGS, "read all available input events from a device" },
    { "upload_effect",        upload_effect,        METH_VARARGS, "" },
    { "erase_effect",         erase_effect,         METH_VARARGS, "" },

    { NULL, NULL, 0, NULL}
};


#define MODULE_NAME "_input"
#define MODULE_HELP "Python bindings to certain linux input subsystem functions"

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    MODULE_NAME,
    MODULE_HELP,
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
    return m;
}

PyMODINIT_FUNC
PyInit__input(void)
{
    return moduleinit();
}

#else
static PyObject *
moduleinit(void)
{
    PyObject* m = Py_InitModule3(MODULE_NAME, MethodTable, MODULE_HELP);
    if (m == NULL) return NULL;
    return m;
}

PyMODINIT_FUNC
init_input(void)
{
    moduleinit();
}
#endif
