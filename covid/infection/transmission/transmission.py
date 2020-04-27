from covid.parameters import ParameterInitializer

class Transmission(ParameterInitializer):
    def __init__(self, timer, user_parameters, required_parameters):
        super().__init__("transmission", user_parameters, required_parameters)
        self.timer = timer
        if timer != None:
            self.infection_start_time = self.timer.now
            self.last_time_updated = self.timer.now  # for testing
        self.probability = 0.0

    def update_probability(self):
        pass


class TransmissionConstant(Transmission):
    def __init__(self, timer, user_parameters=None):
        user_parameters = user_parameters or dict()
        required_parameters = ["transmission_probability"]
        super().__init__(timer, user_parameters, required_parameters)

    def update_probability(self):
        time = self.timer.now
        self.last_time_updated = time


class Transmission:
    """
    The probability for an individual to transmit the infection.
    This is time-dependent, and the actual value is calculated in the method
    Probability.  We allow to vary parameters around their mean value with
    a left- and right-sided Gaussian described by sigma and the result
    limited by 2 sigma in either direction or physical limits.

    Currently two forms are implemented:
    - TransmissionSI
    a constant transmission probability, given by the value, with infinite length
    The only parameter is probability
    - TransmissionConstantInterval
    a constant transmission probability, given by the value and the length
    of the transmission period.
    Parameters are probability and end_time
    - TransmissionXNExp
    a probablity of the form $P(t) = P_0 x^n exp(-x/a)$ with parameters given
    by P_0 = probability, n = exponent, and a = norm

    TODO: we should try and map this onto the Flute/Imperial models, as far
    as possible, to have a baseline and to facilitate validation.
    """

    def __init__(self, person, params={}, time=-1.0):
        self.person = person
        self.starttime = time
        self.value = 0.0
        self.init(params)

    def init(self, params):
        pass

    def probability(self, time):
        if time >= self.starttime:
            self.calculate(time)
        else:
            self.value = 0.0
        return max(0.0, self.value)

    def calculate(self, time):
        pass


#################################################################################
#################################################################################
#################################################################################


class TransmissionSI(Transmission):
    def init(self, params):
        self.prob = max(0.0, params["probability"]["value"])

    def calculate(self, time):
        self.value = self.prob


#################################################################################
#################################################################################
#################################################################################


class TransmissionSIR(Transmission):
    def init(self, params):
        self.probT = max(0.0, params["probability"]["value"])
        self.probR = max(0.0, params["recovery"]["value"])
        self.RecoverCutoff = params["recovery_cutoff"]["value"]
        self.lasttime = self.starttime  # last time they had a chance to recover

    def calculate(self, time):
        if (
                self.probT > 0 and time > self.lasttime and
                (
                    ## this is the probabilistic verion of the SIR model where recovery probability
                    ## is given by probR
                    (self.probR > 0 and
                     random.random() > np.exp(-self.probR*(time-self.lasttime))) or
                    ## this is the "fixed-time" version of the SIR model where patients recover
                    ## with certainty after some time
                    (self.probR==0 and
                     time > self.starttime + self.RecoverCutoff)
                ) ):
            self.person.set_susceptibility(0)  # immune
            self.person.set_recovered(True)
        self.lasttime = time  # update last time
        self.value = self.probT


#################################################################################
#################################################################################
#################################################################################


class TransmissionConstantInterval(Transmission):
    def init(self, params):
        self.prob = max(0.0, params["probability"]["value"])
        self.endtime = params["end_time"]["value"]
        self.value = 0

    def calculate(self, time):
        if time <= self.starttime + self.endtime:
            self.value = self.prob
        else:
            self.value = 0.0


#################################################################################
#################################################################################
#################################################################################


class TransmissionLogNormal(Transmission):
    def init(self, params):
        self.prob          = params["probability"]["value"]
        self.mean_time     = params["mean_time"]["value"]
        self.std_variation = params["width_time"]["value"]
        self.end_time      = params["end_time"]["value"]
        self.norm          = 1. #self.prob/(self.std_variation*np.sqrt(2.*np.pi))
        self.mu            = np.log(self.mean_time)
        self.expnorm       = 1./(2.*self.std_variation**2)
        self.value = 0

    def calculate(self, time):
        if (time >= self.starttime and
            time <= self.starttime+self.end_time):
            delta_t = time-self.starttime
            self.value = ((self.norm) *
                          np.exp( -self.expnorm * (np.log(delta_t)-self.mu)**2))
        else:
            self.value = 0.0


#################################################################################
#################################################################################
#################################################################################


class TransmissionXNExp(Transmission):
    def init(self, params):
        self.prob       = max(0.0, params["probability"]["value"])
        self.relaxation = max(0.0001, 1./params["relaxation"]["value"])
        self.mean_time  = max(0.0, params["mean_time"]["value"])
        self.end_time   = max(0.0, params["end_time"]["value"])
        self.init_norm()

    def init_norm(self):
        self.exponent = self.mean_time * self.relaxation
        self.norm = self.mean_time**self.exponent*np.exp(-self.mean_time*self.relaxation)
        self.norm = 1.0 / self.norm
        #print (self.prob,self.relaxation,self.mean_time,"->",self.norm)

    def calculate(self, time):
        dt = time - self.starttime
        self.value = (
            self.norm * self.prob * dt ** self.exponent * np.exp(-dt * self.relaxation)
        )
