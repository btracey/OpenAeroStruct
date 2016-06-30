""" Defines the aerodynamic analysis component using Weissinger's lifting line theory """

from __future__ import division
import numpy

from openmdao.api import Component, Group
from scipy.linalg import lu_factor, lu_solve
try:
    import lib
    fortran_flag = True
except:
    fortran_flag = False
# fortran_flag = False

def view_mat(mat):
    import matplotlib.pyplot as plt
    if len(mat.shape) > 2:
        mat = numpy.sum(mat, axis=2)
    print "Cond #:", numpy.linalg.cond(mat)
    im = plt.imshow(mat.real, interpolation='none')
    plt.colorbar(im, orientation='horizontal')
    plt.show()

def norm(vec):
    return numpy.sqrt(numpy.sum(vec**2))

def _biot_savart(A, B, P, inf=False, rev=False, eps=1e-5):
    """
    Apply Biot-Savart's law to compute v
    induced at a control point by a vortex line
    - A[3], B[3] : coordinates associated with the vortex line
    - inf : the vortex line is semi-infinite, originating at A
    - rev : signifies the following about the direction of the vortex line:
       If False, points from A to B
       If True,  points from B to A
    - eps : parameter used to avoid singularities when points are on a vortex line
    """

    rPA = norm(A - P)
    rPB = norm(B - P)
    rAB = norm(B - A)
    rH = norm(P - A - numpy.dot((B - A), (P - A)) / \
              numpy.dot((B - A), (B - A)) * (B - A)) + eps
    cosA = numpy.dot((P - A), (B - A)) / (rPA * rAB)
    cosB = numpy.dot((P - B), (A - B)) / (rPB * rAB)
    C = numpy.cross(B - P, A - P)
    C /= norm(C)

    if inf:
        v = -C / rH * (cosA + 1)
    else:
        v = -C / rH * (cosA + cosB)

    if rev:
        v = -v

    return v

def _calc_vorticity(A, B, P):
    r1 = P - A
    r2 = P - B

    r1_mag = norm(r1)
    r2_mag = norm(r2)

    return (r1_mag + r2_mag) * numpy.cross(r1, r2) / \
         (r1_mag * r2_mag * (r1_mag * r2_mag + r1.dot(r2)))


