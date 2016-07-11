""" Defines the structural analysis component using spatial beam theory """

from __future__ import division
import numpy

from openmdao.api import Component, Group
from scipy.linalg import lu_factor, lu_solve
import scipy.sparse
import scipy.sparse.linalg
from vlm import view_mat

try:
    import lib
    fortran_flag = True
except:
    fortran_flag = False
sparse_flag = False

def norm(vec):
    return numpy.sqrt(numpy.sum(vec**2))

def unit(vec):
    return vec / norm(vec)

def radii(mesh, t_c=0.15):
    vectors = mesh[-1, :, :] - mesh[0, :, :]
    chords = numpy.sqrt(numpy.sum(vectors**2, axis=1))
    chords = 0.5 * chords[:-1] + 0.5 * chords[1:]
    return t_c * chords

def _assemble_system(aero_ind, fem_ind, nodes, A, J, Iy, Iz, loads,
                     M_a, M_t, M_y, M_z,
                     elem_IDs, cons,
                     E, G, x_gl, T,
                     K_elem, S_a, S_t, S_y, S_z, T_elem,
                     const2, const_y, const_z, n, size, mtx, rhs):

    """
    Assemble the structural stiffness matrix based on 6 degrees of freedom
    per element.

    Can be run in dense Fortran, Sparse Fortran, or dense
    Python code depending on the flags used. Currently, dense Fortran
    seems to be the fastest version across many matrix sizes.

    """

    data_list = []
    rows_list = []
    cols_list = []

    num_surf = fem_ind.shape[0]
    tot_n_fem = numpy.sum(fem_ind[:, 0])
    size = 6 * tot_n_fem + 6 * num_surf

    for i_surf, row in enumerate(fem_ind):
        n_fem, i_fem = row

        num_cons = 1 # just one constraint per structural component
        size_ = 6 * (n_fem + num_cons)
        mtx_ = numpy.zeros((size_, size_), dtype="complex")
        rhs_ = numpy.zeros((size_), dtype="complex")
        A_ = A[i_fem-i_surf:i_fem-i_surf+n_fem-1]
        J_ = J[i_fem-i_surf:i_fem-i_surf+n_fem-1]
        Iy_ = Iy[i_fem-i_surf:i_fem-i_surf+n_fem-1]
        Iz_ = Iz[i_fem-i_surf:i_fem-i_surf+n_fem-1]
        elem_IDs_ = elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, :] - i_fem
        loads_ = loads[i_fem:i_fem+n_fem]

        if fortran_flag and not sparse_flag:
            mtx_ = lib.assemblestructmtx(nodes, A_, J_, Iy_, Iz_,
                                M_a, M_t, M_y, M_z,
                                elem_IDs_+1, cons[i_surf],
                                E, G, x_gl, T,
                                K_elem, S_a, S_t, S_y, S_z, T_elem,
                                const2, const_y, const_z, n_fem, tot_n_fem, size_)
            mtx[(i_fem+i_surf)*6:(i_fem+n_fem+num_cons+i_surf)*6, (i_fem+i_surf)*6:(i_fem+n_fem+num_cons+i_surf)*6] = mtx_

            rhs_[:] = 0.0
            rhs_[:6*n_fem] = loads_.reshape((6*n_fem))
            rhs[6*(i_fem+i_surf):6*(i_fem+n_fem+i_surf+num_cons)] = rhs_

        elif fortran_flag and sparse_flag:
            num_elems = elem_IDs_.shape[0]

            nnz = 144 * num_elems

            data1, rows1, cols1 = lib.assemblesparsemtx(num_elems, tot_n_fem,
                nnz, x_gl, E*numpy.ones(num_elems), G*numpy.ones(num_elems), A_, J_, Iy_, Iz_, nodes, elem_IDs_+1, const2, const_y, const_z, S_a, S_t, S_y, S_z)

            data2 = numpy.ones(6*num_cons)*1.e9
            rows2 = numpy.arange(6*num_cons) + 6*n_fem
            cols2 = numpy.zeros(6*num_cons)
            for ind in xrange(6):
                cols2[ind::6] = 6*cons[i_surf] + ind

            data = numpy.concatenate([data1, data2, data2])
            rows = numpy.concatenate([rows1, rows2, cols2]) + (i_fem+i_surf)*6
            cols = numpy.concatenate([cols1, cols2, rows2]) + (i_fem+i_surf)*6
            data_list.append(data)
            rows_list.append(rows)
            cols_list.append(cols)

            rhs_[:] = 0.0
            rhs_[:6*n_fem] = loads_.reshape((6*n_fem))
            rhs[6*(i_fem+i_surf):6*(i_fem+n_fem+i_surf+num_cons)] = rhs_

        else:
            num_elems = elem_IDs_.shape[0]
            num_nodes = num_elems + 1

            elem_nodes = numpy.zeros((num_elems, 2, 3), dtype='complex')

            E, G = E * numpy.ones(num_elems), G * numpy.ones(num_elems)

            mtx_[:] = 0.
            for ielem in xrange(num_elems):
                P0 = nodes[elem_IDs_[ielem, 0], :]
                P1 = nodes[elem_IDs_[ielem, 1], :]

                x_loc = unit(P1 - P0)
                y_loc = unit(numpy.cross(x_loc, x_gl))
                z_loc = unit(numpy.cross(x_loc, y_loc))

                T[0, :] = x_loc
                T[1, :] = y_loc
                T[2, :] = z_loc

                for ind in xrange(4):
                    T_elem[3*ind:3*ind+3, 3*ind:3*ind+3] = T

                L = norm(P1 - P0)
                EA_L = E[ielem] * A[ielem] / L
                GJ_L = G[ielem] * J[ielem] / L
                EIy_L3 = E[ielem] * Iy[ielem] / L**3
                EIz_L3 = E[ielem] * Iz[ielem] / L**3

                M_a[:, :] = EA_L * const2
                M_t[:, :] = GJ_L * const2

                M_y[:, :] = EIy_L3 * const_y
                M_y[1, :] *= L
                M_y[3, :] *= L
                M_y[:, 1] *= L
                M_y[:, 3] *= L

                M_z[:, :] = EIz_L3 * const_z
                M_z[1, :] *= L
                M_z[3, :] *= L
                M_z[:, 1] *= L
                M_z[:, 3] *= L

                K_elem[:] = 0
                K_elem += S_a.T.dot(M_a).dot(S_a)
                K_elem += S_t.T.dot(M_t).dot(S_t)
                K_elem += S_y.T.dot(M_y).dot(S_y)
                K_elem += S_z.T.dot(M_z).dot(S_z)

                res = T_elem.T.dot(K_elem).dot(T_elem)

                in0, in1 = elem_IDs[ielem, :]

                mtx_[6*in0:6*in0+6, 6*in0:6*in0+6] += res[:6, :6]
                mtx_[6*in1:6*in1+6, 6*in0:6*in0+6] += res[6:, :6]
                mtx_[6*in0:6*in0+6, 6*in1:6*in1+6] += res[:6, 6:]
                mtx_[6*in1:6*in1+6, 6*in1:6*in1+6] += res[6:, 6:]

            for ind in xrange(num_cons):
                for k in xrange(6):
                    mtx_[6*num_nodes + 6*ind + k, 6*cons[i_surf]+k] = 1.e9
                    mtx_[6*cons[i_surf]+k, 6*num_nodes + 6*ind + k] = 1.e9

            rhs_[:] = 0.0
            rhs_[:6*n_fem] = loads_.reshape((6*n_fem))
            rhs[6*(i_fem+i_surf):6*(i_fem+n_fem+i_surf+num_cons)] = rhs_

            mtx[(i_fem+i_surf)*6:(i_fem+n_fem+num_cons+i_surf)*6, (i_fem+i_surf)*6:(i_fem+n_fem+num_cons+i_surf)*6] = mtx_

    if fortran_flag and sparse_flag:
        data = numpy.concatenate(data_list)
        rows = numpy.concatenate(rows_list)
        cols = numpy.concatenate(cols_list)
        mtx = scipy.sparse.csc_matrix((data, (rows, cols)),
                                      shape=(size, size))


    rhs[numpy.abs(rhs) < 1e-6] = 0.
    return mtx, rhs


