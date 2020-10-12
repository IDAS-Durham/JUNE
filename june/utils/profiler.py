import cProfile
from june.mpi_setup import mpi_rank, mpi_comm 

# a decorator for profiling
def profile(filename=None, comm=mpi_comm):
    def prof_decorator(f):
        def wrap_f(*args, **kwargs):
            pr = cProfile.Profile()
            pr.enable()
            result = f(*args, **kwargs)
            pr.disable()

            if filename is None:
                pr.print_stats()
            else:
                filename_r = filename + ".{}".format(mpi_rank)
                pr.dump_stats(filename_r)

            return result

        return wrap_f

    return prof_decorator



