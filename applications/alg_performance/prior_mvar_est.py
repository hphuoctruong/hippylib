# Copyright (c) 2016-2018, The University of Texas at Austin 
# & University of California--Merced.
# Copyright (c) 2019-2020, The University of Texas at Austin 
# University of California--Merced, Washington University in St. Louis.
#
# All Rights reserved.
# See file COPYRIGHT for details.
#
# This file is part of the hIPPYlib library. For more information and source code
# availability see https://hippylib.github.io.
#
# hIPPYlib is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (as published by the Free
# Software Foundation) version 2.0 dated June 1991.

import dolfin as dl
import ufl
import math
import numpy as np
import matplotlib.pyplot as plt
import argparse

import sys
import os
sys.path.append( os.environ.get('HIPPYLIB_BASE_DIR', "../../") )
from hippylib import *

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Marginal Variance Estimation')
    parser.add_argument('--nx',
                        default=128,
                        type=int,
                        help="Number of elements in x-direction")
    parser.add_argument('--ny',
                        default=128,
                        type=int,
                        help="Number of elements in y-direction")

    args = parser.parse_args()
    try:
        dl.set_log_active(False)
    except:
        pass
    sep = "\n"+"#"*80+"\n"
    ndim = 2
    nx = args.nx
    ny = args.ny
    mesh = dl.UnitSquareMesh(nx, ny)
    
    rank = dl.MPI.rank(mesh.mpi_comm())
    nproc = dl.MPI.size(mesh.mpi_comm())
            
    Vh = dl.FunctionSpace(mesh, 'Lagrange', 1)
    
    ndofs = Vh.dim()
    
    if rank == 0:
        print ("Number of dofs: {0}".format(ndofs) )

    gamma = .1
    delta = .5
    
    theta0 = 2.
    theta1 = .5
    alpha  = math.pi/4
    
    anis_diff = dl.CompiledExpression(ExpressionModule.AnisTensor2D(), degree = 1)
    anis_diff.set(theta0, theta1, alpha)
    
    prior = BiLaplacianPrior(Vh, gamma, delta, anis_diff, robin_bc=True )
    prior.Asolver = PETScLUSolver(mesh.mpi_comm(), "mumps")
    prior.Asolver.set_operator(prior.A)
    
    pr_pw_variance_exact = prior.pointwise_variance(method="Exact")
    
    norm = pr_pw_variance_exact.norm("l2")
    print(norm)
    
    nvs = np.array([int(2**i) for i in range(int( math.log2(nx*ny) ))], dtype=np.int)
    
    data  = np.zeros((nvs.shape[0], 4), dtype=np.float64)
    data[:,0] = nvs

    
    for i in np.arange(nvs.shape[0]):
        nv = nvs[i]
        pr_pw_variance_1 = prior.pointwise_variance(method="Estimator", k=nv, estimator_distribution='rademacher')
        pr_pw_variance_1.axpy(-1., pr_pw_variance_exact)
        err = pr_pw_variance_1.norm("l2")
        data[i, 1] = err/norm
            
    for i in np.arange(nvs.shape[0]):
        nv = nvs[i]
        pr_pw_variance_1 = prior.pointwise_variance(method="Estimator", k=nv, estimator_distribution='normal')
        pr_pw_variance_1.axpy(-1., pr_pw_variance_exact)
        err = pr_pw_variance_1.norm("l2")
        data[i, 2] = err/norm
            
    for i in np.arange(nvs.shape[0]):
        nv = nvs[i]
        pr_pw_variance_2 = prior.pointwise_variance(method="Randomized", r=nv//2)
        pr_pw_variance_2.axpy(-1., pr_pw_variance_exact)
        err = pr_pw_variance_2.norm("l2")
        data[i, 3] = err/norm
            
    np.savetxt('data_cov_estimation.txt', data, header='nv err_rademacher err_gaussian err_ours')
    
    plt.loglog(data[:,0], data[:,1], '-b', label='Rademacher')
    plt.loglog(data[:,0], data[:,2], '-r', label='Gaussian')
    plt.loglog(data[:,0], data[:,3], '-g', label='Our')
    plt.legend()
    plt.show()
    