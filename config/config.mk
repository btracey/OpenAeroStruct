# ----------------------------------------------------------------------
# Config file for Gfortran  with OpenMPI
# ----------------------------------------------------------------------

# ------- Define a possible parallel make ------------------------------
PMAKE = make -j 4

# ------- Define the MPI Compilers--------------------------------------
FF90 = mpif90
CC   = mpicc

# ------- Define CGNS Inlcude and linker flags -------------------------
CGNS_INCLUDE_FLAGS=-I$(HOME)/packages/cgnslib_3.2.1/src
CGNS_LINKER_FLAGS=-L$(HOME)/packages/cgnslib_3.2.1/src -lcgns

# ------- Define Compiler Flags ----------------------------------------
FF90_GEN_FLAGS = -fPIC -g -fbounds-check
CC_GEN_FLAGS   = -fPIC

FF90_OPT_FLAGS   = -fPIC -fdefault-real-8 -O2 -fdefault-double-8
CC_OPT_FLAGS     = -O2

# ------- Define Archiver  and Flags -----------------------------------
AR       = ar
AR_FLAGS = -rvs

# ------- Define Linker Flags ------------------------------------------
LINKER_FLAGS =

# ------- Define Petsc Info --- Should not need to modify this -----
include ${PETSC_DIR}/lib/petsc/conf/variables # PETSc 3.6
#include ${PETSC_DIR}/conf/variables # PETSc 3.5
PETSC_INCLUDE_FLAGS= ${PETSC_CC_INCLUDES} -I$(PETSC_DIR)
PETSC_LINKER_FLAGS= ${PETSC_LIB}

# Define potentially different python, python-config and f2py executables:
PYTHON = python
PYTHON-CONFIG = python-config
F2PY = f2py
