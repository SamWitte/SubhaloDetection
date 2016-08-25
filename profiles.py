# -*- coding: utf-8 -*-
"""
Created on Wed Jul 13 09:54:38 2016

@author: SamWitte
"""
import numpy as np
import os
from subhalo import *
from helper import *
from Limits import *
import scipy.integrate as integrate
import scipy.special as special
from scipy.optimize import fminbound, minimize_scalar, minimize, brentq
from scipy.interpolate import interp1d, interpn

Profile_list = ["Einasto", "NFW", "HW"]

class Subhalo(object):
    """
    Superclass of specific subhalo profiles that calculates the J-factor,
    the spatial extension, and the necessary ingredients to obtain the
    flux threshold for spatially extended sources
    """
    def J(self, dist, theta):
        """
        Calculates J factor.
        :param dist: Distance to subhalo in kpc
        :param theta: Upper bound on anuglar integration (in degrees)
        :return: returns log10 of J factor
        """
        max_theta = radtodeg * np.arctan(self.max_radius / dist)
        if theta > max_theta:
            theta = max_theta
        theta = theta * np.pi / 180.

        #if theta > 0.005 * 180. / np.pi:
        jfact = integrate.dblquad(lambda x, t:
                                  2. * np.pi * kpctocm * np.sin(t) *
                                  self.density(np.sqrt(dist ** 2. + x ** 2. -
                                                       2.0 * dist * x * np.cos(t))
                                               ) ** 2.0,
                                  0., theta, lambda th: self.los_min(th, dist),
                                  lambda th: self.los_max(th, dist), epsabs=10 ** -4,
                                  epsrel=10 ** -4)

        return np.log10(jfact[0])
        #else:
        #    return self.J_pointlike(dist)

    def J_pointlike(self, dist):
        """
        Calculates J factor, assuming its point-like.
        :param dist: Distance to subhalo in kpc
        :return: returns log10 of J factor in GeV^2 /
        """
        jfact = self.int_over_rho_sqr(self.max_radius) / dist**2.
        return np.log10(jfact)

    def los_min(self, theta, dist):
        """
        Calculates lower bound on los integral
        :param theta: Angle from subhalo center in degrees
        :param dist: Distance to subhalo in kpc
        :return: min bound of los integration
        """
        return dist * np.cos(theta) - np.sqrt(dist ** 2. * (np.cos(theta) ** 2. - 1.)
                                              + self.max_radius ** 2.)

    def los_max(self, theta, dist):
        """
        Calculates upper bound on los integral
        :param theta: Angle from subhalo center in degrees
        :param dist: Distance to subhalo in kpc
        :return: max bound of los integration
        """
        return dist * np.cos(theta) + np.sqrt(dist ** 2. * (np.cos(theta) ** 2. - 1.)
                                              + self.max_radius ** 2.)

    def Mass_in_R(self, r):
        """
        Calculates total mass (in SM) contained within some radius r (in kpc)
        :param r: upper limit of radial integration
        :return: Mass enclosed
        """
        return self.int_over_density(r)

    def Mass_diff_005(self, rmax):
        """
        Function used for calculating the truncated radius. Calculates the difference between
        the mass contained in rmax and the 0.5% of the total subhalo mass
        :param rmax: upper bound on radial integration in kpc
        :return: Mass difference
        """
        rmax = 10**rmax
        mass_enc = self.int_over_density(rmax)
        return np.abs(mass_enc - 0.005 * self.halo_mass)

    def Truncated_radius(self):
        """
        Calculates the radius containing 0.5% of the total subhalo mass
        :return: Value of truncated radius in kpc
        """
        r_trunc = fminbound(self.Mass_diff_005, -10., np.log10(self.scale_radius))
        return 10**float(r_trunc)

    def AngRad68(self, theta, dist):
        """
        Function used for calculating the quoted angular extension -- used to
        obtain flux thresholds for spatially extended sources
        :param theta: Max angle of integration in degrees
        :param dist: Subhalo distance in kpc
        :return: We are looking to find the angle theta at which the ratio of
        J(d,t)/J_pointlike(d) = 0.68.
        """
        return np.abs(10. ** self.J(dist, theta) / 10. ** self.J_pointlike(dist) - 0.68)

    def Spatial_Extension(self, dist):
        """
        Function that minimizes AngRad68
        :param dist: Distance of subhalo in kpc
        :return: returns quoted spatial extension to be used for calculation of
        flux threshold of spatially extended sources
        """
        # try:
        #     file_name = 'SpatialExtension_' + str(self.halo_name) + '_Truncate_' + \
        #                 str(self.truncate) + '_Cparam_' + str(self.arxiv_num) + '_alpha_' + \
        #                 str(self.alpha) + '.dat'
        #     se_table = np.loadtxt(MAIN_PATH + '/SubhaloDetection/Data/' + file_name)
        #
        #     pos_index = np.where(np.round(se_table[:, 0], 5) == np.round(self.halo_mass, 5))
        #     pos_index = np.where(np.round(se_table[pos_index][:, 1], 5) == np.round(self.c, 5))
        #     mind = np.min(se_table[pos_index][:, 2])
        #     maxd = np.max(se_table[pos_index][:, 2])
        #     if not mind < dist < maxd:
        #         raise ValueError
        #     exten_interp = interp1d(np.log10(se_table[pos_index][:, 2]), np.log10(se_table[pos_index][:, 3]),
        #                             kind='cubic')
        #     extension = 10.**exten_interp(np.log10(dist))
        # except:
        #     extension = fminbound(self.AngRad68, 0.01, 90., args=[dist], xtol=10**-3.)

        try:
            extension = fminbound(self.AngRad68, 0.01, self.Full_Extension(dist), args=[dist], xtol=10 ** -2.)
            if np.abs(10. ** (self.J(dist, extension) - self.J_pointlike(dist)) - 0.68) < 0.02:
                extension = extension
            else:
                raise ValueError
        except:
            theta_tab = np.logspace(-1.3, np.log10(self.Full_Extension(dist)), 40)
            full_tab = np.logspace(-1.3, np.log10(self.Full_Extension(dist)), 200)
            ang68 = np.zeros(theta_tab.size)
            for i, theta in enumerate(theta_tab):
                ang68[i] = self.AngRad68(theta, dist)
            extension = full_tab[np.argmin(interp1d(theta_tab, ang68, kind='linear', bounds_error=False,
                                                    fill_value=np.inf)(full_tab))]
        return extension

    def Full_Extension(self, dist):
        """
        Calculates the maximum extension (based on max radius)
        of a subhalo at distance = dist
        :param dist: Distance in kpc
        :return: returns extension in degrees
        """
        return radtodeg * np.arctan(self.max_radius / dist)

    def find_tidal_radius(self, r):
        return np.abs(self.halo_mass - self.int_over_density(10. ** r))

    def vel_r_max(self):
        min = minimize_scalar(lambda r: -np.sqrt(self.int_over_density(r) * newton_G / r),
                              bounds=(10**-5., self.max_radius), method='bounded')
        return [-min.fun, min.x]


