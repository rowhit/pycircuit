from pycircuit.circuit import *
import pylab
from pycircuit.circuit.elements import *
from pycircuit.post import plotall
from pycircuit.circuit.transient import Transient

from nose.tools import *
import pycircuit.circuit.circuit 
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal

from myTabVCCS import myVCCS
from myCap import myC

def test_transient_plot():
    vvec=np.linspace(-2,2,100)
    ivec=np.tanh(vvec)
    nvec=ivec*0 # no noise
    c = SubCircuit()
    n1,n2 = c.add_nodes('1', '2')
    c['vsin'] = VSin(n1, gnd, freq=2e3, va=1, vo=1.)
    c['vccs'] = myVCCS(n1, gnd, n2, gnd, ivec=ivec, vvec=vvec, nvec=nvec)
    c['mycap'] = myC(n2, gnd)
    c['rl'] = R(n2, gnd, r=2.0)
    tran = Transient(c)
    res = tran.solve(tend=1e-3, timestep=1e-5)
    plotall(res.v(n1),res.v(n2))
    pylab.show()

def test_nonlinear_gm():
    '''Check gm as a function of bias.

    '''
    pycircuit.circuit.circuit.default_toolkit = numeric
    
    vvec=np.linspace(-2,2,100)
    ivec=vvec**2
    nvec=ivec

    vb=0.1
    iNVCCS=myVCCS(1, 2, 3, 4, vvec=vvec, ivec=ivec, nvec=nvec)
    iVCCS=VCCS(1, 2, 3, 4, gm=2*vb)
    
    G=iNVCCS.G(array([vb,0,0,0]))
    GLin=iVCCS.G(array([vb,0,0,0]))
    assert_array_equal(G,GLin)
    

def test_nonlinear_ac():
    ''' Test that elements are linearised around DC operating point.
    
    '''
    pycircuit.circuit.circuit.default_toolkit = numeric
    cir=SubCircuit()
    
    vvec=np.linspace(-2,2,100)
    ivec=np.exp(vvec/10.)
    nvec=ivec
    
    cir['VB']=VS(1, gnd, v=1, vac=1)
    cir['RL']=R(2, gnd, r=1e2)
    cir['NVCCS']=myVCCS(1, gnd, 2, gnd, vvec=vvec, ivec=ivec, nvec=nvec)
    
    dc = DC(cir)
    resdc = dc.solve()
    
    #I=exp(v/10)
    #gm=1/10*exp(v/10)
    #gm(0)=0.1
    #gm(0.1)=0.1*exp(0.1/10)
    #V(2)=-vac*gm*RL=-gm*RL (-10 for v=0, -10.1 for v=0.1, -11.05 for v=0.5)
    
    res=AC(cir, toolkit = numeric).solve(0)
    assert_almost_equal(res.v(2,gnd),-11.05)

def test_source_degen():
    '''Test myVCCS in a source-degeneration configuration'''
    pycircuit.circuit.circuit.default_toolkit = numeric
    cir=SubCircuit()
    
    vvec=np.linspace(-2,2,100)
    ivec=np.exp(vvec/10.)
    nvec=ivec
    
    cir['VB']=VS(1, gnd, v=1.)
    cir['RL']=R(2, gnd, r=1e2)
    cir['NVCCS']=myVCCS(1, 3, 2, 3, vvec=vvec, ivec=-ivec, nvec=nvec)
    cir['rd'] = R(3,gnd,r=10.) #This doesn't converge
    cir['rd'] = R(3,gnd,r=1.) #This works
    
    dc = DC(cir)
    resdc = dc.solve()
    assert_almost_equal(resdc.v(2,gnd),-110.5)


if __name__ == "__main__":
    test_transient_plot()
