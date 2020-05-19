import numpy as np
from june.demography import Person
from june.infection.health_index import HealthIndexGenerator

def test__smaller_than_one():
    index_list=HealthIndexGenerator.from_file()
    increasing_count=0
    for i in range(len(index_list.prob_lists[0])):
        index_m=index_list(Person(age=i,sex='m'))
        index_w=index_list(Person(age=i,sex='w'))
        bool_m=np.sum(index_m<1)
        bool_w=np.sum(index_w<1)
        increasing_count+=1 if bool_m+bool_w==10 else increasing_count==increasing_count
    assert increasing_count ==121

def test__growing_index():
    index_list=HealthIndexGenerator.from_file()
    increasing_count=0
    for i in range(len(index_list.prob_lists[0])):
        index_m=index_list(Person(age=i,sex='m'))
        index_w=index_list(Person(age=i,sex='w'))
        bool_m=all(i < j for i, j in zip(index_list.prob_lists[0][0],
                                         index_list.prob_lists[0][0][1:])) 
        bool_w=all(i < j for i, j in zip(index_list.prob_lists[0][0],
                                         index_list.prob_lists[0][0][1:]))
        increasing_count+=1 if bool_m+bool_w==2 else increasing_count==increasing_count
    assert increasing_count ==121