class Einasto(Subhalo):
    """
    Class sets all of information for subhalos fitted to Einasto profile.


    halo_mass: Subhalo mass (if truncate = True, this mass is pre-tidal stripping mass)

    alpha: Exponent parameter in density profile

    concentration_param: Concentration parameter. If set to None, it uses c(M).

    z: Redshift (currently unused but included because one of concentration
    parameter sources has possible z dependence)

    truncate: If True, analysis follows Hooper et al. If False, subhalo is
    assumed to be fit by Einasto profile after tidal stripping

    arxiv_num: Arxiv number of paper parameterizing the concentration
    parameter -- currently only [10070438, 13131729] implemented

    M200: If False, virial radius is scaled version of Milky Ways virial radius.
    If True, virial radius is taken to be the radius at which the average density
    is equal to 200 times the critical density.
    """
    def __init__(self, halo_mass, alpha=0.16, concentration_param=None,
                 z=0., truncate=False, arxiv_num=10070438, M200=False,
                 gcd=8.5, vmax=None, rmax=None):

        self.pname = 'Einasto_alpha_' + str(alpha) + '_C_params_' + str(arxiv_num) + \
            '_Truncate_' + str(truncate)
        self.halo_mass = halo_mass
        self.alpha = alpha
        self.halo_name = 'Einasto'
        self.truncate = truncate
        self.arxiv_num = arxiv_num

        xmax = fminbound(self.find_xmax, 0., 10.)

        if concentration_param is None:
            concentration_param = Concentration_parameter(halo_mass, z, arxiv_num)
        self.c = concentration_param

        self.virial_radius = Virial_radius(self.halo_mass, m200=M200)

        if arxiv_num == 160106781:
            try:
                self.scale_radius = rmax / xmax
            except TypeError:
                rmax, vmax = rmax_vmax(self.halo_mass)
                self.scale_radius = rmax / xmax

            self.scale_density = (xmax * vmax ** 2. / (4. * np.pi * newton_G * self.scale_radius ** 2. *
                                                    self.func_f(xmax)) * SolarMtoGeV *
                                  cmtokpc ** 3.)
            c_Delta = 2. * (vmax / (H0 * rmax)) ** 2.
            m200 = rmax * vmax ** 2. / newton_G * self.func_f(c_Delta) / self.func_f(xmax)
            self.virial_radius = Virial_radius(m200, m200=True)

        else:
            self.scale_radius = self.virial_radius / self.c
            self.scale_density = ((self.halo_mass * self.alpha * np.exp(-2. / self.alpha) *
                                   (2. / self.alpha) ** (3. / self.alpha)) /
                                  (4. * np.pi * self.scale_radius ** 3. *
                                   special.gamma(3. / self.alpha) *
                                   (1. - special.gammaincc(3. / self.alpha, 2. *
                                                           self.c ** self.alpha / self.alpha))) *
                                  SolarMtoGeV * cmtokpc ** 3.)

        if not self.truncate:
            if arxiv_num == 160106781:
                self.max_radius = self.virial_radius
                #self.max_radius = np.power(10, fminbound(self.find_tidal_radius, -4., 1.3))
            else:
                self.max_radius = self.virial_radius
        else:
            self.max_radius = self.Truncated_radius()

    def density(self, r):
        return self.scale_density * np.exp(-2. / self.alpha * (((r / self.scale_radius) **
                                                                self.alpha) - 1.))

    def int_over_density(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return ((4. * np.pi * np.exp(2. / self.alpha) * self.scale_density *
                    (self.alpha / 2.) ** (3. / self.alpha) * self.scale_radius ** 3. *
                    special.gamma(3. / self.alpha) *
                    (1. - special.gammaincc(3. / self.alpha, 2. / self.alpha *
                                            (r / self.scale_radius) ** self.alpha))) *
                    kpctocm ** 3. * GeVtoSolarM / self.alpha)

    def int_over_rho_sqr(self, r):
        if r > self.max_radius:
            r = self.max_radius
        if r > 0:
            return ((4. * np.pi * np.exp(4. / self.alpha) * self.scale_density ** 2. *
                    self.alpha ** (3. / self.alpha - 1.) * self.scale_radius ** 3. *
                    special.gamma(3. / self.alpha) *
                    (1. - special.gammaincc(3. / self.alpha, 4. / self.alpha *
                                            (r / self.scale_radius) ** self.alpha))) *
                    kpctocm / 4. ** (3. / self.alpha))

    def func_f(self, x):
        return (np.exp(2. / self.alpha) * self.alpha ** (3. / self.alpha - 1.) *
                special.gamma(3. / self.alpha) *
                (1. - special.gammaincc(3. / self.alpha, 2. / self.alpha * x ** self.alpha)) /
                2. ** (3. / self.alpha))

    def find_xmax(self, x):
        return - np.sqrt(self.func_f(x) / x)


def find_alpha(mass, vmax, rmax):
    a_tab = np.linspace(.02, 1.5, 40)
    var_r_tabs = np.zeros(a_tab.size)
    for i, alpha in enumerate(a_tab):
        subhalo = Einasto(1., alpha=alpha, M200=True, arxiv_num=160106781, vmax=vmax, rmax=rmax)
        var_r_tabs[i] = subhalo.int_over_density(subhalo.max_radius) - mass
    try:
        bf_line = brentq(interp1d(a_tab, var_r_tabs, kind='linear'), a_tab[0], a_tab[-1])
    except:
        bf_line = 0.
        print 'Fail'
        raise ValueError
    return bf_line


class NFW(Subhalo):
    """
    Class sets all of information for subhalos fitted to NFW profile.


    halo_mass: Subhalo mass (if truncate = True, this mass is pre-tidal stripping mass)

    alpha: Does not do anything -- I'm keeping it because I have some ideas...

    concentration_param: Concentration parameter. If set to None, it uses c(M).

    z: Redshift (currently unused but included becuase one of concentration
    paramater sources has possible z dependence)

    truncate: If True, analysis follows Hooper et al. If False, subhalo is
    assumed to be fit by Einasto profile after tidal stripping

    arxiv_num: Arxiv number of paper parameterizing the concentration
    parameter -- currently only [10070438, 13131729] implemented

    M200: If False, virial radius is scaled version of Milky Ways virial radius.
    If True, virial radius is taken to be the radius at which the average density
    is equal to 200 times the critical density.
    """
    def __init__(self, halo_mass, alpha, concentration_param=None,
                 z=0., truncate=False, arxiv_num=10070438, M200=False,
                 gcd=8.5, vmax=None, rmax=None):

        self.pname = 'NFW_alpha_' + '_C_params_' + str(arxiv_num) + \
                     '_Truncate_' + str(truncate)
        self.halo_mass = halo_mass
        self.alpha = alpha
        self.halo_name = 'NFW'
        self.truncate = truncate
        self.arxiv_num = arxiv_num

        if arxiv_num == 160106781:
            if concentration_param is None:
                concentration_param = Concentration_parameter(halo_mass, z, arxiv_num)
            self.c = concentration_param
            self.virial_radius = Virial_radius(self.halo_mass, m200=M200)
            try:
                self.scale_radius = rmax / 2.163
            except TypeError:
                rmax, vmax = rmax_vmax(self.halo_mass)
                self.scale_radius = rmax / 2.163

            self.scale_density = (2.163 * vmax ** 2. / (4. * np.pi * newton_G * self.scale_radius ** 2. *
                                                       (np.log(3.163) - 2.163 / 3.163)) * SolarMtoGeV *
                                  cmtokpc ** 3.)

        elif arxiv_num == 160304057:
            self.cv = Concentration_parameter(self.halo_mass, z=0, arxiv_num=160304057, dist=gcd, vmax=vmax)
            try:
                rmax = vmax / H0 * np.sqrt(2. / self.cv)
                self.scale_radius = rmax / 2.163
                self.c = fminbound(self.solve_c200, 0., 150., args=[self.cv])
                m200 = self.func_f(self.c) / self.func_f(2.163) * rmax * vmax ** 2. / newton_G
                self.virial_radius = (3. * m200 / (4. * np.pi * rho_critical * delta_200)) ** (1. / 3.)
                self.scale_density = (2.163 * vmax ** 2. / (4. * np.pi * newton_G * self.scale_radius ** 2. *
                                                            (np.log(3.163) - 2.163 / 3.163)) * SolarMtoGeV *
                                      cmtokpc ** 3.)
            except:
                self.c = self.cv
                m200 = self.halo_mass
                self.virial_radius = (3. * m200 / (4. * np.pi * rho_critical * delta_200)) ** (1. / 3.)
                self.scale_radius = self.virial_radius / self.c
                self.scale_density = ((self.halo_mass * SolarMtoGeV * cmtokpc ** 3.) /
                                      (4. * np.pi * self.scale_radius ** 3. *
                                       (np.log(1.0 + self.c) -
                                        1.0 / (1.0 + 1.0 / self.c))))

        else:
            if concentration_param is None:
                concentration_param = Concentration_parameter(halo_mass, z, arxiv_num, dist=gcd)
            self.c = concentration_param
            self.virial_radius = Virial_radius(self.halo_mass, m200=M200)
            self.scale_radius = self.virial_radius / self.c
            self.scale_density = ((self.halo_mass * SolarMtoGeV * cmtokpc ** 3.) /
                              (4. * np.pi * self.scale_radius ** 3. *
                               (np.log(1.0 + self.c) -
                                1.0 / (1.0 + 1.0 / self.c))))


        if not truncate:
            if arxiv_num == 160106781:
                self.max_radius = np.power(10, fminbound(self.find_tidal_radius, -4., 1.3))
                #self.max_radius = self.scale_radius
            elif arxiv_num == 160304057:
                self.max_radius = np.power(10, fminbound(self.find_tidal_radius, -4., 1.3))
            else:
                self.max_radius = self.virial_radius
        else:
            self.max_radius = self.Truncated_radius()

    def density(self, r):
        try:
            den_array = np.zeros(len(r))
        except TypeError:
            r = np.array([r])
            den_array = np.zeros(len(r))
        valid_args = r > 0.
        den_array[valid_args] = self.scale_density / ((r[valid_args] / self.scale_radius) *
                                                      (1. + r[valid_args] / self.scale_radius) ** 2.)
        return den_array

    def int_over_density(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return (self.scale_density * 4. * np.pi * self.scale_radius ** 3. *
                    (np.log((r + self.scale_radius) / self.scale_radius) - r / (r + self.scale_radius)) *
                    kpctocm ** 3. * GeVtoSolarM)

    def int_over_rho_sqr(self, r):
        if r > self.max_radius:
            r = self.max_radius
        if r > 0:
            return (4. * np.pi * self.scale_density ** 2. * self.scale_radius ** 3. / 3. *
                    (1. - 1. / (1. + r / self.scale_radius) ** 3.) * kpctocm)
        else:
            return 0.

    def func_f(self, x):
        return np.log(1. + x) - x / (1. + x)

    def solve_c200(self, x, cv):
        return np.abs((x / 2.163) ** 3. * self.func_f(2.163) / self.func_f(x) * delta_200 - cv)


class Over_Gen_NFW(Subhalo):

    def __init__(self, halo_mass, r1=1., r2=2., concentration_param=None,
                 z=0., truncate=False, arxiv_num=10070438, M200=True,
                 gcd=8.5, vmax=3., rmax=.4):

        self.pname = 'NFW_alpha_' + '_C_params_' + str(arxiv_num) + \
                     '_Truncate_' + str(truncate)
        self.r1 = r1
        self.r2 = r2

        xmax = fminbound(find_max_gen_prof, 0., 1000., args=[self.r1, self.r2])
        #print 'Rmax / Rscale = ', xmax
        self.scale_radius = rmax / xmax
        self.scale_density = (xmax * vmax ** 2. / (4. * np.pi * newton_G * self.scale_radius ** 2. *
                                                    self.func_f(xmax)) * SolarMtoGeV *
                              cmtokpc ** 3.)
        c_Delta = 2. * (vmax / (H0 * rmax)) ** 2.
        m200 = rmax * vmax ** 2. / newton_G * self.func_f(c_Delta) / self.func_f(xmax)
        self.virial_radius = Virial_radius(m200, m200=True)
        self.max_radius = self.virial_radius

    def density(self, r):
        if r > 0:
            return self.scale_density / ((r / self.scale_radius) ** self.r1 *
                                         (1. + r / self.scale_radius) ** self.r2)
        else:
            return 0.

    def int_over_density(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return (self.scale_density * 4. * np.pi * self.scale_radius ** 3. *
                    self.func_f(r / self.scale_radius)*
                    kpctocm ** 3. * GeVtoSolarM)

    def int_over_rho_sqr(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return (self.scale_density ** 2. * 4. * np.pi * self.scale_radius ** 3. *
                    self.func_f2(r / self.scale_radius) * kpctocm)

    def func_f(self, x):
        return x ** (3. - self.r1) * hyp2f1(3. - self.r1, self.r2, 4. - self.r1, -x) / (3. - self.r1)

    def func_f2(self, x):
        return x ** (3. - 2. * self.r1) * hyp2f1(3. - 2. * self.r1, 2. * self.r2,
                                                 4. - 2. * self.r1, -x) / (3. - 2. *self.r1)


def find_r1_r2(mass, vmax, rmax):
    r1_tab = np.linspace(0.1, 2.5, 40)
    r2_tab = np.linspace(1.5, 50., 120)
    var_r_tabs = np.zeros(r1_tab.size * r2_tab.size).reshape((r1_tab.size, r2_tab.size))
    bf_line = np.zeros(r1_tab.size)

    for i, r1 in enumerate(r1_tab):
        for j, r2 in enumerate(r2_tab):
            #print r1, r2
            subhalo = Over_Gen_NFW(1., r1=r1, r2=r2, M200=True, vmax=vmax, rmax=rmax)
            #print subhalo.int_over_density(subhalo.max_radius), mass, subhalo.int_over_density(subhalo.max_radius) - mass
            var_r_tabs[i, j] = subhalo.int_over_density(subhalo.max_radius) - mass
            #print r1, r2, subhalo.scale_radius
        try:
            bf_line[i] = brentq(interp1d(r2_tab, var_r_tabs[i, :], kind='linear'), r2_tab[0], r2_tab[-1])
        except:
            bf_line[i] = 0.
            break

    keep_ind = ~(bf_line == 0.)
    bf_line = bf_line[keep_ind]
    r1_tab = r1_tab[keep_ind]
    #print 'Halo Mass: ', mass
    #print np.column_stack((r1_tab, bf_line))
    return np.column_stack((r1_tab, bf_line))


class HW_Fit(Subhalo):

    def __init__(self, halo_mass, gam=0.945, M200=True, gcd=8.5, cons=False,
                 stiff_rb=False, optimistic=False):
        self.halo_mass = halo_mass
        self.gam = gam
        self.optimistic = optimistic
        m = self.halo_mass
        if stiff_rb and self.halo_mass < 4. * 10 ** 5.:
            m = 4. * 10 ** 5.
        if cons:
            self.rb = 10. ** (-4.664) * m ** 0.566
        if optimistic:
            self.rb = 10. ** (-4.976) * m ** 0.550
        if not cons and not optimistic:
            self.rb = 10. ** (-4.653) * m ** 0.533

        self.virial_radius = Virial_radius(self.halo_mass, m200=M200)
        self.scale_density = self.halo_mass / (4. * np.pi * self.rb ** (3. - self.gam) *
            special.gamma(3. - self.gam) * (1. - special.gammaincc(3. - self.gam, self.virial_radius / self.rb))
            * kpctocm ** 3. * GeVtoSolarM)
        self.max_radius = self.virial_radius

    def density(self, r):
        try:
            den_array = np.zeros(len(r))
        except TypeError:
            r = np.array([r])
            den_array = np.zeros(len(r))
        valid_args = r > 0.
        den_array[valid_args] = self.scale_density * r[valid_args] ** (-self.gam) * np.exp(- r[valid_args] / self.rb)
        return den_array

    def int_over_density(self, r):
        try:
            den_array = np.zeros(len(r))
        except TypeError:
            r = np.array([r])
            den_array = np.zeros(len(r))
        valid_args = r > 0.
        den_array[valid_args] = self.scale_density * 4. * np.pi * self.rb ** (3. - self.gam) * \
            special.gamma(3. - self.gam) * (1. - special.gammaincc(3. - self.gam, r[valid_args] / self.rb)) \
            * kpctocm ** 3. * GeVtoSolarM
        return den_array

    def int_over_rho_sqr(self, r):
        try:
            int_arr = np.zeros(len(r))
        except TypeError:
            r = np.array([r])
            int_arr = np.zeros(len(r))
        valid_args = r > 0.
        int_arr[valid_args] = self.scale_density ** 2. * 4. * np.pi * 2. ** (2. * self.gam - 3.) * \
            self.rb ** (3. - 2. * self.gam) * special.gamma(3. - 2. * self.gam) * \
            (1. - special.gammaincc(3. - 2. * self.gam, 2. * r[valid_args] / self.rb)) * kpctocm
        return int_arr

class KMMDSM(Subhalo):

    def __init__(self, halo_mass, gam, concentration_param=None,
                 z=0., truncate=False, arxiv_num=10070438, M200=True,
                 gcd=8.5, vmax=3., rmax=.4, from_sim=True):

        self.pname = 'KMMDSM_' + '_C_params_' + str(arxiv_num) + \
                     '_Truncate_' + str(truncate)
        self.gam = gam
        if from_sim:
            xmax = fminbound(find_max_KMMDSM_prof, 0., 100., args=[self.gam])
            self.rb = rmax / xmax
            self.scale_density = (rmax * vmax ** 2. / (4. * np.pi * newton_G *
                                                       self.rb ** (3. - self.gam) *
                                                       special.gamma(3. - self.gam) *
                                                       (1. - special.gammaincc(3. - self.gam, xmax))) *
                                  SolarMtoGeV * cmtokpc ** 3.)
            c_Delta = 2. * (vmax / (H0 * rmax)) ** 2.
            m200 = self.int_over_density(30.)
            self.virial_radius = Virial_radius(m200, m200=True)
            self.max_radius = self.virial_radius


    def density(self, r):
        if r > 0:
            return self.scale_density * r ** (-self.gam) * np.exp(- r / self.rb)
        else:
            return 0.

    def int_over_density(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return (self.scale_density * 4. * np.pi * self.rb ** (3. - self.gam) *
                    special.gamma(3. - self.gam) * (1. - special.gammaincc(3. - self.gam, r / self.rb))
                    * kpctocm ** 3. * GeVtoSolarM)

    def int_over_rho_sqr(self, r):
        try:
            if r > self.max_radius:
                r = self.max_radius
        except AttributeError:
            pass
        if r > 0:
            return (self.scale_density ** 2. * 4. * np.pi * 2. ** (2. * self.gam - 3.) *
                    self.rb ** (3. - 2. * self.gam) * special.gamma(3. - 2. * self.gam) *
                    (1. - special.gammaincc(3. - 2. * self.gam, 2. * r / self.rb)) * kpctocm)


def find_gamma(mass, vmax, rmax, error=0.):
    a_tab = np.linspace(0., 2., 100)
    var_r_tabs = np.zeros(a_tab.size)
    for i, gam in enumerate(a_tab):
        subhalo = KMMDSM(1., gam, M200=True, vmax=vmax, rmax=rmax)
        var_r_tabs[i] = subhalo.int_over_density(subhalo.max_radius) - mass
    #print var_r_tabs
    try:
        bf_line = brentq(interp1d(a_tab, var_r_tabs, kind='linear'), a_tab[0], a_tab[-1])
    except:
        try:
            subhalo = KMMDSM(1., 0., M200=True, vmax=vmax, rmax=rmax)
            check_3sig = subhalo.int_over_density(subhalo.max_radius) - (mass + 3. * error)
            if check_3sig < 0.:
                bf_line = 0.
            else:
                raise ValueError
        except:
            bf_line = 0.
            raise ValueError
    return bf_line
