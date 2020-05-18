import autofit as af

class SymptomsGaussian:

    def __init__(self, mean_time=1.0, sigma_time=3.0, recovery_rate=0.2):

        self.mean_time = max(0.0, mean_time)
        self.sigma_time = max(0.001, sigma_time)
        self.recovery_rate = recovery_rate

class TransmissionConstant:

    def __init__(self, probability=0.3):

        self.probability = probability


model = af.CollectionPriorModel(symptoms=SymptomsGaussian, transmission=TransmissionConstant)

model.symptoms.mean_time = af.UniformPrior(lower_limit=0.0, upper_limit=5.0)
model.symptoms.sigma_time = af.GaussianPrior(mean=3.0, sigma=5.0)
model.symptoms.recovery_rate = af.LogUniformPrior(lower_limit=0.1, upper_limit=100.0)

model.transmission.probability = af.GaussianPrior(mean=0.3, sigma=0.2)

instance = model.random_instance()

print(instance)
print(instance.symptoms)
print(instance.transmission)
print()
print(instance.symptoms.mean_time)
print(instance.symptoms.sigma_time)
print(instance.symptoms.recovery_rate)
print(instance.transmission.probability)

model.add_assertion(model.symptoms.mean_time > 0.0)
model.add_assertion(model.symptoms.sigma_time > 0.0)
model.add_assertion(model.symptoms.recovery_rate > 0.0)
# The last command below gives the following error:
# AttributeError: 'CollectionPriorModel' object has no attribute 'transmission_probability'
#model.add_assertion(1.0 > model.transmission_probability > 0.0)
