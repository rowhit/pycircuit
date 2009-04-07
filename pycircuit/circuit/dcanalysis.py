import logging

from analysis import *

class DC(Analysis):
    """DC analyis class
    
    Linear circuit example:
    >>> c = SubCircuit()
    >>> n1 = c.add_node('net1')
    >>> c['vs'] = VS(n1, gnd, v=1.5)
    >>> c['R'] = R(n1, gnd, r=1e3)
    >>> dc = DC(c)
    >>> res = dc.solve()
    >>> res.v('net1')
    1.5

    Non-linear example:

    >>> c = SubCircuit()
    >>> n1 = c.add_node('net1')
    >>> c['is'] = IS(gnd, n1, i=57e-3)
    >>> c['D'] = Diode(n1, gnd)
    >>> dc = DC(c)
    >>> res = dc.solve()
    >>> print np.around(res.v('net1'), 2)
    0.7

    >>> c = SubCircuit()
    >>> n1 = c.add_node('net1')
    >>> n2 = c.add_node('net2')
    >>> c['is'] = IS(gnd, n1, i=57e-3)
    >>> c['R'] = R(n1, n2, r=1e1)
    >>> c['D'] = Diode(n2, gnd)
    >>> dc = DC(c)
    >>> res = dc.solve()
    >>> dc.result.keys()
    ['gnd', 'net2', 'net1']
    >>> print np.around(res.v('net2'), 2)
    0.7

    """
    parameters = [Parameter(name='reltol', desc='Relative tolerance', unit='', 
                            default=1e-4),
                  Parameter(name='abstol', desc='Absolute tolerance', unit='', 
                            default=1e-12),
                  ]

    def __init__(self, cir, epar = defaultepar, 
                 toolkit=None, refnode=gnd, **kvargs):
        super(DC, self).__init__(cir, epar=epar, toolkit=toolkit, 
                                 **kvargs)
        
        self.irefnode = self.cir.get_node_index(refnode)
        
    def solve(self):
        ## Refer the voltages to the reference node by removing
        ## the rows and columns that corresponds to this node

        convergence_helpers = [self._simple, self._homotopy_gmin, 
                               self._homotopy_source, 
                               None]

        x0 = zeros(self.cir.n) # Would be good with a better initial guess

        for algorithm in convergence_helpers:
            if algorithm == None:
                raise last_e
            else:
                if algorithm.__doc__:
                    logging.info('Trying ' + algorithm.__doc__)
                try:
                    x = algorithm(x0)
                except (NoConvergenceError, SingularMatrix), last_e:
                    pass
                else:
                    break

        self.result = CircuitResultDC(self.cir, x)

        return self.result

    def _simple(self, x0):
        """Simple Newton's method"""
        def func(x):
            return self.cir.i(x) + self.cir.u(0)

        def fprime(x):
            return self.cir.G(x)
        
        return self._newton(func, fprime, x0)

    def _homotopy_gmin(self, x0):
        """Newton's method with gmin stepping"""
        x = x0
        for gmin in (1e-3, 1e-6, 0):
            n_nodes = len(self.cir.nodes)
            Ggmin = zeros((self.cir.n, self.cir.n))
            Ggmin[0:n_nodes, 0:n_nodes] = eye(n_nodes)

            def func(x):
                return self.cir.i(x) + self.cir.u(0)

            def fprime(x):
                return self.cir.G(x) + Ggmin
            
            x, x0 = self._newton(func, fprime, x0), x

        return x

    def _homotopy_source(self, x0):
        """Newton's method with source stepping"""
        x = x0
        for lambda_ in (0, 1e-2, 1e-1, 1):
            def func(x):
                return self.cir.i(x) + lambda_ * self.cir.u(0)

            def fprime(x):
                return self.cir.G(x)
            
            x, x0 = self._newton(func, fprime, x0), x

        return x

    def _newton(self, func, fprime, x0):
        (x0,) = remove_row_col((x0,), self.irefnode)

        try:
            result = fsolve(refnode_removed(func, self.irefnode), 
                            x0, 
                            fprime=refnode_removed(fprime, self.irefnode),
                            full_output=True)
        except np.linalg.LinAlgError, e:
            raise SingularMatrix(e.message)

        x, infodict, ier, mesg = result

        if ier != 1:
            raise NoConvergenceError(mesg)

        # Insert reference node voltage
        return concatenate((x[:self.irefnode], array([0.0]), x[self.irefnode:]))

class CircuitResultDC(CircuitResult):
    def i(self, term):
        """Return terminal current i(term)"""
        return self.circuit.extract_i(self.x, term, xdot = zeros(self.x.shape))

def fsolve(f, x0, fprime=None, args=(), full_output=False, maxiter=200,
           xtol=1e-6, reltol=1e-4, abstol=1e-12):
    """Solve a multidimensional non-linear equation with Newton-Raphson's method

    In each iteration the linear system

    M{J(x_n)(x_{n+1}-x_n) + F(xn) = 0

    is solved and a new value for x is obtained x_{n+1}
    
    """
    
    converged = False
    ier = 2
    for i in xrange(maxiter):
        J = fprime(x0, *args) # TODO: Make sure J is never 0, e.g. by gmin (stepping)
        F = f(x0, *args)
        xdiff = linalg.solve(J, -F)# TODO: Limit xdiff to improve convergence

        x = x0 + xdiff

        if alltrue(abs(xdiff) < reltol * maximum(x, x0) + xtol):
            ier = 1
            mesg = "Success"
            break
        if alltrue(abs(F) < reltol * max(F) + abstol):
            ier = 1
            mesg = "Success"
            break
            
        x0 = x

    if ier == 2:
        mesg = "No convergence. xerror = "+str(xdiff)
    
    infodict = {}
    if full_output:
        return x, infodict, ier, mesg
    else:
        return x
           
def refnode_removed(func, irefnode):
    def new(x, *args, **kvargs):
        newx = concatenate((x[:irefnode], array([0.0]), x[irefnode:]))
        y = func(newx, *args, **kvargs)
        (f,) = remove_row_col((y,), irefnode)
        return f
    return new

if __name__ == "__main__":
    import doctest
    doctest.testmod()