class SpatialBeamFEM(Component):
    """
    Compute the displacements and rotations by solving the linear system
    using the structural stiffness matrix.

    """

    def __init__(self, aero_ind, fem_ind, E, G, cg_x=5):
        super(SpatialBeamFEM, self).__init__()

        n_fem, i_fem = fem_ind[0, :]
        tot_n = numpy.sum(aero_ind[:, 2])
        num_surf = fem_ind.shape[0]
        self.fem_ind = fem_ind
        self.aero_ind = aero_ind

        num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * num_surf
        self.tot_n_fem = tot_n_fem

        self.size = size = 6 * tot_n_fem + 6 * num_surf
        self.n = n_fem

        self.add_param('A', val=numpy.zeros((tot_n_fem - num_surf)))
        self.add_param('Iy', val=numpy.zeros((tot_n_fem - num_surf)))
        self.add_param('Iz', val=numpy.zeros((tot_n_fem - num_surf)))
        self.add_param('J', val=numpy.zeros((tot_n_fem - num_surf)))
        self.add_param('nodes', val=numpy.zeros((tot_n_fem, 3)))
        self.add_param('loads', val=numpy.zeros((tot_n_fem, 6)))
        self.add_state('disp_aug', val=numpy.zeros((size), dtype="complex"))

        # self.deriv_options['type'] = 'cs'
        # self.deriv_options['form'] = 'central'
        #self.deriv_options['extra_check_partials_form'] = "central"
        self.deriv_options['linearize'] = True # only for circulations

        self.E = E
        self.G = G
        self.cg_x = cg_x

        tot_n_fem = numpy.sum(fem_ind[:, 0])
        self.num_surf = fem_ind.shape[0]
        elem_IDs = numpy.zeros((tot_n_fem-self.num_surf, 2), int)

        for i_surf, row in enumerate(fem_ind):
            nx, ny, n, n_bpts, n_panels, i, i_bpts, i_panels = aero_ind[i_surf, :]
            n_fem, i_fem = row

            arange = numpy.arange(n_fem-1) + i_fem
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 0] = arange
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 1] = arange + 1

            self.elem_IDs = elem_IDs

        self.const2 = numpy.array([
            [1, -1],
            [-1, 1],
        ], dtype='complex')
        self.const_y = numpy.array([
            [12, -6, -12, -6],
            [-6, 4, 6, 2],
            [-12, 6, 12, 6],
            [-6, 2, 6, 4],
        ], dtype='complex')
        self.const_z = numpy.array([
            [12, 6, -12, 6],
            [6, 4, -6, 2],
            [-12, -6, 12, -6],
            [6, 2, -6, 4],
        ], dtype='complex')
        self.x_gl = numpy.array([1, 0, 0], dtype='complex')

        self.K_elem = numpy.zeros((12, 12), dtype='complex')
        self.T_elem = numpy.zeros((12, 12), dtype='complex')
        self.T = numpy.zeros((3, 3), dtype='complex')

        num_nodes = tot_n_fem
        num_cons = self.num_surf
        size = 6*num_nodes + 6*num_cons
        self.mtx = numpy.zeros((size, size), dtype='complex')
        self.rhs = numpy.zeros(size, dtype='complex')

        self.M_a = numpy.zeros((2, 2), dtype='complex')
        self.M_t = numpy.zeros((2, 2), dtype='complex')
        self.M_y = numpy.zeros((4, 4), dtype='complex')
        self.M_z = numpy.zeros((4, 4), dtype='complex')

        self.S_a = numpy.zeros((2, 12), dtype='complex')
        self.S_a[(0, 1), (0, 6)] = 1.

        self.S_t = numpy.zeros((2, 12), dtype='complex')
        self.S_t[(0, 1), (3, 9)] = 1.

        self.S_y = numpy.zeros((4, 12), dtype='complex')
        self.S_y[(0, 1, 2, 3), (2, 4, 8, 10)] = 1.

        self.S_z = numpy.zeros((4, 12), dtype='complex')
        self.S_z[(0, 1, 2, 3), (1, 5, 7, 11)] = 1.


    def solve_nonlinear(self, params, unknowns, resids):
        self.cons = numpy.zeros((self.num_surf))

        for i_surf, row in enumerate(self.fem_ind):
            n_fem, i_fem = row
            nodes = params['nodes'][i_fem:i_fem+n_fem]
            idx = (numpy.linalg.norm(nodes-numpy.array([self.cg_x, 0, 0]), axis=1)).argmin()
            self.cons[i_surf] = idx

        self.mtx, self.rhs = _assemble_system(self.aero_ind, self.fem_ind, params['nodes'], params['A'], params['J'],
                            params['Iy'], params['Iz'], params['loads'],
                            self.M_a, self.M_t, self.M_y, self.M_z,
                            self.elem_IDs, self.cons,
                            self.E, self.G, self.x_gl, self.T,
                            self.K_elem, self.S_a, self.S_t, self.S_y, self.S_z, self.T_elem,
                            self.const2, self.const_y, self.const_z, self.n, self.size, self.mtx, self.rhs)

        if type(self.mtx) == numpy.ndarray:
            unknowns['disp_aug'] = numpy.linalg.solve(self.mtx, self.rhs)
        else:
            self.splu = scipy.sparse.linalg.splu(self.mtx)
            unknowns['disp_aug'] = self.splu.solve(self.rhs)

    def apply_nonlinear(self, params, unknowns, resids):
        nodes = params['nodes']
        self.mtx, self.rhs = _assemble_system(self.aero_ind, self.fem_ind, nodes, params['A'], params['J'],
                            params['Iy'], params['Iz'], params['loads'],
                            self.M_a, self.M_t, self.M_y, self.M_z,
                            self.elem_IDs, self.cons,
                            self.E, self.G, self.x_gl, self.T,
                            self.K_elem, self.S_a, self.S_t, self.S_y, self.S_z, self.T_elem,
                            self.const2, self.const_y, self.const_z, self.n, self.size, self.mtx, self.rhs)

        disp_aug = unknowns['disp_aug']
        resids['disp_aug'] = self.mtx.dot(disp_aug) - self.rhs

    def linearize(self, params, unknowns, resids):
        """ Jacobian for disp."""

        jac = self.alloc_jacobian()
        fd_jac = self.complex_step_jacobian(params, unknowns, resids, \
                                            fd_params=['A','Iy','Iz','J','nodes', 'loads'], \
                                            fd_states=[])
        jac.update(fd_jac)
        jac['disp_aug', 'disp_aug'] = self.mtx.real

        if type(self.mtx) == numpy.ndarray:
            self.lup = lu_factor(self.mtx.real)
        else:
            self.splu = scipy.sparse.linalg.splu(self.mtx)
            self.spluT = scipy.sparse.linalg.splu(self.mtx.transpose())

        return jac

    def solve_linear(self, dumat, drmat, vois, mode=None):

        if mode == 'fwd':
            sol_vec, rhs_vec = self.dumat, self.drmat
            t = 0
        else:
            sol_vec, rhs_vec = self.drmat, self.dumat
            t = 1

        for voi in vois:
            if type(self.mtx) == numpy.ndarray:
                sol_vec[voi].vec[:] = lu_solve(self.lup, rhs_vec[voi].vec, trans=t)
            else:
                if t == 0:
                    sol_vec[voi].vec[:] = self.splu.solve(rhs_vec[voi].vec)
                elif t == 1:
                    sol_vec[voi].vec[:] = self.spluT.solve(rhs_vec[voi].vec)



