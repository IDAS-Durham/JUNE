from covid.inputs import Inputs 
import matplotlib.pyplot as plt

inputs = Inputs()
pop_df = inputs.read_population_df(freq=False)

fig = plt.figure()
plt.hist(
        pop_df['n_residents'], 
        log=True,
        alpha=0.3,
        )
plt.text(2000,1e3, f'Mean {int(pop_df.n_residents.mean())} residents')
plt.text(2000,5e2, f'Median {int(pop_df.n_residents.median())} residents')

plt.xlabel('Number of residents per output area (in the North East)')
plt.ylabel('Bin count')
plt.savefig('../images/residents_output_area.png',
                       dpi=250,
                       bbox_to_anchor='tight'
                )
    


