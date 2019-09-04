import abc

class VMElement(abc.ABC):
  """ Base class for InputStrip and OutputBus. """
  def __init__(self, remote, index):
    self._remote = remote
    self.index = index

  def get(self, param, **kwargs):
    """ Returns the param value of the current strip. """
    return self._remote.get(f'{self.identifier}.{param}', **kwargs)
  def set(self, param, val, **kwargs):
    """ Sets the param value of the current strip. """
    self._remote.set(f'{self.identifier}.{param}', val, **kwargs)
  
  @abc.abstractmethod
  def identifier(self):
    pass
    

def bool_prop(param):
  """ A boolean VM parameter. """
  def getter(self):
    return (self.get(param) == 1)
  def setter(self, val):
    return self.set(param, 1 if val else 0)
  return property(getter, setter)

def str_prop(param):
  """ A string VM parameter. """
  def getter(self):
    return self.get(param, string=True)
  def setter(self, val):
    return self.set(param, val)
  return property(getter, setter)

def float_prop(param, range=None):
  """ A floating point VM parameter. """
  def getter(self):
    val = self.get(param)
    if range:
      lo, hi = range
      val = (val-lo)/(hi-lo)
    return val
  def setter(self, val):
    if range:
      lo, hi = range
      val = val*(hi-lo)+lo
    return self.set(param, val)
  return property(getter, setter)