# -*- coding: latin-1 -*-
# Copyright (c) 2008 Pycircuit Development Team
# See LICENSE for details.

""" Test circuit module
"""

from nose.tools import *
import pycircuit.circuit.circuit 
from pycircuit.circuit.circuit import *
from pycircuit.circuit.elements import *
from pycircuit.circuit import AC, symbolic


from sympy import var, Symbol, simplify
import sympy
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal
from numpy.testing.decorators import slow
from copy import copy

def generate_testcircuit():
    subc = SubCircuit()
    plus, minus = subc.add_nodes('plus', 'minus')
    subc['R1'] = R(plus, minus, r=2e3)

    subc['R3'] = R(plus, plus)

    class MySubC(SubCircuit):
        terminals = ['p', 'm']

        def __init__(self, *args, **kvargs):
            super(MySubC, self).__init__(*args, **kvargs)
            
            internal = self.add_node('internal')
            
            self['R1'] = R(self.nodenames['p'], internal)
            self['R2'] = R(internal, self.nodenames['m'])
            self['V1'] = VS(internal, gnd)
            self['R3'] = R(internal, gnd)

    subc['I1'] = MySubC(plus, minus)

    return subc

def test_parallel():
    pycircuit.circuit.circuit.default_toolkit = numeric

    cir=SubCircuit()

    res = 1e3
    cir['R1'] = R(1, 2, res)
    cir['R2'] = R(1, 2, res)

    G = cir.G(np.array([0,0]))

    assert_array_equal(G, np.array([[2/res, -2/res],
                                    [-2/res, 2/res]]))

def test_print_element():
    pycircuit.circuit.circuit.default_toolkit = symbolic

    assert_equal(str(C(1, 0, gnd, c=sympy.Symbol('c'))),
                 "C('plus','minus',c=c)")

def test_print_netlist():
    """Test printing of netlist"""
    pycircuit.circuit.circuit.default_toolkit = numeric

    subc = generate_testcircuit()

    netlist = subc.netlist()
    print netlist
    
    refnetlist = \
""".subckt MySubC p m
  V1 internal gnd! VS v=0 vac=1 phase=0 noisePSD=0
  R1 p internal R r=1000.0 noisy=True
  R2 internal m R r=1000.0 noisy=True
  R3 internal gnd! R r=1000.0 noisy=True
.ends
I1 plus minus MySubC 
R1 plus minus R r=2000.0 noisy=True
R3 plus plus R r=1000.0 noisy=True"""

    assert_equal(netlist, refnetlist)    

def test_subcircuit_nodes():
    """Test node consistency of hierarchical circuit"""
    
    subc = generate_testcircuit()

    ## Check nodes of subc
    assert_equal(set(subc.nodes), 
                 set([Node('plus'), Node('minus'), Node('I1.internal'), 
                      gnd]))

    ## Check local names of subc
    assert_equal(subc.nodenames,
                 {'plus': Node('plus'), 'minus': Node('minus'),
                  'I1.internal': Node('I1.internal'),
                  'gnd': gnd})

    ## Check branches of subc
    assert_equal(subc.branches,
                 [Branch(Node('I1.internal'), gnd)])

    ## Check local names of I1
    assert_equal(subc['I1'].nodenames,
                 {'p': Node('p'), 'm': Node('m'),
                  'internal': Node('internal'),
                  'gnd': gnd})

    ## Check branches of I1
    assert_equal(subc['I1'].branches,
                 [Branch(Node('internal'), gnd)])

    ## Check nodes of I1
    assert_equal(set(subc['I1'].nodes), 
                 set([Node('p'), Node('m'), Node('internal'), 
                      gnd]))

    ## Check that first nodes of I1 are terminal nodes 
    assert_equal(subc['I1'].nodes[0:2], [Node('p'), Node('m')])

    ## Check terminal map
    assert_equal(subc.term_node_map['I1'], {'p':Node('plus'), 'm':Node('minus')})

    ## delete I1
    del subc['I1']
    
    ## Check nodes of subc
    assert_equal(set(subc.nodes), 
                 set([Node('plus'), Node('minus')]))

    ## Check local names of subc
    assert_equal(subc.nodenames,
                 {'plus': Node('plus'), 'minus': Node('minus')})
    
    ## Check terminal map
    assert_false('I1' in subc.term_node_map)

    ## Check nodes of R3
    assert_equal(subc['R3'].nodes,
                 [Node('plus'), Node('minus')])