class SpatialBeamDisp(Component):
    """
    Select displacements from augmented vector.

    The solution to the linear system has additional results due to the
    constraints on the FEM model. The displacements from this portion of
    the linear system is not needed, so we select only the relevant
    portion of the displacements for further calculations.

    """

    def __init__(self, fem_ind):
        super(SpatialBeamDisp, self).__init__()

        self.num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * self.num_surf
        self.tot_n_fem = tot_n_fem
        self.fem_ind = fem_ind

        self.add_param('disp_aug', val=numpy.zeros((size)))
        self.add_output('disp', val=numpy.zeros((tot_n_fem, 6)))
        self.arange = numpy.arange(6*tot_n_fem)

    def solve_nonlinear(self, params, unknowns, resids):
        tot_n_fem = self.tot_n_fem
        num_surf = self.num_surf
        for i_surf, row in enumerate(self.fem_ind):
            n_fem, i_fem = row
            unknowns['disp'][i_fem:i_fem+n_fem] = numpy.array(params['disp_aug'][(i_fem+i_surf)*6:(i_fem+n_fem+i_surf)*6].reshape((n_fem, 6)))

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        fd_jac = self.complex_step_jacobian(params, unknowns, resids, \
                                            fd_params=['disp_aug'], \
                                            fd_states=[])
        jac.update(fd_jac)
        return jac

