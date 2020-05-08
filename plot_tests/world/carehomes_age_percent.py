import matplotlib.pyplot as plt
#from june.world import World

#pie chart taken from https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/articles/changesintheolderresidentcarehomepopulationbetween2001and2011/2014-08-01

def count_percent_within_age(age_bins, world):

    counts = np.zeros(len(age_bins)-1)

    for carehome in world_ne.carehomes.members:
        for person in carehome.people:
            k = np.searchsorted(age_bins, person.age)-1
            counts[k] += 1

    return counts/np.sum(counts)*100.

labels = '65-74', '75-84', '>85'
sizes = [10.5, 30.3, 59.2]

fig1, (ax1,ax2) = plt.subplots(ncols=2)
ax1.set_title('All England carehomes age in Census')
ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.


world = World.from_pickle(pickle_obj  = "../data/world.pkl")
age_bins = [65, 75, 85, 100]
sim_sizes = count_percent_within_age(age_bins, world)


ax2.set_title('North East carehomes age in Simulation')
ax2.pie(sim_sizes, labels=labels, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

plt.show()


age_bins = [20, 40, 65, 75, 85, 100]
sim_sizes = count_percent_within_age(age_bins, world)

print(sim_sizes)


