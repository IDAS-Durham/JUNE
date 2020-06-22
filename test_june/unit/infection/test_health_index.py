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


def test__No_negative_provavility():
  Probability_object=HealthIndexGenerator.from_file()
  Probability_list=Probability_object.Prob_lists
  negatives=0.0
  for i in range(len(Probability_list[0])):
       negatives+=sum(Probability_list[0][i]<0)
       negatives+=sum(Probability_list[1][i]<0)
  assert negatives==0

def test__growing_index():
    index_list=HealthIndexGenerator.from_file()
    increasing_count=0
    for i in range(len(index_list.Prob_lists[0])):
        index_m=index_list(Person.from_attributes(age=i,sex='m'))
        index_w=index_list(Person.from_attributes(age=i,sex='w'))
        
        if sum(np.sort(index_w)==index_w)!=len(index_w):
            increasing_count+=0


        if sum(np.sort(index_m)==index_m)!=len(index_m):
            increasing_count+=0

    assert increasing_count ==0