class ComputeNodes(Component):
    """
    Compute FEM nodes based on aerodynamic mesh.

    The FEM nodes are placed at 0.35*chord, based on the fem_origin value.

    """

    def __init__(self, fem_ind, aero_ind, fem_origin=0.35):
        super(ComputeNodes, self).__init__()

        self.num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        tot_n = numpy.sum(aero_ind[:, 2])
        size = 6 * tot_n_fem + 6 * self.num_surf
        self.tot_n_fem = tot_n_fem
        self.fem_ind = fem_ind
        self.aero_ind = aero_ind
        self.fem_origin = fem_origin

        self.add_param('mesh', val=numpy.zeros((tot_n, 3)))
        self.add_output('nodes', val=numpy.zeros((tot_n_fem, 3)))

    def solve_nonlinear(self, params, unknowns, resids):
        w = self.fem_origin
        for i_surf, row in enumerate(self.fem_ind):
            nx, ny, n, n_bpts, n_panels, i, i_bpts, i_panels = self.aero_ind[i_surf, :]
            n_fem, i_fem = row
            mesh = params['mesh'][i:i+n, :].reshape(nx, ny, 3)
            unknowns['nodes'][i_fem:i_fem+n_fem] = (1-w) * mesh[0, :, :] + w * mesh[-1, :, :]

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        fd_jac = self.complex_step_jacobian(params, unknowns, resids, \
                                            fd_params=['mesh'], \
                                            fd_states=[])
        jac.update(fd_jac)
        return jac