def _assemble_AIC_mtx(mtx, mesh, points, b_pts, alpha, skip=False):
    """
    Compute the aerodynamic influence coefficient matrix
    either for the ation linear system or Trefftz-plane drag computation
    - mtx[num_y-1, num_y-1, 3] : derivative of v w.r.t. circulation
    - mesh[2, num_y, 3] : contains LE and TE coordinates at each section
    - points[num_y-1, 3] : control points
    - b_pts[num_y, 3] : bound vortex coordinates
    """

    num_y = mesh.shape[1]
    num_x = mesh.shape[0]
    mtx[:, :, :] = 0.0
    alpha_conv = alpha * numpy.pi / 180.
    cosa = numpy.cos(alpha_conv)
    sina = numpy.sin(alpha_conv)
    u = numpy.array([cosa, 0, sina])

    if 0: # kink
        if fortran_flag:
            mtx[:, :, :] = lib.assembleaeromtx_kink(num_y, num_x, alpha, mesh, points, b_pts)
            # old_mtx = mtx.copy()
            # mtx[:, :, :] = 0.
        else:
            # Spanwise loop through horseshoe elements
            for el_j in xrange(num_y - 1):

                el_loc_j = el_j * (num_x - 1)

                # Chordwise loop through horseshoe elements
                for el_i in xrange(num_x - 1):

                    el_loc = el_i + el_loc_j

                    A = b_pts[el_i, el_j + 0, :]
                    B = b_pts[el_i, el_j + 1, :]
                    D = mesh[el_i + 1, el_j + 0, :]
                    E = mesh[el_i + 1, el_j + 1, :]
                    F = D + u
                    G = E + u

                    # Spanwise loop through control points
                    for cp_j in xrange(num_y - 1):

                        cp_loc_j = cp_j * (num_x - 1)

                        # Chordwise loop through control points
                        for cp_i in xrange(num_x - 1):

                            cp_loc = cp_i + cp_loc_j

                            P = points[cp_i, cp_j]

                            chk = _biot_savart(A, B, P, inf=False, rev=False)
                            if numpy.isnan(chk).any() or numpy.isinf(chk).any():
                                pass
                            else:
                                mtx[cp_loc, el_loc, :] += chk

                            mtx[cp_loc, el_loc, :] += _biot_savart(B, E, P, inf=False, rev=False)
                            mtx[cp_loc, el_loc, :] += _biot_savart(A, D, P, inf=False, rev=True)
                            mtx[cp_loc, el_loc, :] += _biot_savart(E, G, P, inf=True,  rev=False)
                            mtx[cp_loc, el_loc, :] += _biot_savart(D, F, P, inf=True,  rev=True)

            mtx /=  4 * numpy.pi

    if 0: # paper version (Modern Adaptation of Prandtl's Classic Lifting-Line Theory)
        if fortran_flag:
            mtx[:, :, :] = lib.assembleaeromtx_paper(num_y, num_x, alpha, points, b_pts, skip)
            # old_mtx = mtx.copy()
            # mtx[:, :, :] = 0.
        else:
            # Spanwise loop through horseshoe elements
            for el_j in xrange(num_y - 1):

                el_loc_j = el_j * (num_x - 1)

                # Chordwise loop through horseshoe elements
                for el_i in xrange(num_x - 1):

                    el_loc = el_i + el_loc_j

                    A = b_pts[el_i, el_j + 0, :]
                    B = b_pts[el_i, el_j + 1, :]

                    # Spanwise loop through control points
                    for cp_j in xrange(num_y - 1):

                        cp_loc_j = cp_j * (num_x - 1)

                        # Chordwise loop through control points
                        for cp_i in xrange(num_x - 1):

                            cp_loc = cp_i + cp_loc_j

                            P = points[cp_i, cp_j]

                            r1 = P - A
                            r2 = P - B

                            r1_mag = norm(r1)
                            r2_mag = norm(r2)

                            t1 = numpy.cross(u, r2) / (r2_mag * (r2_mag - u.dot(r2)))
                            t3 = numpy.cross(u, r1) / (r1_mag * (r1_mag - u.dot(r1)))

                            if skip and el_loc == cp_loc:
                                mtx[cp_loc, el_loc, :] = t1 - t3
                            else:
                                t2 = _calc_vorticity(A, B, P)
                                mtx[cp_loc, el_loc, :] = t1 + t2 - t3

            mtx /= 4 * numpy.pi


    if 1: # following planform but still horseshoe version
        if fortran_flag:
            mtx[:, :, :] = lib.assembleaeromtx_hug_planform(num_y, num_x, alpha, points, b_pts, mesh, skip)
            # old_mtx = mtx.copy()
            # mtx[:, :, :] = 0.
        else:
            # Spanwise loop through horseshoe elements
            for el_j in xrange(num_y - 1):
                el_loc_j = el_j * (num_x - 1)
                C_te = mesh[-1, el_j + 1, :]
                D_te = mesh[-1, el_j + 0, :]

                # Spanwise loop through control points
                for cp_j in xrange(num_y - 1):
                    cp_loc_j = cp_j * (num_x - 1)

                    # Chordwise loop through control points
                    for cp_i in xrange(num_x - 1):
                        cp_loc = cp_i + cp_loc_j

                        P = points[cp_i, cp_j]

                        r1 = P - D_te
                        r2 = P - C_te

                        r1_mag = norm(r1)
                        r2_mag = norm(r2)

                        t1 = numpy.cross(u, r2) / (r2_mag * (r2_mag - u.dot(r2)))
                        t3 = numpy.cross(u, r1) / (r1_mag * (r1_mag - u.dot(r1)))

                        trailing = t1 - t3
                        edges = 0

                        # Chordwise loop through horseshoe elements
                        for el_i in reversed(xrange(num_x - 1)):
                            el_loc = el_i + el_loc_j

                            A = b_pts[el_i, el_j + 0, :]
                            B = b_pts[el_i, el_j + 1, :]

                            if el_i == num_x - 2:
                                C = mesh[-1, el_j + 1, :]
                                D = mesh[-1, el_j + 0, :]
                            else:
                                C = b_pts[el_i + 1, el_j + 1, :]
                                D = b_pts[el_i + 1, el_j + 0, :]
                            edges += _calc_vorticity(B, C, P)
                            edges += _calc_vorticity(D, A, P)

                            if skip and el_loc == cp_loc:
                                mtx[cp_loc, el_loc, :] = trailing + edges
                            else:
                                bound = _calc_vorticity(A, B, P)
                                mtx[cp_loc, el_loc, :] = trailing + edges + bound

            mtx /= 4 * numpy.pi