def test_subcircuit_get_instance():
    cir = generate_testcircuit()

    assert_equal(cir[''], cir)
    assert_equal(cir['R1'], R('plus', 'minus', r=2e3))
    assert_equal(cir['I1.R1'], R('plus', 'minus', r=1e3))
    assert_raises(KeyError, lambda: cir['R10'])
    assert_raises(KeyError, lambda: cir['I1.R10'])
    assert_raises(KeyError, lambda: cir['I2.R10'])

def test_subcircuit_add_nodes_implicitly():
    subc = SubCircuit()

    ## Test to add nodes implicitly using node objects
    subc['R1'] = R(Node('a'), Node('b'))
    
    ## Check nodes of subc
    assert_equal(set(subc.nodes), 
                 set([Node('a'), Node('b')]))

    ## Check local names of subc
    assert_equal(subc.nodenames,
                 {'a': Node('a'), 'b': Node('b') })

    ## Test to add nodes implicitly using strings
    subc['R2'] = R('a', 'c')
    subc['R3'] = R('b', 1)
    
    ## Check nodes of subc
    assert_equal(set(subc.nodes), 
                 set([Node('a'), Node('b'), Node('c'), Node('1')]))

    ## Check local names of subc
    assert_equal(subc.nodenames,
                 {'a': Node('a'), 'b': Node('b'), 'c': Node('c'), 
                  '1': Node('1')})
    
def create_current_divider(R1,R3,C2):
    cir = SubCircuit()

    n1,n2 = cir.add_nodes('n1', 'n2')
    
    class MySubC(SubCircuit):
        terminals = ['plus', 'minus']

        def __init__(self, *args, **kvargs):
            super(MySubC, self).__init__(*args, **kvargs)

            self['R3'] = R(self.nodenames['plus'], self.nodenames['minus'], r=R3)
            self['I2'] = IS(self.nodenames['plus'], self.nodenames['minus'], iac=1)


    cir['IS'] = IS(gnd,n1, iac=2)
    cir['R1'] = R(n1, n2, r=R1)
    cir['I1'] = MySubC(n2, gnd)
    cir['C2'] = C(n2, gnd, c=C2)
 
    return cir

def test_current_probing():
    """Test current probing with a current divider circuit"""
    pycircuit.circuit.circuit.default_toolkit = symbolic
    
    s = sympy.Symbol('s')

    R1, R3, C2 = sympy.symbols('R1', 'R3', 'C2')

    cir = create_current_divider(R1,R3,C2)
    
    cir = cir.save_current('I1.plus')
    
    assert cir.get_terminal_branch('I1.plus') != None
    
    res = AC(cir, toolkit=symbolic).solve(s, complexfreq=True)

    assert_equal(sympy.simplify(res.i('I1.plus')), (2 + C2*R3*s)/(1 + C2*R3*s))

    assert_equal(sympy.simplify(res.i('C2.plus')), s*R3*C2 / (1 + s*R3*C2))

            
def test_current_probing_wo_branch():
    """Test current probing with a current divider circuit without current probe"""

    s = sympy.Symbol('s')

    R1, C2, R3 = sympy.symbols('R1', 'C2', 'R3')

    cir = create_current_divider(R1,R3,C2)

    res = AC(cir, toolkit=symbolic).solve(s, complexfreq=True)
    
    assert_equal(sympy.simplify(res.i('I1.plus')), (2 + C2*R3*s)/(1 + C2*R3*s))

    assert_equal(sympy.simplify(res.i('C2.plus')), s*R3*C2 / (1 + s*R3*C2))

