import numpy as np
def read_dataset(dataset, index1=None, index2=None):
    ret = np.empty(dataset.shape, dtype=dataset.dtype)
    if index1 is None:
        index1 = 0
    if index2 is None:
        index2 = dataset.len()
    dataset.read_direct(ret, np.s_[index1:index2], np.s_[0:index2-index1])
    return ret