class WeissingerGeometry(Component):
    """ Compute various geometric properties for Weissinger analysis """

    def __init__(self, nx, n):
        super(WeissingerGeometry, self).__init__()

        self.add_param('def_mesh', val=numpy.zeros((nx, n, 3)))
        self.add_output('b_pts', val=numpy.zeros((nx-1, n, 3)))
        self.add_output('c_pts', val=numpy.zeros((nx-1, n-1, 3)))
        self.add_output('widths', val=numpy.zeros((nx-1, n-1)))
        self.add_output('normals', val=numpy.zeros((nx-1, n-1, 3)))
        self.add_output('S_ref', val=0.)
        self.num_y = n
        self.num_x = nx

        self.deriv_options['form'] = 'central'

    def _get_lengths(self, A, B, axis):
        return numpy.sqrt(numpy.sum((B - A)**2, axis=axis))

    def solve_nonlinear(self, params, unknowns, resids):
        mesh = params['def_mesh']

        unknowns['b_pts'] = mesh[:-1, :, :] * .75 + mesh[1:, :, :] * .25

        unknowns['c_pts'] = 0.5 * 0.25 * mesh[:-1, :-1, :] + \
                            0.5 * 0.75 * mesh[1:, :-1, :] + \
                            0.5 * 0.25 * mesh[:-1,  1:, :] + \
                            0.5 * 0.75 * mesh[1:,  1:, :]

        b_pts = unknowns['b_pts']
        unknowns['widths'] = self._get_lengths(b_pts[:, 1:, :], b_pts[:, :-1, :], 2)

        normals = numpy.cross(
            mesh[:-1,  1:, :] - mesh[ 1:, :-1, :],
            mesh[:-1, :-1, :] - mesh[ 1:,  1:, :],
            axis=2)

        norms = numpy.sqrt(numpy.sum(normals**2, axis=2))

        for ind in xrange(3):
            normals[:, :, ind] /= norms

        unknowns['normals'] = normals
        unknowns['S_ref'] = 0.5 * numpy.sum(norms)

    def linearize(self, params, unknowns, resids):
        """ Jacobian for geometry."""

        jac = self.alloc_jacobian()

        n = self.num_y

        fd_jac = self.complex_step_jacobian(params, unknowns, resids,
                                         fd_params=['def_mesh'],
                                         fd_unknowns=['widths', 'normals', 'S_ref'],
                                         fd_states=[])

        jac.update(fd_jac)

        b_pts_size = n*3
        b_pts_eye = numpy.eye(b_pts_size)
        jac['b_pts', 'def_mesh'] = numpy.hstack((.75 * b_pts_eye, .25 * b_pts_eye))

        for i, v in zip((0, 3, n*3, (n+1)*3), (.125, .125, .375, .375)):
            numpy.fill_diagonal(jac['c_pts', 'def_mesh'][:,i:], v)

        return jac