def test_adddel_subcircuit_element():
    """add subcircuit element that contains a branch then delete it"""
    cir = SubCircuit()

    n1, = cir.add_nodes('n1')
    
    cir['R1'] = R(n1, gnd, r=1e3)
    
    cir['V'] = VS(n1, gnd)
    
    del cir['V']
    
    assert_equal(cir.elements.values(), [cir['R1']])
    assert_equal(cir.nodes, [n1,gnd])
    assert_equal(cir.branches, [])

def test_short_resistor():
    """Test shorting of instance terminals"""
    cir = SubCircuit()

    cir['R1'] = R(gnd, gnd)
    
    assert_equal(cir.G(np.zeros(1)), np.array([0]))
    
def test_copy_circuit():
    """Test to make a copy of circuit"""

    cir = generate_testcircuit()
    
    cir_copy = copy(cir)

    assert_equal(cir, cir_copy)

def test_VCCS_tied():
    """Test VCCS with some nodes tied together"""
    pycircuit.circuit.circuit.default_toolkit = symbolic

    cir = SubCircuit()

    n3,n2 = cir.add_nodes('3','2')

    gm1 = sympy.Symbol('gm1')

    cir['gm'] = VCCS(gnd, n3, n2, n3, gm = gm1)   
    
    assert_array_equal(cir.G(np.zeros(cir.n)),
                       np.array([[gm1, 0, -gm1],
                                 [-gm1, 0, gm1],
                                 [0, 0, 0]]))

    
def test_proxy():
    pycircuit.circuit.circuit.default_toolkit = symbolic
    
    refcir = generate_testcircuit()
    
    cir = generate_testcircuit()

    print CircuitProxy(cir['I1'], cir, 'I1').terminalhook
    cir['I1'] = CircuitProxy(cir['I1'], cir, 'I1')
    
    assert_equal(cir['I1'].terminals, refcir['I1'].terminals)
    assert_equal(cir['I1'].non_terminal_nodes(), refcir['I1'].non_terminal_nodes())
    assert_equal(cir.nodes, refcir.nodes)
    assert_equal(cir.branches, refcir.branches)
    assert_equal(cir.n, refcir.n)

    for method in ['G', 'C', 'i', 'q']:
        assert_array_equal(getattr(cir, method)(np.zeros(cir.n)),
                           getattr(refcir, method)(np.zeros(cir.n)),
                           )

    assert_array_equal(cir.CY(np.zeros(cir.n),1), refcir.CY(np.zeros(cir.n),1))

def test_parameter_propagation():
    """Test instance parameter value propagation through hierarchy"""
    pycircuit.circuit.circuit.default_toolkit = symbolic

    class A(SubCircuit):
        instparams = [Parameter('x')]

    a = A()

    a['R1'] = R(1,0, r=Parameter('x') + 10)

    a.ipar.x = 20

    assert_equal(a['R1'].ipar.r, 30)
    assert_equal(a['R1'].ipar.noisy, True)

    ## test 2 levels of hierarchy
    a['I1'] = A(x=Parameter('x'))
    a['I1']['R1'] = R(1,0, r=Parameter('x') + 20)
    
    a.ipar.x = 30

    assert_equal(a['R1'].ipar.r, 40)
    assert_equal(a['I1']['R1'].ipar.r, 50)
    
def test_design_variables():
    a = SubCircuit(toolkit=symbolic)
    
    a['R1'] = R(1,0, r=Variable('R')+10, toolkit=symbolic)
    
    ipars = ParameterDict()
    variables = ParameterDict(Variable('R'))

    variables.R = 20

    a.update_ipar(ipars, variables)

    assert_equal(a['R1'].ipar.r, 30)

def test_replace_element():
    """Test node list consitency when replacing an element"""
    c = SubCircuit()
    c['VS'] = VS(1, gnd)
    assert_equal(set(c.nodes), set([Node('1'), gnd]))
    c['VS'] = VS(1, 0)
    assert_equal(set(c.nodes), set([Node('1'), Node('0')]))
    
