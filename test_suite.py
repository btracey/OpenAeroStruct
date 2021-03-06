from __future__ import division
import sys
from time import time
import numpy
import unittest

from run_classes import OASProblem

class TestAero(unittest.TestCase):

    def test_aero_analysis_flat(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : False})
        OAS_prob.add_surface({'span_cos_spacing' : 0})
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob

        self.assertAlmostEqual(prob['CL'], .46173591841167, places=5)
        self.assertAlmostEqual(prob['CD'], .005524603647, places=5)

    def test_aero_analysis_flat_multiple(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : False})
        OAS_prob.add_surface({'span_cos_spacing' : 0.})
        OAS_prob.add_surface({'name' : 'tail',
                              'span_cos_spacing' : 0.,
                              'offset' : numpy.array([0., 0., 1000000.])})
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['CL'], .46173591841167, places=5)
        self.assertAlmostEqual(prob['tail_CL'], .46173591841167, places=5)

    def test_aero_analysis_flat_side_by_side(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : False})
        OAS_prob.add_surface({'name' : 'wing',
                              'span' : 5.,
                              'num_y' : 3,
                              'span_cos_spacing' : 0.,
                              'offset' : numpy.array([0., -2.5, 0.])})
        OAS_prob.add_surface({'name' : 'tail',
                              'span' : 5.,
                              'num_y' : 3,
                              'span_cos_spacing' : 0.,
                              'offset' : numpy.array([0., 2.5, 0.])})
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['wing_CL'], .46173591841167, places=5)
        self.assertAlmostEqual(prob['tail_CL'], .46173591841167, places=5)
        self.assertAlmostEqual(prob['wing_CD'], .005524603647, places=5)
        self.assertAlmostEqual(prob['tail_CD'], .005524603647, places=5)

    def test_aero_analysis_flat_symmetry(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : False})
        surf_dict = {'symmetry' : True}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['CL'], .45655138, places=5)

    def test_aero_optimization_flat(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : True})
        OAS_prob.add_surface()
        OAS_prob.setup()

        OAS_prob.add_desvar('twist_cp', lower=-10., upper=15.)
        OAS_prob.add_desvar('sweep', lower=10., upper=30.)
        OAS_prob.add_desvar('dihedral', lower=-10., upper=20.)
        OAS_prob.add_desvar('taper', lower=.5, upper=2.)
        OAS_prob.add_constraint('CL', equals=0.5)
        OAS_prob.add_objective('CD', scaler=1e4)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['CD'], .004048702908627036, places=5)

    def test_aero_multiple_opt(self):
        OAS_prob = OASProblem({'type' : 'aero',
                               'optimize' : True})
        surf_dict = {    'name' : 'wing',
                      'span' : 5.,
                      'num_y' : 3,
                      'span_cos_spacing' : 0.}
        OAS_prob.add_surface(surf_dict)
        surf_dict.update({'name' : 'tail',
                       'offset' : numpy.array([0., 0., 10.])})
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()

        OAS_prob.add_desvar('tail_twist_cp', lower=-10., upper=15.)
        OAS_prob.add_desvar('tail_sweep', lower=10., upper=30.)
        OAS_prob.add_desvar('tail_dihedral', lower=-10., upper=20.)
        OAS_prob.add_desvar('tail_taper', lower=.5, upper=2.)
        OAS_prob.add_constraint('tail_CL', equals=0.5)
        OAS_prob.add_objective('tail_CD', scaler=1e4)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['wing_CL'], .41543435621928004, places=5)
        self.assertAlmostEqual(prob['tail_CL'], .5, places=5)
        self.assertAlmostEqual(prob['wing_CD'], .0075400306289957033, places=5)
        self.assertAlmostEqual(prob['tail_CD'], .00791118243006308, places=5)


class TestStruct(unittest.TestCase):
    def test_struct_analysis(self):
        OAS_prob = OASProblem({'type' : 'struct',
                               'optimize' : False})
        surf_dict = {'symmetry' : False}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['weight'], 83.2113646, places=3)

    def test_struct_analysis_symmetry(self):
        OAS_prob = OASProblem({'type' : 'struct',
                               'optimize' : False})
        surf_dict = {'symmetry' : True}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['weight'], 83.2113646, places=3)

    def test_struct_optimization(self):
        OAS_prob = OASProblem({'type' : 'struct',
                               'optimize' : True})
        OAS_prob.add_surface()
        OAS_prob.setup()

        OAS_prob.add_desvar('thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_constraint('failure', upper=0.)
        OAS_prob.add_objective('weight', scaler=1e-3)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['weight'], 2010.4792274, places=2)

    def test_struct_optimization_symmetry(self):
        OAS_prob = OASProblem({'type' : 'struct',
                               'optimize' : True})
        surf_dict = {'symmetry' : True}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()

        OAS_prob.add_desvar('thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_constraint('failure', upper=0.)
        OAS_prob.add_objective('weight', scaler=1e-3)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['weight'], 1908.6362044761127, places=2)