class SpatialBeamEnergy(Component):
    """ Compute strain energy. """

    def __init__(self, aero_ind, fem_ind):
        super(SpatialBeamEnergy, self).__init__()

        num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * num_surf
        self.n = tot_n_fem

        self.add_param('disp', val=numpy.zeros((tot_n_fem, 6)))
        self.add_param('loads', val=numpy.zeros((tot_n_fem, 6)))
        self.add_output('energy', val=0.)

    def solve_nonlinear(self, params, unknowns, resids):
        unknowns['energy'] = numpy.sum(params['disp'] * params['loads'])

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        jac['energy', 'disp'][0, :] = params['loads'].real.flatten()
        jac['energy', 'loads'][0, :] = params['disp'].real.flatten()
        return jac


class SpatialBeamWeight(Component):
    """ Compute total weight. """

    def __init__(self, aero_ind, fem_ind, mrho):
        super(SpatialBeamWeight, self).__init__()

        tot_n = numpy.sum(aero_ind[:, 2])
        num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * num_surf
        self.n = tot_n_fem

        self.fem_ind = fem_ind
        self.aero_ind = aero_ind

        self.add_param('A', val=numpy.zeros((tot_n_fem-num_surf)))
        self.add_param('nodes', val=numpy.zeros((tot_n_fem, 3)))
        self.add_output('weight', val=0.)

        self.deriv_options['type'] = 'cs'
        self.deriv_options['form'] = 'central'

        elem_IDs = numpy.zeros((tot_n_fem-num_surf, 2), int)

        for i_surf, row in enumerate(fem_ind):
            nx, ny, n, n_bpts, n_panels, i, i_bpts, i_panels = aero_ind[i_surf, :]
            n_fem, i_fem = row

            arange = numpy.arange(n_fem-1) + i_fem
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 0] = arange
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 1] = arange + 1

            self.elem_IDs = elem_IDs

        self.mrho = mrho

    def solve_nonlinear(self, params, unknowns, resids):
        nx, ny, n, n_bpts, n_panels, i, i_bpts, i_panels = self.aero_ind[0, :]
        A = params['A']
        nodes = params['nodes']
        num_elems = self.elem_IDs.shape[0]


        volume = 0.
        for ielem in xrange(num_elems):
            in0, in1 = self.elem_IDs[ielem, :]
            P0 = nodes[in0, :]
            P1 = nodes[in1, :]
            L = norm(P1 - P0)
            volume += L * A[ielem]

        unknowns['weight'] = volume  * self.mrho * 9.81

    def linearize(self, params, unknowns, resids):
        jac = self.alloc_jacobian()
        jac['weight', 't'][0, :] = 1.0
        return jac