def test_nullor_vva():
    """Test nullor element by building a V-V amplifier"""
    pycircuit.circuit.circuit.default_toolkit = symbolic

    c = SubCircuit()

    Vin = Symbol('Vin')
    R1 =Symbol('R1')
    R2 = Symbol('R2')
    
    nin = c.add_node('in')
    n1 = c.add_node('n1')
    nout = c.add_node('out')
     
    c['vin'] = VS(nin, gnd, vac=Vin)
    c['R1'] = R(n1, gnd, r=R1)
    c['R2'] = R(nout, n1, r=R2)
    c['nullor'] = Nullor(n1, nin, gnd, nout)
    
    result = AC(c, toolkit=symbolic).solve(Symbol('s'))
    
    vout = result.v(nout)

    assert simplify(vout - Vin * (R1 + R2) / R1) == 0, \
        'Did not get the expected result, %s != 0'% \
        str(simplify(vout - Vin * (R1 + R2) / R1))

def test_SVCVS_laplace_d1():
    """Test VCCS with a laplace defined transfer function, with on denominator coefficient"""
    pycircuit.circuit.circuit.default_toolkit = symbolic

    cir = SubCircuit()

    n1,n2 = cir.add_nodes('1','2')

    a0,a1,Gdc = [sympy.Symbol(symname, real=True) for symname in 'a0,a1,Gdc'.split(',')]

    s = sympy.Symbol('s', complex=True)

    cir['VS']   = VS( n1, gnd, vac=1)
    cir['VCVS'] = SVCVS( n1, gnd, n2, gnd, g = Gdc, denominator = [a0, a1, 0])   

    res = AC(cir, toolkit=symbolic).solve(s, complexfreq=True)

    assert_equal(sympy.simplify(res.v(n2,gnd)),sympy.simplify(Gdc/(a0*s*s+a1*s)))

def test_SVCVS_laplace_n1_d2():
    """Test VCCS with a laplace defined transfer function first order denominator and 
    second order numerator"""

    pycircuit.circuit.circuit.default_toolkit = symbolic
    cir = SubCircuit()
                 

    n1,n2 = cir.add_nodes('1','2')

    b0,a0,a1,Gdc = [sympy.Symbol(symname, real=True) for symname in 'b0,a0,a1,Gdc'.split(',')]

    s = sympy.Symbol('s', complex=True)

    cir['VS']   = VS( n1, gnd, vac=1)
    cir['VCVS'] = SVCVS( n1, gnd, n2, gnd, g = Gdc, denominator = [a0, a1], numerator = [b0])   

    res = AC(cir, toolkit=symbolic).solve(s, complexfreq=True)

    assert_equal(sympy.simplify(res.v(n2,gnd)),(Gdc*b0)/(a0*s+a1))

@slow
def test_SVCVS_laplace_d3_n1_c():
    """Test VCCS with a laplace defined transfer function with first order numerator and third order denominator
    """

    pycircuit.circuit.circuit.default_toolkit = symbolic
    cir = SubCircuit()

    n1,n2 = cir.add_nodes('1','2')

    b0,b1,a0,a1,a2,a3,Gdc = [sympy.Symbol(symname, real=True) for 
                                symname in 'b0,b1,a0,a1,a2,a3,Gdc'
                                .split(',')]

    s = sympy.Symbol('s', complex=True)

    cir['VS']   = VS( n1, gnd, vac=1)
    cir['VCVS'] = SVCVS( n1, gnd, n2, gnd, 
                        g = Gdc, denominator = [a0, a1, a2, a3], 
                        numerator = [b0, b1])

    res = AC(cir, toolkit=symbolic).solve(s, complexfreq=True)

    assert_equal(sympy.simplify(res.v(n2,gnd)),sympy.simplify((-1.0*Gdc*b0*s-1.0*Gdc*b1)/(-a0*s*s*s-a1*s*s-a2*s-a3)))
