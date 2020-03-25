import matplotlib as mpl
import matplotlib.pyplot as plotter
import matplotlib.animation as anim
import numpy
import Person as person


class Canvas:
    def __init__(self,People,Nsteps):
        self.people  = People
        self.dim     = self.people.Dim()
        self.people.SetCanvas(self)
        self.delay   = 1./self.dim**2
        plotter.ion()
        self.showed  = plotter.subplot(2,1,1)
        self.showed.axis([-0.5,N-0.5,-0.5,N-0.5])
        self.summary = plotter.subplot(2,1,2)
        self.summary.axis([1.,Nsteps,0,1])
        self.InitLines()
        self.statuslist = []
        self.Harvest()
        self.showed.matshow(self.statuslist)
        plotter.draw()
        plotter.pause(self.delay)

    def InitLines(self):
        self.xsteps        = numpy.linspace(0,Nsteps,Nsteps)
        self.infected = numpy.zeros(Nsteps)
        self.line1,   = self.summary.plot(self.xsteps,self.infected,'r-')
        self.dead     = numpy.zeros(Nsteps)
        self.line2,   = self.summary.plot(self.xsteps,self.dead,'k-')
        self.immune = numpy.zeros(Nsteps)
        self.line3,   = self.summary.plot(self.xsteps,self.immune,'b-')
        
    def Harvest(self):
        for x in range(self.dim):
            statusrow = []
            for y in range(self.dim):
                statusrow.append(self.people.Get(x,y).Colour())
            self.statuslist.append(statusrow)

    def Update(self,step):
        self.showed.matshow(self.statuslist)
        self.infected[step] = self.people.NInfected()
        self.line1.set_ydata(self.infected)
        self.dead[step] = self.people.NDead()
        self.line2.set_ydata(self.dead)
        self.immune[step] = self.people.NImmune()
        self.line3.set_ydata(self.immune)
        plotter.draw()
        plotter.pause(self.delay)

    def GetList(self):
        return self.statuslist

    def Print(self):
        print (self.statuslist)
    
if __name__ == "__main__":
    N       = 150
    Nsteps  = 100

    people  = person.People(N)
    canvas  = Canvas(people,Nsteps)
    illness = person.Illness(people,canvas)

    people.Seed(illness,3)
    people.Evolution(Nsteps,illness)
    
