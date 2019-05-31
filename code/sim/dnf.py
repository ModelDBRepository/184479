#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Dymamic Neural Field simulator with finite transmission speed
# Copyright (C) 2010 Nicolas P. Rougier
# Copyright (C) 2012 - 2015 Eric J. Nichols
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------------
# Contributors:
#
#     Eric Nichols
#     Nicolas P. Rougier
#     Axel Hutt
#     Cyril Noël
#
# Contact Information:
#
#     Axel Hutt / Eric Nichols
#     INRIA Nancy - Grand Est research center
#     CS 20101
#     54603 Villers les Nancy Cedex France
#
# References:
#
#     Axel Hutt and Nicolas P. Rougier
#     "Activity spread and breathers induced by finite transmission
#      speeds in two-dimensional neural fields"
#     Physical Review Letter E, 2010, to appear.
#
# -----------------------------------------------------------------------------

import numpy         as np
from numpy.fft import fft2,ifft2,fftshift,ifftshift
import exceptions
import values as p
a,b,x=p.a,p.b,p.x
import time

class Data():

    def __init__(self):

        self.epoc = 0 # start at the beginning

        # note: casting as floats to ensure avoidance of integer division       
        self.dt             = float(p.dt)        # temporal discretisation (seconds). 
        self.l              = float(p.l)         # size of the field
        self.n              = float(p.n)         # discretized spatial units
        self.gammafactor    = float(p.gamma)     # prefactor of first derivative in second order operator
        self.etafactor      = float(p.eta)       # eta value of second derivative
        try:
            self.c          = float(p.c)         # c, transmission speed
        except:
            self.c          = float(p.axonSpeed) # c, old value
        self.Vexcite        = p.V0               # field voltage at time = 0
        self.noisy          = p.noiseVcont       # noise +- applied to V(t>=0)
        if self.etafactor is not 0.0:
            self.Uexcite = p.Uexcite
        if p.I is None:                          # I, input from external source
            self.I          = 0 
        else:
            self.I          = p.I
        self.K_             = p.K                # K, synaptic connectivity kernel   
        
        # Peel field into several 'onion rings' of width ringWidth. 
        radius      = np.sqrt((self.n/2.0)**2 + (self.n/2.0)**2) # max radius in field: hypotenuse
        self.ringWidth   = max(1.0, self.c*self.dt*self.n/self.l)  # width of a ring in # of grid intervals
        self.nrings = 1 + int(radius/self.ringWidth)             # number of rings
        # Initialisation of past S(V) values (from t=-Tmax to t=0, where Tmax =
        # nrings*dt) Since we're working in the Fourier domain, past values are
        # directly stored using their Fourier transform
        self.U  = [fftshift(fft2(ifftshift(p.updateS(self.Vexcite)))).real,]*self.nrings
        self.finite()                                   # set finite axon speed paradigm
        
        self.synapticfactor = self.l**2/float(self.n**2) # synapse kernel factor
        if p.endTime<0:
            self.simRange = float("inf")
        else:
            self.simRange = int(p.endTime/self.dt) #  duration of simulation
            self.endtime = p.endTime
        
        # Which data to show
        # 0 = show V0 matrix - do not update V
        # 1 = show V matrix after V updates
        # 2 = show input matrix
        # 3 = show kernel matrix
        self.showData = int(p.showData)

        # open our graph window
        from sim import display3D as g3
        self.dim3=g3.graph3D(self.Vexcite, 'DNF simulation', externalUpdate=True, xyText=[0,self.l,0,self.l])
        self.dim3.updateTitle('press p on your keyboard to begin the simulation.') # Set the title of the graph window
        self.dim3.changeMinMax() # show only current min max values
        self.dim3.run = False    # start by pausing the simulation

        # here's our main worker loop conditions
        for to in range(30):
            if self.dim3.windowOpen():
                self.dim3.updateGraph(self.simulate())
        
        # Now test the time it takes for 1 iteration of the simulation
        if self.dim3.windowOpen():
            st = time.time()
            self.dim3.updateGraph(self.simulate())
            en = time.time() 
        
        # We cannot fit 2 iterations per display
        if (en - st) > 0.015: 
            while self.dim3.windowOpen():
                self.dim3.updateGraph(self.simulate())
        
        # Else, we can fit at least 2 per display.
        # Continue the timers because the simulation might slow down 
        # over time and also the user might have paused the simulation
        else:
            while self.dim3.windowOpen():
                st = time.time()
                field = self.simulate()         # simulate field
                if time.time() - st < 0.015:    # time for 1 more
                    field = self.simulate()     # simulate field
                    if time.time() - st < 0.02: # time for 1 more
                        field = self.simulate() # simulate field
                        if time.time() - st < 0.0225:    # time for 1 more
                            field = self.simulate()      # simulate field
                            if time.time() - st < 0.024: # time for 1 more
                                field = self.simulate()  # simulate field
                self.dim3.updateGraph(field)


    def finite(self): # def finite :)
        '''Initialize the finite axon speed paradigm. '''

        def disc(epoc):
            ''' Generate a numpy array containing a disc.

            :Parameters:
                `epoc`: int
                    epoc of discs: Disc radius = epoc*ringWidth
                                (if radius = 0 -> disc is 1 point) 
            '''

            def distance(x,y):
                return np.sqrt((x-self.n//2)**2+(y-self.n//2)**2)
            D=np.fromfunction(distance,(self.n,self.n))
            return np.where(D<(epoc*self.ringWidth),True,False).astype(np.float32)

        # Generate 1+int(d/r) rings
        dsk1 = disc(1)
        L=[dsk1*self.K_] 
        for i in range(1,self.nrings):
            dsk2 = disc(i+1)
            L.append(((dsk2-dsk1)*self.K_)) 
            dsk1 = dsk2

        # Precompute Fourier transform for each kernel ring since they're
        # only used in the Fourier domain
        self.Ki = np.zeros((self.nrings,self.n,self.n)) # self.Ki is our kernel in layers in Fourier space
        for i in range(self.nrings):
            self.Ki[i,:,:]=np.real(fftshift(fft2(ifftshift(L[i]))))


    def simulate(self):
        """Simulate the field and return its potential, V.

        :returns: a 2 dimensional numpy matrix
        :rtype: numpy 2D matrix

        """

        if self.epoc <= self.simRange and self.dim3.run:
            
            # update the iteration
            self.epoc += 1

            # multiply firing rate and synaptic kernel over space and time then transform
            L = self.Ki[0] * self.U[0]
            for j in xrange(1, self.nrings):
                L += self.Ki[j] * self.U[j]
            L = self.synapticfactor*(fftshift(ifft2(ifftshift(L)))).real

            # update V
            self.Vexcite += self.dt/self.gammafactor*(-self.Vexcite+L+self.I) +np.random.normal(0,1.0,(self.n,self.n))*self.noisy

            # update U
            self.U = [fftshift(fft2(ifftshift(p.updateS(self.Vexcite)))),] + self.U[:-1]

            # update the window title
            self.dim3.updateTitle('%.3f seconds     Vmin: %.12f     Vmax: %.12f'%((self.epoc*self.dt),self.Vexcite.min(),self.Vexcite.max()))

        # else if maximum calculation time reached
        elif self.epoc-1 == self.simRange:
            self.dim3.run = False
            print 'Maximum simulation time of', self.endtime, 'seconds has been reached.'
            self.epoc +=1

        return self.Vexcite # return the V matrix