class WeissingerCirculations(Component):
    """ Define circulations """

    def __init__(self, nx, n):
        super(WeissingerCirculations, self).__init__()
        self.add_param('v', val=10.)
        self.add_param('alpha', val=3.)
        self.add_param('def_mesh', val=numpy.zeros((nx, n, 3)))
        self.add_param('normals', val=numpy.zeros((nx-1, n-1, 3)))
        self.add_param('b_pts', val=numpy.zeros((nx-1, n, 3)))
        self.add_param('c_pts', val=numpy.zeros((nx-1, n-1, 3)))
        size = (n-1) * (nx-1)
        self.add_state('circulations', val=numpy.zeros((size)))

        #self.deriv_options['form'] = 'central'
        #self.deriv_options['linearize'] = True # only for circulations

        self.num_y = n
        self.AIC_mtx = numpy.zeros((size, size, 3), dtype="complex")
        self.mtx = numpy.zeros((size, size), dtype="complex")
        self.rhs = numpy.zeros((size), dtype="complex")

    def _assemble_system(self, params):
        _assemble_AIC_mtx(self.AIC_mtx, params['def_mesh'],
                          params['c_pts'], params['b_pts'], params['alpha'])

        self.mtx[:, :] = 0.
        for ind in xrange(3):
            self.mtx[:, :] += (self.AIC_mtx[:, :, ind].T * params['normals'][:, :, ind].flatten('F')).T

        alpha = params['alpha'] * numpy.pi / 180.
        cosa = numpy.cos(alpha)
        sina = numpy.sin(alpha)
        v_inf = params['v'] * numpy.array([cosa, 0., sina], dtype="complex")
        self.rhs[:] = -params['normals'].reshape(-1, params['normals'].shape[-1], order='F').dot(v_inf)

    def solve_nonlinear(self, params, unknowns, resids):
        self._assemble_system(params)
        # obtain incompressible circulations
        unknowns['circulations'] = numpy.linalg.solve(self.mtx, self.rhs)
        resids = self.mtx.dot(unknowns['circulations']) - self.rhs
        #a = 295.4 # hardcoded speed of sound
        #M = params['v'] / a
        #beta = numpy.sqrt(1 - M**2)
        # obtain compressible circulations
        #unknowns['circulations'] /= beta

    def apply_nonlinear(self, params, unknowns, resids):
        self._assemble_system(params)

        circ = unknowns['circulations']
        resids['circulations'] = self.mtx.dot(circ) - self.rhs

    def linearize(self, params, unknowns, resids):
        """ Jacobian for circulations."""

        self.lup = lu_factor(self.mtx.real)
        jac = self.alloc_jacobian()

        fd_jac = self.complex_step_jacobian(params, unknowns, resids,
                                         fd_params=['def_mesh', 'b_pts', 'c_pts',
                                                    'normals', 'alpha'],
                                         fd_states=[])
        jac.update(fd_jac)

        jac['circulations', 'circulations'] = self.mtx.real

        normals = params['normals'].real
        alpha = params['alpha'].real * numpy.pi / 180.
        cosa = numpy.cos(alpha)
        sina = numpy.sin(alpha)

        jac['circulations', 'v'][:, 0] = -self.rhs.real / params['v'].real

        return jac

    def solve_linear(self, dumat, drmat, vois, mode=None):

        if mode == 'fwd':
            sol_vec, rhs_vec = self.dumat, self.drmat
            t = 0
        else:
            sol_vec, rhs_vec = self.drmat, self.dumat
            t = 1

        for voi in vois:
            sol_vec[voi].vec[:] = lu_solve(self.lup, rhs_vec[voi].vec, trans=t)


