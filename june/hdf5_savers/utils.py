import time
from venv import logger
import numpy as np


def read_dataset(dataset, index1=None, index2=None, max_retries=3):
    """
    Enhanced version of read_dataset with retry mechanism
    while maintaining the original functionality
    """
    if index1 is None:
        index1 = 0
    if index2 is None:
        index2 = dataset.len()

    dataset_shape = dataset.shape
    
    # Determine load shape
    if len(dataset_shape) > 1:
        load_shape = [index2 - index1] + list(dataset_shape[1:])
    else:
        load_shape = index2 - index1

    # Create empty array for data
    ret = np.empty(load_shape, dtype=dataset.dtype)

    # Add retry mechanism
    for attempt in range(max_retries):
        try:
            dataset.read_direct(ret, np.s_[index1:index2], np.s_[0:index2-index1])
            return ret
        except (OSError, IOError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # Wait before retry
            logger.warning(f"Retry {attempt + 1} of {max_retries} for dataset read")


def write_dataset(group, dataset_name, data, index1=None, index2=None):
    if dataset_name not in group:
        if len(data.shape) > 1:
            maxshape = (None, *data.shape[1:])
        else:
            maxshape = (None,)
        group.create_dataset(dataset_name, data=data, maxshape=maxshape)
    else:
        if len(data.shape) > 1:
            newshape = (group[dataset_name].shape[0] + data.shape[0], *data.shape[1:])
        else:
            newshape = (group[dataset_name].shape[0] + data.shape[0],)
        group[dataset_name].resize(newshape)
        group[dataset_name][index1:index2] = data
