import ctypes as ct
import time

from .driver import dll
from .errors import VMRError, VMRDriverError
from .input import InputStrip
from .output import OutputBus
from . import kinds

class VMRemote:
  """ Wrapper around Voicemeeter Remote's C API. """
  def __init__(self, delay=.015):
    self.delay = delay
    self.cache = {}

  def _call(self, fn, *args, check=True, expected=(0,)):
    """
    Runs a C API function.
    
    Raises an exception when check is True and the
    function's return value is not 0 (OK).
    """
    fn_name = 'VBVMR_' + fn
    retval = getattr(dll, fn_name)(*args)
    if check and retval not in expected:
      raise VMRDriverError(fn_name, retval)
    time.sleep(self.delay)
    return retval

  def _login(self):
    self._call('Login')
  def _logout(self):
    self._call('Logout')
  
  @property
  def kind(self):
    """ Returns the type of Voicemeeter installation (basic, banana, potato). """
    buf = ct.c_long()
    self._call('GetVoicemeeterType', ct.byref(buf))
    val = buf.value
    if val == 1:
      return 'basic'
    elif val == 2:
      return 'banana'
    elif val == 3:
      return 'potato'
    else:
      raise VMRError(f'Unexpected Voicemeeter type: {val}')

  @property
  def version(self):
    """ Returns Voicemeeter's version as a tuple (v1, v2, v3, v4) """
    buf = ct.c_long()
    self._call('GetVoicemeeterVersion', ct.byref(buf))
    v1 = (buf.value & 0xFF000000) >> 24
    v2 = (buf.value & 0x00FF0000) >> 16
    v3 = (buf.value & 0x0000FF00) >> 8
    v4 = (buf.value & 0x000000FF)
    return (v1, v2, v3, v4)

  @property
  def dirty(self):
    """ True iff UI parameters have been updated. """
    val = self._call('IsParametersDirty', expected=(0,1))
    return (val == 1)
  
  def get(self, param, string=False):
    """ Retrieves a parameter. """
    print('GET', param)
    param = param.encode('ascii')
    if not self.dirty:
      if param in self.cache:
        return self.cache[param]

    if string:
      buf = (ct.c_wchar * 512)()
      self._call('GetParameterStringW', param, ct.byref(buf))
    else:
      buf = ct.c_float()
      self._call('GetParameterFloat', param, ct.byref(buf))
    val = buf.value
    self.cache[param] = val
    return val
  
  def set(self, param, val):
    """ Updates a parameter. """
    print('SET', param)
    param = param.encode('ascii')
    if isinstance(val, str):
      if len(val) >= 512:
        raise VMRError('String is too long')
      self._call('SetParameterStringW', param, ct.c_wchar_p(val))
    else:
      self._call('SetParameterFloat', param, ct.c_float(float(val)))

  def show(self):
    """ Shows Voicemeeter if it's hidden. """
    self.set('Command.Show', 1)
  def shutdown(self):
    """ Closes Voicemeeter. """
    self.set('Command.Shutdown', 1)
  def restart(self):
    """ Restarts Voicemeeter's audio engine. """
    self.set('Command.Restart', 1)

  def apply(self, mapping):
    """ Sets all parameters of a dict. """
    for key, submapping in mapping.items():
      strip, index = key.split('-')
      index = int(index)
      if strip in ('in', 'input'):
        target = self.inputs[index]
      elif strip in ('out', 'output'):
        target = self.outputs[index]
      else:
        raise ValueError(strip)
      target.apply(submapping)

  def __enter__(self):
    self._login()
    return self
  def __exit__(self, type, value, traceback):
    self._logout()


def _make_remote(kind):
  """
  Creates a new remote class and sets its number of inputs
  and outputs for a VM kind.
  
  The returned class will subclass VMRemote.
  """
  def init(self, *args, **kwargs):
    VMRemote.__init__(self, *args, **kwargs)
    self.kind = kind
    self.num_A, self.num_B = kind.layout
    self.inputs = [InputStrip.make((i < self.num_A), self, i) for i in range(self.num_A+self.num_B)]
    self.outputs = [OutputBus.make((i < self.num_B), self, i) for i in range(self.num_A+self.num_B)]
  return type(f'VMRemote{kind.name}', (VMRemote,), {
    '__init__': init
  })

_remotes = {kind.id: _make_remote(kind) for kind in kinds.all}

def connect(kind_id, *args, **kwargs):
  """ Connect to Voicemeeter and sets its strip layout. """
  try:
    cls = _remotes[kind_id]
    return cls(*args, **kwargs)
  except KeyError as err:
    raise VMRError(f'Invalid Voicemeeter kind: {kind_id}')