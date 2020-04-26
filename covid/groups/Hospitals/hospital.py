from sklearn.neighbors import BallTree
from covid.groups import Group
import numpy as np

class Hospital(Group):
    ''' 
    hospitals to be assigned to each Group
    '''
    
    def __init__(self,hospital_id,coordinates,n_beds):
        self.id = hospital_id
        self.coordinates = coordinates
        self.beds = n_beds
        print ("Boris build a new hospital [",self.id,"] with ",self.beds," beds.")
        
        
class Hospitals:
    def __init__(self,hospital_df):
        #self.world = world
        #self.init_hospitals(hospital_df)
        """
        this is for a quick development and testing round
        """
        self.hospital       = Hospital("test",None,10)
        self.hospital_trees = None

    def init_hospitals(self,hospital_df):
        hospital_trees = self._create_hospital_tree(hospital_df)
        self.hospital_trees = hospital_trees
        
        
    def _create_hospital_tree(self,hospital_df):
        hospital_tree = BallTree(
            np.deg2rad(hospital_df[["Latitude", "Longitude"]].values), metric="haversine"
            )
        return hospital_tree
    
    def get_closest_hospital(self,area,k):
        """
        this is for a quick development and testing round
        """
        if self.hospital_trees==None:
           return self.hospital 
        """    
        hospital_tree = self.hospital_trees
        distances,neighbours = hospital_tree.query(
            np.deg2rad(area.coordinates.reshape(1,-1)),k = k,sort_results=True
            )
        
        return neighbours
        """
