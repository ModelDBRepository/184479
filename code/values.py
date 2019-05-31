#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
You can set the values in the simulation of dynamic neural fields of the type:

  ∂     ∂                          ⌠                       |x-y|
(η-- + γ-- + 1) V(x,t) = I(x,t) + ⎮  K(|x-y|) S( V(y, t - -----) ) d²y
  ∂t    ∂t                        ⌡Ω                        c

where # V(x,t) is the potential of a neural population at position x and time t
      # Ω is the domain of integration of size lxl (mm²)
      # c is the velocity of an action potential (mm/s)
      # γ is the first order derivative value
      # η is the second order derivative value
      # I(x,t) is the input at position x and time t
      # K(x) is the synaptic neighborhood function from [0,√2l] -> ℝ
      # S(x) is the firing rate of a single neuron from  ℝ⁺ -> ℝ
      
The integration is made over the finite 2d domain [-l/2,+l/2]x[-l/2,+l/2] discretized 
into n x n elements considered as a toric surface, during a period of t seconds.
'''


'''Which data to show in the graph.'''
# 1 = show V, potential matrix updates
# 2 = show V0, potential matrix at time=0 (does not update V)
# 3 = show I, input matrix
# 4 = show K, kernel matrix
showData = 1


'''Temporal values.''' 
endTime = -1    # simulation duration (a float in seconds or -1:infinity) 
dt      = 0.001 # temporal discretization (delta t in seconds)


'''Derivative values.'''
gamma = 1.0 # γ first order 
eta   = 0.0 # η second order  


'''Axonal transmission speed value.'''
c = 500.0  # mm/s


'''Field space values - applies to length and also width of square field.'''
l = 30.0 # field size 
n = 512  # number of field discretized units


# This sets up the square field, x. Do not change the next 3 lines!!!! **********
import numpy as np
a,b= np.meshgrid(np.arange(-l/2.0,l/2.0,l/float(n)),np.arange(-l/2.0,l/2.0,l/float(n)))
x  = np.sqrt(a**2+b**2)
# Do not change the previous 3 lines! *******************************************


'''This is the field voltage at time=0, V0. 
You can delete/add/change variables but you must initialize a V0 that is a numpy array of size n*n.'''
V0 = np.zeros( (n,n) )  # our V at t=0 that will be used in the simulation


'''Noise applied to the voltage at t>=0, noiseVcont. 
This variable is multiplied by a matrix of random numbers reset every epoc.
The noiseVcont variable can be None (for no continuous noise) or a numpy array of size n*n.''' 
noiseVcont = np.exp(-(a**2/32.0+b**2/32.0))/(np.pi*32.0) * 0.1 * np.sqrt(dt)


'''This is data for the second order calculation, Uexcite. 
You can delete/add/change variables but if eta is not 0.0, 
you must initialize a Uexcite that is a numpy array of size n*n.
If eta (above) == 0.0, then Uexcite can be None, but this is not neccesary.'''
Uexcite = np.zeros((n,n)) # # AXEL: set Uexcite to zero


'''This is the input from external source, I. 
You can delete/add/change variables but you must initialize an I that uses x.'''
Gamma = 20.0       # Γ value
sigma = 5.65685425 # σ value, cannot be 0.0 (division by 0)
# Gaussian value for I of the form I_ + Γ *exp(-x² /σ²) / (π.σ²)
I = Gamma * (np.exp(-1 * x**2 / sigma**2) / (sigma**2 * np.pi)) 


'''This is the synaptic connectivity kernel, K. 
You can delete/add/change variables but you must initialize a K that uses x.'''
K = -4*np.exp(-x/3) / (18*np.pi)


'''This is the firing rate, S. 
You can delete/add/change variables but you must keep the function name S and return the firing rate.'''
def updateS(V): # V is the passed in field voltage
    S0    = 1.0 # S: maximum frequency
    alpha = 10000.0 # α: steepness at the threshold 
    theta = 0.005 # θ: firing threshold
    return S0 / (1.0 + np.exp(-1*alpha*(V-theta)))
