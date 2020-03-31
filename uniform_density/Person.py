import matplotlib.pyplot as plot
import numpy as np
import random
import math

class Person:
    def __init__(self,x,y,people):
        self.prinitit       = 0
        self.x              = x
        self.y              = y
        if (random.random()>people.Susceptibility()):
            self.immune     = 1
            self.status     = 2
        else:
            self.immune     = 0
            self.status     = 0
        self.step           = 0
        self.must_die       = 0
        self.die_step       = 1.e12
        self.heal_step      = -1
        self.people         = people
        if (self.prinitit):
            self.Print()

    def Print(self):
        print ('-----------------------------------------------------')
        print ('--- person at x = ',self.x,', y = ',self.y,' status = ',self.status)
        print ('-----------------------------------------------------')

    def Status(self):
        return self.status

    def IsImmune(self):
        return (self.immune==1)
    
    def IsHealthy(self):
        return (self.status==0)
    
    def IsInfected(self,step):
        return (self.status==1 and step>self.step)

    def IsCured(self,step):
        return (self.status==2 and step>self.step)

    def IsDead(self,step):
        return (self.status==-1)

    def MustDie(self):
        return self.must_die==1

    def DeathStep(self):
        return self.die_step

    def Healing(self):
        return self.heal_step

    def Colour(self):
        if self.status == -1:
            return (0., 0., 0.)
        elif self.status == 0 or self.immune==1:
            return (0., 1.0, 0.4)
        elif self.status == 1:
            return (1., 0., 0.)
        elif self.status == 2:
            return (0., 0., 1.)
        
    def SetStatus(self,status,step):
        if self.status==-1:
            return
        elif self.must_die==1 and status==-1:
            self.people.IncrementDead()
        elif status==1 and self.immune==0:
            self.people.IncrementInfected()
        elif self.must_die!=1 and status==2:
            self.people.IncrementImmune()
        self.status = status
        self.step   = step

    def SetDeath(self,step):
        self.must_die = 1
        self.die_step = step
        
    def SetHealing(self,step):
        self.heal_step = step
        
    def Step(self):
        return self.step
        
    def Update(self,statuslist):
        statuslist[self.x][self.y] = self.Colour()


class People:
    def __init__(self,dim):
        self.people         = []
        self.dim            = dim
        self.healthy        = 0
        self.infected       = 0
        self.immune         = 0
        self.dead           = 0
        self.susceptibility = 0.8
        self.travelprob     = 0.001
        for x in range(self.dim):
            row = []
            for y in range(self.dim):
                person = Person(x,y,self)
                row.append(person)
                if person.IsHealthy():
                    self.healthy += 1
                elif person.IsImmune():
                    self.immune += 1
            self.people.append(row)

    def Get(self,x,y):
        return self.people[x][y]

    def Dim(self):
        return self.dim
    
    def Nmax(self):
        return self.dim**2

    def Susceptibility(self):
        return self.susceptibility

    def IncrementDead(self):
        self.dead     += 1
        self.infected -= 1

    def IncrementImmune(self):
        self.immune   += 1
        self.infected -= 1

    def IncrementInfected(self):
        self.infected += 1
        self.healthy  -= 1

    def NHealthy(self):
        return self.healthy/self.dim**2

    def NInfected(self):
        return self.infected/self.dim**2
    
    def NImmune(self):
        return self.immune/self.dim**2

    def NDead(self):
        return self.dead/self.dim**2

    def SetCanvas(self,canvas):
        self.canvas = canvas

    def Seed(self,illness,N=1):
        if N==1:
            illness.Infect(int(self.dim/2.),int(self.dim/2.),0,0,1.)
        else:
            for i in range(N):
                illness.Infect(random.randint(1,self.dim-1),random.randint(1,self.dim-1),0,0,1.)

    def Evolution(self,Nsteps,illness):
        for step in range(Nsteps):
            self.Step(step,illness)
            self.canvas.Update(step)
            
    def Step(self,step,illness):
        for x in range(self.dim):
            for y in range(self.dim):
                test = self.people[x][y]
                if test.IsHealthy():
                    continue
                if test.IsInfected(step):
                    self.InfectNeighbours(x,y,step,illness)
                    if (self.travelprob>random.random()):
                        illness.Infect(random.randint(1,self.dim-1),random.randint(1,self.dim-1),0,0,step)
                    illness.Evolve(test,step)

    def InfectNeighbours(self,x,y,step,illness):
        dxy = math.ceil(illness.Range())
        for dx in range(-dxy,dxy+1,1):
            for dy in range(-dxy,dxy+1,1):
                if dx==0 and dy==0:
                    continue
                if x+dx>=0 and x+dx<self.dim and y+dy>=0 and y+dy<self.dim:
                    illness.Infect(x,y,dx,dy,step)

    
            

class Illness:
    def __init__(self,people,canvas):
        self.transmission   = 1.
        self.dying          = 0.05
        self.dyingmean      = 17.3
        self.dyingwidth     = 5.
        self.dyingthres     = self.dyingmean-self.dyingwidth
        self.healingmean    = 15.
        self.healingwidth   = 5.
        self.healingthres   = 10.
        self.people         = people
        self.dim            = self.people.Dim()
        self.canvas         = canvas
        self.drange         = 1.
        self.drange2        = self.drange*self.drange

    def Range(self):
        return self.drange
    
    def Evolve(self,patient,step):
        dstep   = step - patient.Step()
        if patient.IsInfected(step) and dstep>0:
            if patient.MustDie():
                if patient.DeathStep()<=step:
                    patient.SetStatus(-1,step)
                    patient.Update(self.canvas.GetList())
            elif patient.Healing()<=step:
                patient.SetStatus(2,step)
                patient.Update(self.canvas.GetList())

    def Infect(self,x,y,dx,dy,step,transmission=-1.):
        dist2 = (dx**2+dy**2)
        if dist2>self.drange2:
            return
        person = self.people.Get(x+dx,y+dy) 
        if person.IsHealthy() and not person.IsImmune():
            if transmission==-1:
                transmission = self.transmission
            if random.random()<transmission*math.exp(-(dist2-1.)/self.drange2):
                if random.random()<self.dying:
                    dstep = -1
                    while dstep<self.dyingthres:
                        dstep = random.gauss(self.dyingmean,self.dyingwidth)
                    person.SetDeath(step + dstep)
                else:
                    hstep = -1
                    while hstep<self.healingthres:
                        hstep = random.gauss(self.healingmean,self.healingwidth)
                    person.SetHealing(step + hstep)     
                person.SetStatus(1,step)
                person.Update(self.canvas.GetList())

        

if __name__ == '__main__':
    x = np.arange(10.,50.,0.1)
    plot.plot(x,np.exp(-(x-17.3)**2/7.**2))
    plot.show()