class TestAeroStruct(unittest.TestCase):

    def test_aerostruct_analysis(self):
        OAS_prob = OASProblem({'type' : 'aerostruct',
                               'optimize' : False})
        surf_dict = {'num_y' : 13,
                  'num_x' : 2,
                  'wing_type' : 'CRM',
                  'CL0' : 0.2,
                  'CD0' : 0.015}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['CL'], .58245256)
        self.assertAlmostEqual(prob['failure'], -.431801158, places=5)
        self.assertAlmostEqual(prob['fuelburn'], 1400891.8033734, places=2)

    def test_aerostruct_analysis_symmetry(self):
        OAS_prob = OASProblem({'type' : 'aerostruct',
                               'optimize' : False})
        surf_dict = {'symmetry' : True,
                  'num_y' : 13,
                  'num_x' : 2,
                  'wing_type' : 'CRM',
                  'CL0' : 0.2,
                  'CD0' : 0.015}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()
        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['CL'], .58245256)
        self.assertAlmostEqual(prob['failure'], -.5011158763, places=5)
        self.assertAlmostEqual(prob['fuelburn'], 1400891.8033734, places=2)

    def test_aerostruct_optimization(self):
        OAS_prob = OASProblem({'type' : 'aerostruct',
                               'optimize' : True})
        surf_dict = {'num_y' : 13,
                  'num_x' : 2,
                  'wing_type' : 'CRM',
                  'CL0' : 0.2,
                  'CD0' : 0.015}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()

        OAS_prob.add_desvar('twist_cp', lower=-15., upper=15.)
        OAS_prob.add_desvar('thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_desvar('alpha', lower=-10., upper=10.)
        OAS_prob.add_constraint('failure', upper=0.)
        OAS_prob.add_constraint('eq_con', equals=0.)
        OAS_prob.add_objective('fuelburn', scaler=1e-5)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['fuelburn'], 922881.03287074505, places=0)
        self.assertAlmostEqual(prob['failure'], 1e-9)

    def test_aerostruct_optimization_symmetry(self):
        OAS_prob = OASProblem({'type' : 'aerostruct',
                               'optimize' : True})
        surf_dict = {'symmetry' : True,
                  'num_y' : 13,
                  'num_x' : 2,
                  'wing_type' : 'CRM',
                  'CL0' : 0.2,
                  'CD0' : 0.015}
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()

        OAS_prob.add_desvar('twist_cp', lower=-15., upper=15.)
        OAS_prob.add_desvar('thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_desvar('alpha', lower=-10., upper=10.)
        OAS_prob.add_constraint('failure', upper=0.)
        OAS_prob.add_constraint('eq_con', equals=0.)
        OAS_prob.add_objective('fuelburn', scaler=1e-5)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['fuelburn'], 854092.32011637127, places=0)
        self.assertAlmostEqual(prob['failure'], 1e-9)

    def test_aerostruct_optimization_symmetry_multiple(self):
        OAS_prob = OASProblem({'type' : 'aerostruct',
                               'optimize' : True})
        surf_dict = {'name' : 'wing',
                     'symmetry' : True,
                     'num_y' : 13,
                     'num_x' : 2,
                     'wing_type' : 'CRM',
                     'CL0' : 0.2,
                     'CD0' : 0.015}
        OAS_prob.add_surface(surf_dict)
        surf_dict.update({'name' : 'tail',
                          'offset':numpy.array([0., 0., 1.e7])})
        OAS_prob.add_surface(surf_dict)
        OAS_prob.setup()

        OAS_prob.add_desvar('wing_twist_cp', lower=-15., upper=15.)
        OAS_prob.add_desvar('wing_thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_constraint('wing_failure', upper=0.)
        OAS_prob.add_desvar('tail_twist_cp', lower=-15., upper=15.)
        OAS_prob.add_desvar('tail_thickness_cp', lower=0.01, upper=0.25, scaler=1e2)
        OAS_prob.add_constraint('tail_failure', upper=0.)

        OAS_prob.add_desvar('alpha', lower=-10., upper=10.)
        OAS_prob.add_constraint('eq_con', equals=0.)
        OAS_prob.add_objective('fuelburn', scaler=1e-5)

        OAS_prob.run()
        prob = OAS_prob.prob
        self.assertAlmostEqual(prob['fuelburn'], 1708184.640125683, places=0)
        self.assertAlmostEqual(prob['wing_failure'], 1e-9)
        self.assertAlmostEqual(numpy.linalg.norm(prob['wing_twist_cp']), numpy.linalg.norm(prob['tail_twist_cp']), places=3)


if __name__ == "__main__":
    print
    print '===================================================='
    print '|             RUNNING FULL TEST SUITE              |'
    print '===================================================='
    print
    unittest.main()
