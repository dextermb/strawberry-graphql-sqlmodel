class MetaKeywordArguments(type):
  def __new__(cls, name, bases, class_dict, **kwargs):
    for key, value in kwargs.items():
      class_dict[key] = value

    return super().__new__(cls, name, bases, class_dict)

  def __init__(cls, name, bases, class_dict, **kwargs):
    return super().__init__(name, bases, class_dict)