class SpatialBeamVonMisesTube(Component):
    """ Compute the max von Mises stress in each element. """

    def __init__(self, aero_ind, fem_ind, E, G):
        super(SpatialBeamVonMisesTube, self).__init__()

        tot_n = numpy.sum(aero_ind[:, 2])
        num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * num_surf
        self.tot_n_fem = tot_n_fem

        self.aero_ind = aero_ind
        self.fem_ind = fem_ind

        self.add_param('nodes', val=numpy.zeros((tot_n_fem, 3), dtype="complex"))
        self.add_param('r', val=numpy.zeros((tot_n_fem-num_surf), dtype="complex"))
        self.add_param('disp', val=numpy.zeros((tot_n_fem, 6), dtype="complex"))

        self.add_output('vonmises', val=numpy.zeros((tot_n_fem-num_surf, 2), dtype="complex"))

        self.deriv_options['type'] = 'cs'
        self.deriv_options['form'] = 'central'

        elem_IDs = numpy.zeros((tot_n_fem-num_surf, 2), int)

        for i_surf, row in enumerate(fem_ind):
            nx, ny, n, n_bpts, n_panels, i, i_bpts, i_panels = aero_ind[i_surf, :]
            n_fem, i_fem = row

            arange = numpy.arange(n_fem-1) + i_fem
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 0] = arange
            elem_IDs[i_fem-i_surf:i_fem-i_surf+n_fem-1, 1] = arange + 1

            self.elem_IDs = elem_IDs

        self.T_elem = numpy.zeros((12, 12), dtype='complex')
        self.T = numpy.zeros((3, 3), dtype='complex')
        self.x_gl = numpy.array([1, 0, 0], dtype='complex')

        self.E = E
        self.G = G

    def solve_nonlinear(self, params, unknowns, resids):
        elem_IDs = self.elem_IDs
        r = params['r']
        disp = params['disp']
        nodes = params['nodes']
        vonmises = unknowns['vonmises']

        num_elems = elem_IDs.shape[0]
        for ielem in xrange(num_elems):
            in0, in1 = elem_IDs[ielem, :]

            P0 = nodes[in0, :]
            P1 = nodes[in1, :]
            L = norm(P1 - P0)

            x_loc = unit(P1 - P0)
            y_loc = unit(numpy.cross(x_loc, self.x_gl))
            z_loc = unit(numpy.cross(x_loc, y_loc))

            self.T[0, :] = x_loc
            self.T[1, :] = y_loc
            self.T[2, :] = z_loc

            u0x, u0y, u0z = self.T.dot(disp[in0, :3])
            r0x, r0y, r0z = self.T.dot(disp[in0, 3:])
            u1x, u1y, u1z = self.T.dot(disp[in1, :3])
            r1x, r1y, r1z = self.T.dot(disp[in1, 3:])

            tmp = numpy.sqrt((r1y - r0y)**2 + (r1z - r0z)**2)
            sxx0 = self.E * (u1x - u0x) / L \
                  + self.E * r[ielem] / L * tmp
            sxx1 = self.E * (u0x - u1x) / L \
                  + self.E * r[ielem] / L * tmp
            sxt = self.G * r[ielem] * (r1x - r0x) / L

            vonmises[ielem, 0] = numpy.sqrt(sxx0**2 + sxt**2)
            vonmises[ielem, 1] = numpy.sqrt(sxx1**2 + sxt**2)



