import numpy as np
def read_dataset(dataset, index1=None, index2=None):
    if index1 is None:
        index1 = 0
    if index2 is None:
        index2 = dataset.len()
    dataset_shape = dataset.shape
    if len(dataset_shape) > 1:
        load_shape = [index2-index1] + list(dataset_shape[1:])
    else:
        load_shape = index2-index1
    ret = np.empty(load_shape, dtype=dataset.dtype)
    dataset.read_direct(ret, np.s_[index1:index2], np.s_[0:index2-index1])
    return ret
