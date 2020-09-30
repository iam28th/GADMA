import unittest

from .test_data import YRI_CEU_DATA
from gadma import *
import gadma
import gadma
import dadi
import copy
import pickle

DATA_PATH = os.path.join(os.path.dirname(__file__), "test_data")


def rmdir(dirname):
    if not os.path.exists(dirname):
        return
    for filename in os.listdir(dirname):
        path = os.path.join(dirname, filename)
        if os.path.isdir(path):
            rmdir(path)
        else:
            os.remove(path)
    os.rmdir(dirname)


def rosenbrock(X):
    """
    This R^2 -> R^1 function should be compatible with algopy.
    http://en.wikipedia.org/wiki/Rosenbrock_function
    A generalized implementation is available
    as the scipy.optimize.rosen function
    """
    x = X[0]
    y = X[1]
    a = 1. - x
    b = y - x*x
    return a*a + b*b*100.

class TestRestore(unittest.TestCase):
    def test_ga_restore(self):
        ga = get_global_optimizer("Genetic_algorithm")
        f = rosenbrock
        variables = [ContinuousVariable('var1', [-1, 2]),
                     ContinuousVariable('var2', [-2, 3])]
        save_file = "save_file"
        report_file = "report_file"
        res1 = ga.optimize(f, variables, maxiter=5, verbose=1,
                           report_file=report_file,
                           save_file=save_file)

        res2 = ga.optimize(f, variables, maxiter=10, verbose=1,
                           report_file=report_file,
                           restore_file=save_file)

        res3 = ga.optimize(f, variables, maxiter=5, verbose=1,
                           report_file=report_file,
                           restore_file=save_file)

        self.assertEqual(res1.y, res3.y)
        self.assertTrue(res1.y >= res2.y)

    def test_ls_restore(self):
        for opt in all_local_optimizers():
            f = rosenbrock
            # positive domain because we check log scaling optimizations too
            variables = [ContinuousVariable('var1', [10, 20]),
                         ContinuousVariable('var2', [1, 2])]
            x0 = [var.resample() for var in variables]
            save_file = "save_file"
            report_file = "report_file"
            res1 = opt.optimize(f, variables, x0=x0, maxiter=5, verbose=1,
                                report_file=report_file,
                                save_file=save_file)
#            print(res1)
            res2 = opt.optimize(f, variables, x0=x0, maxiter=5, verbose=1,
                                report_file=report_file,
                                restore_file=save_file,
                                restore_models_only=True)
#            print(res2)
            res3 = opt.optimize(f, variables, x0=x0, maxiter=5, verbose=1,
                                report_file=report_file,
                                restore_file=save_file)
#            print(res3)
            res4 = opt.optimize(f, variables, x0=x0, maxiter=10, verbose=1,
                                report_file=report_file,
                                restore_file=save_file,
                                restore_models_only=True)
#            print(res4)
            self.assertEqual(res1.y, res3.y)
            self.assertTrue(res1.y >= res2.y)
            self.assertTrue(res2.y >= res4.y)
            for res in [res1, res2, res3, res4]:
                self.assertEqual(res.y, f(res.x))

    def test_gs_and_ls_restore(self):
        param_file = os.path.join(DATA_PATH, 'another_test_params')
        base_out_dir = "test_gs_and_ls_restore_output"
        sys.argv = ['gadma', '-p', param_file, '-o', base_out_dir]
        settings, _ = get_settings()
        settings.linked_snp_s = False
        out_dir = 'some_not_existed_dir'
        shared_dict = gadma.shared_dict.SharedDictForCoreRun(multiprocessing=False)
        if os.path.exists(out_dir):
            rmdir(out_dir)
        for ls_opt in all_local_optimizers():
            if os.path.exists(settings.output_directory):
                rmdir(settings.output_directory)
            if os.path.exists(out_dir):
                rmdir(out_dir)
            settings.local_optimizer = ls_opt.id
            core_run = CoreRun(0, shared_dict, settings)
            res1 = core_run.run()

#            print(res1)
            restore_settings = copy.copy(settings)
            restore_settings.output_directory = out_dir
            restore_settings.resume_from = settings.output_directory

            restore_core_run = CoreRun(0, shared_dict, restore_settings)
            res2 = restore_core_run.run()
#            print(res2)

            self.assertEqual(res1.y, res2.y)
            if os.path.exists(out_dir):
                rmdir(out_dir)

            restore_settings.only_models = True
            restore_core_run = CoreRun(0, shared_dict, restore_settings)
            res3 = restore_core_run.run()
#            print(res3)

            self.assertTrue(res3.y >= res2.y)
        if os.path.exists(settings.output_directory):
            rmdir(settings.output_directory)