import sys

"""
organise data according to
 * lower age threshold,
 * probabilities for (non-symptomatic, influenza-like symptoms, pneumonia,
                      hospitalisation, intensive care, fatality)
The problem is to backwards calculate the rates for each one.  For a first model
I use the IC data
(table 1 of
     https://www.imperial.ac.uk/media/imperial-college/medicine/sph/ide/gida-fellowships/ImperialCollege-june19-NPI-modelling-16-03-2020.pdf)
in the following way: I will assume that a certain value of cases is non-symptomatic
(IC gives 40-50 %, this is a model parameter), and will assume that the symptomatic
cases that do not need hospitalisation have either influenza-like or penumonia-like
symptoms where I distribute them according to the ratios in the RKI publication
(table 1/column 2 of
     https://www.rki.de/DE/Content/Infekt/EpidBull/Archiv/2020/Ausgaben/17_20.pdf?__blob=publicationFile)
For this I assume a "pneumonia probability for the asyptomatic, non-hospitalised cases
given by Pneumonia/(ILI+Peumonia) - probably too crude.

I think I do not fully trust the ratio of infected fatality rate and probability to end
up in an ICU unit - I have added this as comment for each age group, roughly rounded.
"""


ICdata = [
    [0.,  [  0.1,  0.005,  0.002]], # 40%
    [10., [  0.3,  0.015,  0.006]], # 40%
    [20., [  1.2,  0.060,  0.030]], # 50%
    [30., [  3.2,  0.160,  0.080]], # 50%
    [40., [  4.9,  0.310,  0.150]], # 50%
    [50., [ 10.2,  1.240,  0.600]], # 50%
    [60., [ 16.6,  4.550,  2.200]], # 50%
    [70., [ 24.3, 10.500,  5.100]], # 50%
    [80., [ 27.3, 19.400,  9.300]], # 50%
]

RKIdata = [
    [0.,   4.0],
    [5.,   4.0],
    [15.,  1.5],
    [35.,  4.0],
    [60., 14.0],
    [80., 46.0]
]

class HealthIndex:
    def __init__(self, config=None):
        if config is None or "health_datafiles" not in config:
            self.ICdata  = ICdata
            self.RKIdata = RKIdata
        if config is not None:
            self.ratio   = config["infection"]["asymptomatic_ratio"]
        else:
            self.ratio = 0.4
        for row in range(len(self.ICdata)):
            for j in range(len(self.ICdata[row][1])):
                if (j<len(self.ICdata[row][1])-1):
                    self.ICdata[row][1][j] -= self.ICdata[row][1][j+1]
                self.ICdata[row][1][j] /= 100.
        for row in range(len(self.RKIdata)):
            self.RKIdata[row][1] /= 100.

        self.index_dict = {}
        self.make_dict()

    def make_dict(self):
        lenIC  = len(self.ICdata)
        lenRKI = len(self.RKIdata)
        for age in range(120):
            ageindex  = lenIC - 1
            threshold = self.ICdata[ageindex][0]
            while threshold> 1.*age and ageindex>=0:
                ageindex  -= 1
                threshold  = self.ICdata[ageindex][0]

            hospindex = self.ICdata[ageindex][1]
            hospsum   = sum(hospindex)

            ageindex  = lenRKI - 1
            threshold = self.RKIdata[ageindex][0]
            while threshold> 1.*age and ageindex>=0:
                ageindex  -= 1
                threshold  = self.RKIdata[ageindex][0]

            prate    = self.RKIdata[ageindex][1]
            nohosp   = 1. - self.ratio - hospsum
            age_list = [self.ratio, self.ratio + nohosp*(1.-prate), self.ratio + nohosp]
            hospdiff = 0.
            for hosp in hospindex:
                hospdiff += hosp
                age_list.append(self.ratio + nohosp + hospdiff)
            self.index_dict[age] = age_list

    def get_index_for_age(self, age):
        return self.index_dict[round(age)]
