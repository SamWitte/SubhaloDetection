# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 09:58:38 2016

@author: SamWitte
"""
import numpy as np
import os
from subhalo import *
from helper import *
from profiles import *


def table_spatial_extension(profile=0, truncate=False, arxiv_num=10070438,
                            M200=False, d_low=-3., d_high=1., d_num=30, m_num=20,
                            c_num=20, m_low=10.**5., m_high=10**7.):
    """ Tables spatial extension for future use.

        Profile Numbers correspond to [Einasto, NFW, HW] # 0 - 2
    """

    alpha = 0.16
    file_name = 'SpatialExtension_' + str(Profile_list[profile]) + '2.dat'

    dir = MAIN_PATH + '/SubhaloDetection/Data/'
    open(dir + file_name, "a")
    if truncate:
        mass_list = np.logspace(np.log10(m_low / 0.005), np.log10(m_high / 0.005),
                                (np.log10(m_high) - np.log10(m_low)) * 6)
    else:
        mass_list = np.logspace(np.log10(m_low), np.log10(m_high),  (np.log10(m_high) - np.log10(m_low)) * 6)
    dist_list = np.logspace(d_low, d_high, d_num)

    for m in mass_list:
        print 'Subhalo mass: ', m
        if profile == 0:
            c_list = np.logspace(np.log10(2.5), 2.4, c_num)
            for c in c_list:
                print '     Concentration parameter: ', c
                subhalo = Einasto(m, alpha, c, truncate=True,
                                  arxiv_num=13131729, M200=False)
                for ind, d in enumerate(dist_list):
                    print '         Distance', d
                    value = '{:.3e}     {:.3e}      {:.3e}'.format(m, c, d)
                    try:
                        f = np.loadtxt(dir + file_name)
                        m_check = float('{:.3e}'.format(m))
                        c_check = float('{:.3e}'.format(c))
                        d_check = float('{:.3e}'.format(d))
                        if np.sum((f[:, 0] == m_check) & (f[:, 1] == c_check) &
                                          (f[:, 3] == d_check)) < 1:
                            raise ValueError
                    except:
                        if subhalo.Full_Extension(d) > 0.1:
                            ext = subhalo.Spatial_Extension(d)
                            print '             Extension: ', ext
                            value += '      {:.3e} \n'.format(float(ext))
                            ff = open(dir + file_name, 'a+')
                            ff.write(value)
                            ff.close()
        elif profile == 1:
            subhalo = NFW(m, 1., truncate=False,
                          arxiv_num=160106781, M200=True)
            for ind, d in enumerate(dist_list):
                print '         Distance', d
                value = '{:.3e}     {:.3e}'.format(m, d)
                try:
                    f = np.loadtxt(dir + file_name)
                    m_check = float('{:.3e}'.format(m))
                    d_check = float('{:.3e}'.format(d))
                    if np.sum((f[:, 0] == m_check) & (f[:, 3] == d_check)) < 1:
                        raise ValueError
                except:
                    if subhalo.Full_Extension(d) > 0.1:
                        ext = subhalo.Spatial_Extension(d)
                        print '             Extension: ', ext
                        value += '      {:.3e} \n'.format(float(ext))
                        ff = open(dir + file_name, 'a+')
                        ff.write(value)
                        ff.close()
        else:
            rb_med = np.log10(10. ** (-4.24) * m ** 0.459)
            rb_low = rb_med - 1.
            rb_high = rb_med + 1.
            rb_list = np.logspace(rb_low, rb_high, 8)
            gamma_list = np.linspace(0., 1.45, 8)
            for rb in rb_list:
                print '     Rb: ', rb
                for gam in gamma_list:
                    print '         Gamma: ', gam
                    subhalo = HW_Fit(m, gam=gam, rb=rb, M200=True, gcd=8.5, stiff_rb=False)
                    for ind, d in enumerate(dist_list):
                        print '           Distance', d
                        value = '{:.3e}     {:.3e}      {:.3e}      {:.3e}'.format(m, rb, gam, d)
                        try:
                            f = np.loadtxt(dir + file_name)
                            m_check = float('{:.3e}'.format(m))
                            rb_check = float('{:.3e}'.format(rb))
                            gam_check = float('{:.3e}'.format(gam))
                            d_check = float('{:.3e}'.format(d))
                            if np.sum((f[:, 0] == m_check) & (f[:, 1] == rb_check) &
                                              (f[:, 2] == gam_check) & (f[:, 3] == d_check)) < 1:
                                print np.sum((f[:, 0] == m_check) & (f[:, 1] == rb_check) &
                                              (f[:, 2] == gam_check) & (f[:, 3] == d_check))
                                raise ValueError
                        except:
                            if subhalo.Full_Extension(d) > 0.1:
                                ext = subhalo.Spatial_Extension(d)
                                print '             Extension: ', ext
                                value += '      {:.3e} \n'.format(float(ext))
                                ff = open(dir + file_name, 'a+')
                                ff.write(value)
                                ff.close()

    return
