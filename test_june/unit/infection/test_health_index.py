import numpy as np
from june.demography import Person
from june.infection.health_index import HealthIndexGenerator

def test__smaller_than_one():
    index_list=HealthIndexGenerator.from_file()
    increasing_count=0
    for i in range(len(index_list.Prob_lists[0])):
        index_m=index_list(Person.from_attributes(age=i,sex='m'))
        index_w=index_list(Person.from_attributes(age=i,sex='w'))
        bool_m=np.sum(np.round(index_m,7)<=1)
        bool_w=np.sum(np.round(index_w,7)<=1)
        if bool_m+bool_w==14:
           increasing_count+=1
        else:
           increasing_count==increasing_count
    assert increasing_count ==121

def test__growing_index():
    index_list=HealthIndexGenerator.from_file()
    increasing_count=0
    for i in range(len(index_list.Prob_lists[0])):
        index_m=index_list(Person.from_attributes(age=i,sex='m'))
        index_w=index_list(Person.from_attributes(age=i,sex='w'))
        bool_m=all(i < j for i, j in zip(index_list.Prob_lists[0][0],
                                         index_list.Prob_lists[0][0][1:])) 
        bool_w=all(i < j for i, j in zip(index_list.Prob_lists[0][0],
                                         index_list.Prob_lists[0][0][1:]))
        if bool_m+bool_w==2:
             increasing_count+=1  
        else:
               increasing_count==increasing_count
    assert increasing_count ==121

