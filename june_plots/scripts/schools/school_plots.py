import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import h5py
import math

from june.hdf5_savers import generate_world_from_hdf5
from pathlib import Path


from june import paths

from numba import jit

#iomd = pd.read_csv(
#    paths.data_path / "input/demography/index_of_multiple_deprivation.csv",
#    index_col = 0
#)



earth_radius = 6371  # km

default_school_data_path = (
    paths.data_path / "input/schools/england_schools.csv"
)

class SchoolPlots:
    """
    Class for plotting schools

    Parameters
    ----------
    world
    """

    def __init__(self, world):
        self.world = world

    def load_school_data(
        self,
        school_data_path = default_school_data_path,
        use_global=False
    ):

        self.school_data = pd.read_csv(school_data_path, index_col=0)
        if use_global is False:
            world_areas = [area.name for area in self.world.areas]
            self.school_data = self.school_data.query("oa in @world_areas")
        self.primary_data = self.school_data.query("sector == 'primary'")
        self.secondary_data = self.school_data.query("sector == 'secondary'")
        self.mixed_data = self.school_data.query("sector == 'primary_secondary'")

    #@jit
    def _distance(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
        radius = 6371 # km

        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
      
        d = radius * c 

        return d # km
    
    def _get_school_sizes(self,):

        school_sizes = []
        primary_sizes = []
        secondary_sizes = []

        for school in self.world.schools:
            school_sizes.append(school.size)
            if school.sector == "primary":
                primary_sizes.append(school.size)
            elif school.sector == "secondary":
                secondary_sizes.append(school.size)
            else:
                pass
                # not sure how to do primary/secondary split for 
                # school.sector=primary_secondary       
        self.school_sizes = np.array(school_sizes)
        self.primary_sizes = np.array(primary_sizes)
        self.secondary_sizes = np.array(secondary_sizes)
        
    def plot_school_sizes(
        self,
        bins=None, 
        split_primary_secondary=False,
        age_split=11
    ):
        """Plot number of students per school for given world
        
        Parameters
        ----------
        bins
            histogram bins. Default [0,100,200,...,1900,2000]
        split_primary_secondary
            if True, include students in sector primary_secondary schools in the
            specific 'primary', 'secondary' bins, with split based on student age.
            if False, include these students in 'mixed' histogram.
            default False, as real data does not make this division.
        age_split
            age to split primary_secondary. Default age 11.
            If student.age < age_split, include in primary, else in secondary.
        """
        school_sizes = []
        primary_sizes = []
        secondary_sizes = []
        mixed_sizes = []

        for school in self.world.schools:
            school_sizes.append(school.size)
           
            if school.sector == "primary":
                primary_sizes.append(school.size)
            elif school.sector == "secondary":
                secondary_sizes.append(school.size)
            else:
                if split_primary_secondary:
                    n_primary = 0
                    n_secondary = 0
                    for student in school.students:
                        if student.age < age_split:
                            n_primary += 1
                        else:
                            n_secondary += 1

                    primary_sizes.append(n_primary)
                    secondary_sizes.append(n_secondary)
                else:
                    mixed_sizes.append(school.size)

        if bins is None:
            bins = np.arange(0,2100,100)

        mids = 0.5*(bins[1:]+bins[:-1])

        primary_data_hist,_ = np.histogram(self.primary_data['NOR'],bins=bins)
        secondary_data_hist,_ = np.histogram(self.secondary_data['NOR'],bins=bins)
        mixed_data_hist,_ = np.histogram(self.mixed_data['NOR'],bins=bins)

        
        f, ax = plt.subplots()
        #ax.hist(school_sizes,bins=bins,label="all")
        ax.hist(primary_sizes, bins=bins, label="primary",alpha=0.7)
        ax.hist(secondary_sizes, bins=bins, label="secondary",alpha=0.7)
        ax.hist(mixed_sizes, bins=bins, label="mixed",alpha=0.7)

        ax.plot(mids, primary_data_hist,label="NOMIS primary")
        ax.plot(mids, secondary_data_hist,label="NOMIS secondary")
        ax.plot(mids, mixed_data_hist, label="NOMIS mixed")

        ax.legend()
        ax.set_xlabel("School size (number of students)")
        ax.set_ylabel("Frequency")

        return ax

    def plot_student_teacher_ratio(self,bins=None):
        """Histogram of n_students/n_teachers for 'all' schools, 
        specific 'primary', specific 'secondary'. 
        Schools with sector 'primary_secondary' are only included in 'all'.
        
        Parameters
        ----------
        bins
            histogram bins. default from min(ratio)-2, max(ratio) +2 in steps of 2.
        """
        school_sizes = []
        primary_sizes = []
        secondary_sizes = []
        mixed_sizes = []

        n_teachers = []
        primary_teachers = []
        secondary_teachers = []
        mixed_teachers = []

        for school in self.world.schools:

            school_sizes.append(school.size)
            n_teachers.append(school.n_teachers)

            if school.sector == "primary":
                primary_sizes.append(school.size)
                primary_teachers.append(school.n_teachers)
            elif school.sector == "secondary":
                secondary_sizes.append(school.size)
                secondary_teachers.append(school.n_teachers)
            else:
                mixed_sizes.append(school.size)
                mixed_teachers.append(school.n_teachers)

        school_sizes = np.array(school_sizes)
        primary_sizes = np.array(primary_sizes)
        secondary_sizes = np.array(secondary_sizes)
        mixed_sizes = np.array(mixed_sizes)

        n_teachers = np.array(n_teachers)
        primary_teachers = np.array(primary_teachers)
        secondary_teachers = np.array(secondary_teachers)
        mixed_teachers = np.array(mixed_teachers)

        st_ratio = school_sizes/n_teachers   
        primary_st_ratio = primary_sizes/primary_teachers
        secondary_st_ratio = secondary_sizes/secondary_teachers
        mixed_st_ratio = mixed_sizes/mixed_teachers
       
        bins = np.arange( int(min(st_ratio))-2, int(max(st_ratio))+2, 1)

        primary_mean = np.mean(primary_st_ratio)
        primary_data_mean = 22.0

        secondary_mean = np.mean(secondary_st_ratio)
        secondary_data_mean = 15.5

        # data mean from
        # https://assets.publishing.service.gov.uk/
        # government/uploads/system/uploads/attachment_data/file/183364/DFE-RR169.pdf

        mids = 0.5*(bins[1:] + bins[:-1])   

        f, ax = plt.subplots()
        ax.hist(primary_st_ratio,bins=bins,label="primary",alpha=0.7)
        ax.hist(secondary_st_ratio,bins=bins,label="secondary",alpha=0.7)
        ax.hist(mixed_st_ratio,bins=bins,label="mixed",alpha=0.7)
        ax.axvline(primary_mean,color='r',label="JUNE pri. mean")
        ax.axvline(primary_data_mean,color='r',ls='--', label="2011 UK pri. mean")
        ax.axvline(secondary_mean,color='k',label="JUNE sec. mean")
        ax.axvline(secondary_data_mean,color='k',ls='--',label="2011 UK sec. mean")
        ax.legend(bbox_to_anchor=(1.05, 1))
        ax.set_xlabel("Student:Teacher ratio")
        ax.set_ylabel("Frequency")

        return ax

    def plot_distance_to_school(
        self,
        bins=None, 
        split_primary_secondary=True,
        age_split=11
    ):
        """Histogram of distance travelled to school per student, for 'mixed',
        specific 'primary', specific 'secondary'. Can split students in 
        mixed sector 'primary_secondary' based on age (see parameters).
        
        Parameters
        ----------
        bins
            histogram bins (in km). Default [0,5,10...,70,75].
        split_primary_secondary
            Default False.
            if True, include students in sector primary_secondary schools in the
            specific 'primary', 'secondary' bins, with split based on student age.
            if False, include these students in 'mixed' histogram.
        age_split
            age to split primary_secondary. Default age 11.
            If student.age < age_split, include in primary, else in secondary.
        """

        school_distances = []
        primary_distances = []
        secondary_distances = []
        mixed_distances = []
       
        for school in self.world.schools:
            for student in school.students:
                dist = self._distance(
                    student.area.coordinates,
                    school.area.coordinates
                )
                school_distances.append(dist)
                if school.sector == "primary":
                    primary_distances.append(dist)
                elif school.sector == "secondary":
                    secondary_distances.append(dist)
                else:
                    if split_primary_secondary:
                        if student.age < age_split:
                            primary_distances.append(dist)
                        else:
                            secondary_distances.append(dist)
                    else:
                        mixed_distances.append(dist)
        if bins is None:
            bins = np.arange(0,80,5)
            
        f, ax = plt.subplots()
        #ax.hist(
        #    school_distances, bins=bins, log=True,
        #    label="all", alpha=0.5,
        #)
        ax.hist(
            primary_distances, bins=bins, log=True,
            label="primary", alpha=0.7,
        )
        ax.hist(
            secondary_distances, bins=bins, log=True,
            label="secondary", alpha=0.7,
        )
        if len(mixed_distances) > 0:
            ax.hist(
                mixed_distances, bins=bins, log=True,
                label="mixed", alpha=0.7,
            )
        ax.legend()
        ax.set_xlabel("Distance travelled to school (km)")
        ax.set_ylabel("Number of students")

        return ax