class SpatialBeamFailureKS(Component):
    """
    Aggregate failure constraints from the structure.

    To simplify the optimization problem, we aggregate the individual
    elemental failure constraints using a Kreisselmeier-Steinhauser (KS)
    function.

    """

    def __init__(self, fem_ind, sigma, rho=10):
        super(SpatialBeamFailureKS, self).__init__()

        num_surf = fem_ind.shape[0]
        tot_n_fem = numpy.sum(fem_ind[:, 0])
        size = 6 * tot_n_fem + 6 * num_surf
        self.tot_n_fem = tot_n_fem

        self.add_param('vonmises', val=numpy.zeros((tot_n_fem - num_surf, 2)))
        self.add_output('failure', val=0.)

        self.deriv_options['type'] = 'cs'
        self.deriv_options['form'] = 'central'

        self.sigma = sigma
        self.rho = rho

    def solve_nonlinear(self, params, unknowns, resids):
        sigma = self.sigma
        rho = self.rho
        vonmises = params['vonmises']

        fmax = numpy.max(vonmises/sigma - 1)

        nlog, nsum, nexp = numpy.log, numpy.sum, numpy.exp
        unknowns['failure'] = fmax + 1 / rho * \
                              nlog(nsum(nexp(rho * (vonmises/sigma - 1 - fmax))))



class SpatialBeamStates(Group):
    """ Group that contains the spatial beam states. """

    def __init__(self, aero_ind, fem_ind, E, G):
        super(SpatialBeamStates, self).__init__()

        self.add('nodes',
                 ComputeNodes(fem_ind, aero_ind),
                 promotes=['*'])
        self.add('fem',
                 SpatialBeamFEM(aero_ind, fem_ind, E, G),
                 promotes=['*'])
        self.add('disp',
                 SpatialBeamDisp(fem_ind),
                 promotes=['*'])



class SpatialBeamFunctionals(Group):
    """ Group that contains the spatial beam functionals used to evaluate
    performance. """

    def __init__(self, aero_ind, fem_ind, E, G, stress, mrho):
        super(SpatialBeamFunctionals, self).__init__()

        self.add('energy',
                 SpatialBeamEnergy(aero_ind, fem_ind),
                 promotes=['*'])
        self.add('weight',
                 SpatialBeamWeight(aero_ind, fem_ind, mrho),
                 promotes=['*'])
        self.add('vonmises',
                 SpatialBeamVonMisesTube(aero_ind, fem_ind, E, G),
                 promotes=['*'])
        self.add('failure',
                 SpatialBeamFailureKS(fem_ind, stress),
                 promotes=['*'])
