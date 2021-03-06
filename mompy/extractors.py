#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
Given a moment matrix and its values, extract solutions
"""

import numpy as np
import scipy as sc
import scipy.linalg # for schur decomp, which np doesnt have
import numpy.linalg # for its norm, which suits us better than scipy
import itertools
import ipdb
import util

def dict_mono_to_ind(monolist):
    dict = {}
    for i,mono in enumerate(monolist):
        dict[mono]=i
    return dict

def extract_solutions_lasserre(MM, ys, Kmax=10, tol=1e-6, maxdeg = None):
    """
    extract solutions via (unstable) row reduction described by Lassarre and used in gloptipoly
    MM is a moment matrix, and ys are its completed values
    @params - Kmax: the maximum rank allowed to extract
    @params - tol: singular values less than this is truncated.
    @params - maxdeg: only extract from the top corner of the matrix up to maxdeg
    """
    M = MM.numeric_instance(ys, maxdeg = maxdeg)
    
    Us,Sigma,Vs=np.linalg.svd(M)
    #
    count = min(Kmax,sum(Sigma>tol))
    # now using Lassarre's notation in the extraction section of
    # "Moments, Positive Polynomials and their Applications"
    T,Ut = util.srref(Vs[0:count,:])
    
    if Sigma[count] <= tol:
        print 'lost %.7f' % Sigma[count]
    # inplace!
    util.row_normalize_leadingone(Ut)

    couldbes = np.where(Ut>0.9)
    ind_leadones = np.zeros(Ut.shape[0], dtype=np.int)
    for j in reversed(range(len(couldbes[0]))):
        ind_leadones[couldbes[0][j]] = couldbes[1][j]

    basis = [MM.row_monos[i] for i in ind_leadones]
    dict_row_monos = dict_mono_to_ind(MM.row_monos)
    
    Ns = {}
    bl = len(basis)
    # create multiplication matrix for each variable
    for var in MM.vars:
        Nvar = np.zeros((bl,bl))
        for i,b in enumerate(basis):
            Nvar[:,i] = Ut[ :,dict_row_monos[var*b] ]
        Ns[var] = Nvar

    N = np.zeros((bl,bl))
    for var in Ns:
        N+=Ns[var]*np.random.randn()
    T,Q=scipy.linalg.schur(N)

    sols = {}

    quadf = lambda A, x : np.dot(x, np.dot(A,x))
    for var in MM.vars:
        sols[var] = np.array([quadf(Ns[var], Q[:,j]) for j in range(bl)])
    #ipdb.set_trace()
    return sols

def extract_solutions_lasserre_average(MM, ys, Kmax=10, tol=1e-6, numiter=10):
    """
    extract solutions via (unstable) row reduction described by Lassarre and used in gloptipoly
    MM is a moment matrix, and ys are its completed values
    """
    M = MM.numeric_instance(ys)
    Us,Sigma,Vs=np.linalg.svd(M)
    #
    count = min(Kmax,sum(Sigma>tol))
    # now using Lassarre's notation in the extraction section of
    # "Moments, Positive Polynomials and their Applications"
    sols = {}
    totalweight = 0;
    for i in range(numiter):
        
        T,Ut = util.srref(M[0:count,:])
        
        if Sigma[count] <= tol:
            print 'lost %.7f' % Sigma[count]
        # inplace!
        util.row_normalize_leadingone(Ut)

        couldbes = np.where(Ut>0.9)
        ind_leadones = np.zeros(Ut.shape[0], dtype=np.int)
        for j in reversed(range(len(couldbes[0]))):
            ind_leadones[couldbes[0][j]] = couldbes[1][j]

        basis = [MM.row_monos[i] for i in ind_leadones]
        dict_row_monos = dict_mono_to_ind(MM.row_monos)

        Ns = {}
        bl = len(basis)
        # create multiplication matrix for each variable
        for var in MM.vars:
            Nvar = np.zeros((bl,bl))
            for i,b in enumerate(basis):
                Nvar[:,i] = Ut[ :,dict_row_monos[var*b] ]
            Ns[var] = Nvar

        N = np.zeros((bl,bl))
        for var in Ns:
            N+=Ns[var]*np.random.randn()
        T,Q=scipy.linalg.schur(N)

        quadf = lambda A, x : np.dot(x, np.dot(A,x))
        for var in MM.vars:
            sols[var] = np.array([quadf(Ns[var], Q[:,j]) for j in range(bl)])
            
    return sols

def extract_solutions_dreesen_proto(MM, ys, Kmax=10, tol=1e-5):
    """
    extract solutions dreesen's nullspace method
    this is the prototype implementation that does not match solutions!
    """
    M = MM.numeric_instance(ys)
    Us,Sigma,Vs=sc.linalg.svd(M)
    
    count = min(Kmax,sum(Sigma>tol))
    Z = Us[:,0:count]
    print 'the next biggest eigenvalue we are losing is %f' % Sigma[count]

    dict_row_monos = dict_mono_to_ind(MM.row_monos)
    
    sols = {}
    for var in MM.vars:
        S1 = np.zeros( (len(MM.row_monos), len(MM.row_monos)) )
        Sg = np.zeros( (len(MM.row_monos), len(MM.row_monos)) )
        # a variable is in basis of the current var if var*basis in row_monos
        basis = []
        i = 0
        for mono in MM.row_monos:
            if mono*var in MM.row_monos:
                basis.append(mono)
                basisind = dict_row_monos[mono]
                gind = dict_row_monos[mono*var]
                
                S1[i, basisind] = 1
                Sg[i, gind] = 1
                i += 1
        S1 = S1[0:i,:]
        Sg = Sg[0:i,:]
        
        A = Sg.dot(Z)
        B = S1.dot(Z)
        
        # damn this, cant i just have a GE solver that works for non-square matrices?
        __,__,P = np.linalg.svd(np.random.randn(count,i), full_matrices = False)
        
        sols[var] = sc.real(sc.linalg.eigvals(P.dot(A),P.dot(B))).tolist()
        
    return sols

def extract_solutions_dreesen(MM, ys, Kmax=10, tol=1e-5):
    """
    extract solutions dreesen's nullspace method
    """
    M = MM.numeric_instance(ys)
    Us,Sigma,Vs=sc.linalg.svd(M)
    
    count = min(Kmax,sum(Sigma>tol))
    Z = Us[:,0:count]
    print 'the next biggest eigenvalue we are losing is %f' % Sigma[count]

    dict_row_monos = dict_mono_to_ind(MM.row_monos)
    
    sols = {}
    
    S1list = []
    Sglist = []
    it = 0 # i total
    for var in MM.vars:
        S1 = np.zeros( (len(MM.row_monos), len(MM.row_monos)) )
        Sg = np.zeros( (len(MM.row_monos), len(MM.row_monos)) )
        # a variable is in basis of the current var if var*basis in row_monos
        basis = []
        i = 0
        for mono in MM.row_monos:
            if mono*var in MM.row_monos:
                basis.append(mono)
                basisind = dict_row_monos[mono]
                gind = dict_row_monos[mono*var]
                S1[i, basisind] = 1
                Sg[i, gind] = 1
                i += 1
        S1 = S1[0:i,:]
        Sg = Sg[0:i,:]
        S1list.append(S1)
        Sglist.append(Sg)

    S1s = np.zeros( (len(MM.row_monos)*len(MM.vars), len(MM.row_monos)) )
    Sgs = np.zeros( (len(MM.row_monos)*len(MM.vars), len(MM.row_monos)) )

    r = 0
    for i in xrange(len(S1list)):
        S1i = S1list[i]
        Sgi = Sglist[i]
        numrow = S1i.shape[0]
        S1s[r:r+numrow, :] = S1i
        Sgs[r:r+numrow, :] = Sgi
        r = r + numrow
                
    S1s = S1s[0:r,:]
    Sgs = Sgs[0:r,:]

    A = Sgs.dot(Z)
    B = S1s.dot(Z)
    
    __,__,P = np.linalg.svd(np.random.randn(count,r), full_matrices = False)
    Dproj, V = sc.linalg.eig(P.dot(A),P.dot(B))
    
    sols = {}
    for i,var in enumerate(MM.vars):
        Ai = Sglist[i].dot(Z)
        Bi = S1list[i].dot(Z)
        AiVBiV = sc.sum(Ai.dot(V) * Bi.dot(V), 0)
        BiVBiV = sc.sum(Bi.dot(V) * Bi.dot(V), 0)
        sols[var] = AiVBiV / BiVBiV
    #ipdb.set_trace()
    return sols

def test_solution_extractors():
    import sympy as sp
    import core as core
    x = sp.symbols('x')
    M = core.MomentMatrix(2, [x], morder='grevlex')
    ys = [1, 1.5, 2.5, 4.5, 8.5]
    sols_lass = extract_solutions_lasserre(M, ys)

    sols_dree = extract_solutions_dreesen(M, ys)
    print sols_lass, sols_dree
    print 'true values are 1 and 2'
    
if __name__ == "__main__":
    test_solution_extractors()
