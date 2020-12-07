from typing import Union
import importlib
import datetime


def read_date(date: Union[str, datetime.datetime]) -> datetime.datetime:
    """
        Read date in two possible formats, either string or datetime.date, both
        are translated into datetime.datetime to be used by the simulator

        Parameters
        ----------
        date:
            date to translate into datetime.datetime

        Returns
        -------
            date in datetime format
        """
    if type(date) is str:
        return datetime.datetime.strptime(date, "%Y-%m-%d")
    elif isinstance(date, datetime.date):
        return datetime.datetime.combine(date, datetime.datetime.min.time())
    else:
        raise TypeError("date must be a string or a datetime.date object")

def str_to_class(classname, base_policy_modules=("june.policy",)):
    for module_name in base_policy_modules:
        try:
            module = importlib.import_module(module_name)
            return getattr(module, classname)
        except AttributeError:
            continue
    raise ValueError(f"Cannot find policy {classname} in paths!")

