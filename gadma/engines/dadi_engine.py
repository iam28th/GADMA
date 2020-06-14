from . import Engine, register_engine
from .dadi_moments_common import DadiOrMomentsEngine
from ..models import DemographicModel, Epoch, Split
from ..utils import DynamicVariable
from .. import SFSDataHolder


class DadiEngine(DadiOrMomentsEngine):
    """
    Engine for using :py:mod:`dadi` for demographic inference.

    Citation of :py:mod:`dadi`:

    Gutenkunst RN, Hernandez RD, Williamson SH, Bustamante CD (2009)
    Inferring the Joint Demographic History of Multiple Populations
    from Multidimensional SNP Frequency Data. PLoS Genet 5(10): e1000695.
    https://doi.org/10.1371/journal.pgen.1000695
    """

    id = 'dadi'  #:
    import dadi as base_module
    supported_data = [SFSDataHolder]  #:
    inner_data_type = base_module.Spectrum  #:

    @staticmethod
    def _get_kwargs(event, var2value):
        """
        Builds kwargs for dadi.Integration functions (one_pop, two_pops,
        three_pops).

        :param event: build for this event
        :type event: event.Epoch
        :param var2value: dictionary {variable: value}, it is required because
            the dynamics values should be fixed.
        """
        ret_dict = {'T': event.time_arg}
        for i in range(event.n_pop):
            if event.n_pop == 1:
                arg_name = 'nu'
            else:
                arg_name = 'nu%d' % (i+1)

            if event.dyn_args is not None:
                dyn_arg = event.dyn_args[i]
                if var2value.get(dyn_arg, dyn_arg) == 'Sud':
                    ret_dict[arg_name] = event.size_args[i]
                else:
                    ret_dict[arg_name] = 'nu%d_func' % (i+1)
            else:
                ret_dict[arg_name] = event.size_args[i]

        if event.mig_args is not None:
            for i in range(event.n_pop):
                for j in range(event.n_pop):
                    if i == j:
                        continue
                    ret_dict['m%d%d' % (i+1, j+1)] = event.mig_args[i][j]
        if event.sel_args is not None:
            if event.n_pop == 1:
                arg_name = 'gamma'
            else:
                arg_name = 'gamma%d' % (i+1)
            for i in range(event.n_pop):
                ret_dict[arg_name] = event.sel_args[i]
        return ret_dict

    def _dadi_inner_func(self, values, ns, pts):
        """
        Simulates expected SFS for proposed values of variables.

        :param values: values of variables
        :param ns: sample sizes of simulated SFS
        :param pts: grid points for numerical solution
        """
        var2value = self.model.var2value(values)
        dadi = self.base_module

        xx = dadi.Numerics.default_grid(pts)
        phi = dadi.PhiManip.phi_1D(xx)

        addit_values = {}
        for ind, event in enumerate(self.model.events):
            if isinstance(event, Epoch):
                if event.dyn_args is not None:
                    for i in range(event.n_pop):
                        dyn_arg = event.dyn_args[i]
                        value = var2value.get(dyn_arg, dyn_arg)
                        if value != 'Sud':
                            func = DynamicVariable.get_func_from_value(value)
                            y1 = var2value.get(event.init_size_args[i],
                                               event.init_size_args[i])
                            y2 = var2value.get(event.size_args[i],
                                               event.size_args[i])
                            x_diff = var2value.get(event.time_arg,
                                                   event.time_arg)
                            addit_values['nu%d_func' % (i+1)] = func(
                                y1=y1,
                                y2=y2,
                                x_diff=x_diff)
                kwargs_with_vars = self._get_kwargs(event, var2value)
                kwargs = {x: var2value.get(y, y)
                          for x, y in kwargs_with_vars.items()}
                kwargs = {x: addit_values.get(y, y)
                          for x, y in kwargs.items()}
                if event.n_pop == 1:
                    phi = dadi.Integration.one_pop(phi, xx, **kwargs)
                if event.n_pop == 2:
                    phi = dadi.Integration.two_pops(phi, xx, **kwargs)
                if event.n_pop == 3:
                    phi = dadi.Integration.three_pops(phi, xx, **kwargs)
            elif isinstance(event, Split):
                if event.n_pop == 1:
                    phi = dadi.PhiManip.phi_1D_to_2D(xx, phi)
                else:
                    func_name = "phi_%dD_to_%dD_split_%d" % (
                        event.n_pop, event.n_pop + 1, event.pop_to_div + 1)
                    phi = getattr(dadi.PhiManip, func_name)(xx, phi)
        sfs = dadi.Spectrum.from_phi(phi, ns, [xx]*len(ns))
        return sfs

    def simulate(self, values, ns, pts):
        """
        Returns simulated expected SFS for :attr:`demographic_model` with
        values as parameters. Simulation is performed with :attr:`self.pts`
        as grid points for numerical solutions.

        :param values: values of demographic model parameters.
        :param ns: sample sizes of the simulated SFS.
        """
        dadi = self.base_module
        func_ex = dadi.Numerics.make_extrap_log_func(self._dadi_inner_func)
        model = func_ex(values, ns, pts)
        # TODO: Nref
        return model

    def get_theta(self, values, pts):
        return super(DadiEngine, self).get_theta(values, pts)

    def evaluate(self, values, pts):
        return super(DadiEngine, self).evaluate(values, pts)

    def generate_code(self, values, filename, pts):
        return super(DadiEngine, self).generate_code(values, filename, pts)

register_engine(DadiEngine)
