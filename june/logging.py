# -*- coding: utf-8 -*-
"""
https://gist.github.com/chengdi123000/42ec8ed2cbef09ee050766c2f25498cb#file-mpifilehandler-py
Created on Wed Feb 14 16:17:38 2018
This handler is used to deal with logging with mpi4py in Python3.

@author: cheng

@reference: 
    https://cvw.cac.cornell.edu/python/logging
    https://groups.google.com/forum/#!topic/mpi4py/SaNzc8bdj6U
    https://gist.github.com/JohnCEarls/8172807
"""

#%% mpi4py logging handler
from mpi4py import MPI 
import logging
from os.path import abspath

class MPIFileHandler(logging.FileHandler):                                      
    def __init__(self,
                 filename,
                 mode=MPI.MODE_WRONLY|MPI.MODE_CREATE|MPI.MODE_APPEND ,
                 encoding='utf-8',  
                 delay=False,
                 comm=MPI.COMM_WORLD ):                                                
        self.baseFilename = abspath(filename)                           
        self.mode = mode                                                        
        self.encoding = encoding                                            
        self.comm = comm                                                        
        if delay:                                                               
            #We don't open the stream, but we still need to call the            
            #Handler constructor to set level, formatter, lock etc.             
            logging.Handler.__init__(self)                                      
            self.stream = None                                                  
        else:                                                                   
           logging.StreamHandler.__init__(self, self._open())                   
                                                                                
    def _open(self):                                                            
        stream = MPI.File.Open( self.comm, self.baseFilename, self.mode )     
        stream.Set_atomicity(True)                                              
        return stream
                                                    
    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        
        Modification:
            stream is MPI.File, so it must use `Write_shared` method rather
            than `write` method. And `Write_shared` method only accept 
            bytestring, so `encode` is used. `Write_shared` should be invoked
            only once in each all of this emit function to keep atomicity.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            stream.Write_shared((msg+self.terminator).encode(self.encoding))
            #self.flush()
        except Exception:
            self.handleError(record)
                                                         
    def close(self):                                                            
        if self.stream:                                                         
            self.stream.Sync()                                                  
            self.stream.Close()                                                 
            self.stream = None                                                  

#%% example code
if __name__ == "__main__":
    comm = MPI.COMM_WORLD                                                           
    logger = logging.getLogger("rank[%i]"%comm.rank)                                
    logger.setLevel(logging.DEBUG)                                                  
                                                                                    
    mh = MPIFileHandler("logfile.log")                                           
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    mh.setFormatter(formatter)                                                      
                                                                                    
    logger.addHandler(mh)                                                           
    # 'application' code                                                            
    logger.debug('debug message')                                                   
    logger.info('info message')                                                     
    logger.warning('warn message')                                                     
    logger.error('error message')                                                   
    logger.critical('critical message')    