class WeissingerForces(Component):
    """ Define aerodynamic forces acting on each section """

    def __init__(self, nx, n):
        super(WeissingerForces, self).__init__()
        self.add_param('def_mesh', val=numpy.zeros((nx, n, 3)))
        self.add_param('b_pts', val=numpy.zeros((nx-1, n, 3)))
        size = (nx-1) * (n-1)
        self.add_param('circulations', val=numpy.zeros((size)))
        self.add_param('alpha', val=3.)
        self.add_param('v', val=10.)
        self.add_param('rho', val=3.)
        self.add_output('sec_forces', val=numpy.zeros((nx-1, n-1, 3), dtype="complex"))

        self.mtx = numpy.zeros((size, size, 3), dtype="complex")

        self.num_y = n
        self.num_x = nx
        self.v = numpy.zeros((size, 3), dtype="complex")

    def solve_nonlinear(self, params, unknowns, resids):
        circ = params['circulations']

        alpha = params['alpha'] * numpy.pi / 180.
        cosa = numpy.cos(alpha)
        sina = numpy.sin(alpha)

        mid_b = (params['b_pts'][:, 1:, :] + params['b_pts'][:, :-1, :]) / 2

        _assemble_AIC_mtx(self.mtx, params['def_mesh'],
                          mid_b, params['b_pts'], params['alpha'], skip=True)


        for ind in xrange(3):
            self.v[:, ind] = self.mtx[:, :, ind].dot(circ)
        self.v[:, 0] += cosa * params['v']
        self.v[:, 2] += sina * params['v']

        bound = params['b_pts'][:, 1:, :] - params['b_pts'][:, :-1, :]

        cross = numpy.cross(self.v, bound.reshape(-1, bound.shape[-1], order='F'))

        for ind in xrange(3):
            unknowns['sec_forces'][:, :, ind] = (params['rho'] * circ * cross[:, ind]).reshape(self.num_x-1, self.num_y-1, order='F')

    def linearize(self, params, unknowns, resids):
        """ Jacobian for forces."""

        jac = self.alloc_jacobian()

        n = self.num_y

        fd_jac = self.complex_step_jacobian(params, unknowns, resids,
                                         fd_params=['def_mesh', 'alpha', 'rho',
                                                    'circulations', 'v', 'b_pts'],
                                         fd_states=[])
        jac.update(fd_jac)

        arange = numpy.arange(n-1)
        circ = params['circulations'].real
        rho = params['rho'].real
        v = params['v'].real
        sec_forces = unknowns['sec_forces'].real

        jac['sec_forces', 'rho'] = sec_forces.flatten() / rho

        return jac


class WeissingerLiftDrag(Component):
    """ Calculate total lift and drag in force units based on section forces """

    def __init__(self, nx, n):
        super(WeissingerLiftDrag, self).__init__()

        self.add_param('sec_forces', val=numpy.zeros((nx-1, n-1, 3)))
        self.add_param('alpha', val=3.)
        self.add_output('L', val=0.)
        self.add_output('D', val=0.)

        self.deriv_options['form'] = 'central'
        #self.deriv_options['extra_check_partials_form'] = "central"

        self.num_y = n

    def solve_nonlinear(self, params, unknowns, resids):
        alpha = params['alpha'] * numpy.pi / 180.
        forces = params['sec_forces']

        cosa = numpy.cos(alpha)
        sina = numpy.sin(alpha)
        unknowns['L'] = numpy.sum(-forces[:, :, 0] * sina + forces[:, :, 2] * cosa)
        unknowns['D'] = numpy.sum( forces[:, :, 0] * cosa + forces[:, :, 2] * sina)


    def linearize(self, params, unknowns, resids):
        """ Jacobian for liftdrag."""

        jac = self.alloc_jacobian()

        alpha = params['alpha'] * numpy.pi / 180.
        forces = params['sec_forces']
        cosa = numpy.cos(alpha)
        sina = numpy.sin(alpha)
        n = self.num_y

        tmp = numpy.array([-sina, 0, cosa])
        jac['L', 'sec_forces'] = numpy.atleast_2d(numpy.tile(tmp, n-1))
        tmp = numpy.array([cosa, 0, sina])
        jac['D', 'sec_forces'] = numpy.atleast_2d(numpy.tile(tmp, n-1))

        jac['L', 'alpha'] = numpy.pi / 180. * numpy.sum(-forces[:, :, 0] * cosa - forces[:, :, 2] * sina)
        jac['D', 'alpha'] = numpy.pi / 180. * numpy.sum(-forces[:, :, 0] * sina + forces[:, :, 2] * cosa)

        return jac

