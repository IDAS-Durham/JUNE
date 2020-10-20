"""
Script to unify checkpoints after running a parallel simulation.
"""
import sys

base_path = sys.argv[1]

from june.hdf5_savers.checkpoint_saver import combine_checkpoints_for_ranks

combine_checkpoints_for_ranks(base_path)