class WeissingerCoeffs(Component):
    """ Compute lift and drag coefficients """

    def __init__(self):
        super(WeissingerCoeffs, self).__init__()

        self.add_param('S_ref', val=0.)
        self.add_param('L', val=0.)
        self.add_param('D', val=0.)
        self.add_param('v', val=0.)
        self.add_param('rho', val=0.)
        self.add_output('CL1', val=0.)
        self.add_output('CDi', val=0.)


        self.deriv_options['form'] = 'central'
        #self.deriv_options['extra_check_partials_form'] = "central"

    def solve_nonlinear(self, params, unknowns, resids):
        S_ref = params['S_ref']
        rho = params['rho']
        v = params['v']
        L = params['L']
        D = params['D']
        unknowns['CL1'] = L / (0.5*rho*v**2*S_ref)
        unknowns['CDi'] = D / (0.5*rho*v**2*S_ref)

    def linearize(self, params, unknowns, resids):
        """ Jacobian for forces."""

        S_ref = params['S_ref']
        rho = params['rho']
        v = params['v']
        L = params['L']
        D = params['D']

        jac = self.alloc_jacobian()

        jac['CL1', 'D'] = 0.
        jac['CDi', 'L'] = 0.

        tmp = 0.5*rho*v**2*S_ref
        jac['CL1', 'L'] = 1. / tmp
        jac['CDi', 'D'] = 1. / tmp

        tmp = -0.5*rho**2*v**2*S_ref
        jac['CL1', 'rho'] = L / tmp
        jac['CDi', 'rho'] = D / tmp

        tmp = -0.5*rho*v**2*S_ref**2
        jac['CL1', 'S_ref'] = L / tmp
        jac['CDi', 'S_ref'] = D / tmp

        tmp = -0.25*rho*v**3*S_ref
        jac['CL1', 'v'] = L / tmp
        jac['CDi', 'v'] = D / tmp

        return jac


class TotalLift(Component):
    """ Calculate total lift in force units """

    def __init__(self, CL0):
        super(TotalLift, self).__init__()

        self.add_param('CL1', val=1.)
        self.add_output('CL', val=1.)

        self.deriv_options['form'] = 'central'

        self.CL0 = CL0

    def solve_nonlinear(self, params, unknowns, resids):
        unknowns['CL'] = params['CL1'] + self.CL0

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        jac['CL', 'CL1'] = 1
        return jac

class TotalDrag(Component):
    """ Calculate total drag in force units """

    def __init__(self, CD0):
        super(TotalDrag, self).__init__()

        self.add_param('CDi', val=1.)
        self.add_output('CD', val=1.)

        self.deriv_options['form'] = 'central'

        self.CD0 = CD0

    def solve_nonlinear(self, params, unknowns, resids):
        unknowns['CD'] = params['CDi'] + self.CD0

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        jac['CD', 'CDi'] = 1
        return jac

class WeissingerStates(Group):
    """ Group that contains the aerodynamic states """

    def __init__(self, num_x, num_y):
        super(WeissingerStates, self).__init__()

        self.add('wgeom',
                 WeissingerGeometry(num_x, num_y),
                 promotes=['*'])
        self.add('circ',
                 WeissingerCirculations(num_x, num_y),
                 promotes=['*'])
        self.add('forces',
                 WeissingerForces(num_x, num_y),
                 promotes=['*'])



class WeissingerFunctionals(Group):
    """ Group that contains the aerodynamic functionals used to evaluate performance """

    def __init__(self, nx, num_y, CL0, CD0, num_twist):
        super(WeissingerFunctionals, self).__init__()

        self.add('liftdrag',
                 WeissingerLiftDrag(nx, num_y),
                 promotes=['*'])
        self.add('coeffs',
                 WeissingerCoeffs(),
                 promotes=['*'])
        self.add('CL',
                 TotalLift(CL0),
                 promotes=['*'])
        self.add('CD',
                 TotalDrag(CD0),
                 promotes=['*'])
