# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

# ----------------------------------------------------------------------------
# If you submit this package back to Spack as a pull request,
# please first remove this boilerplate and all FIXME comments.
#
# This is a template package file for Spack.  We've put "FIXME"
# next to all the things you'll want to change. Once you've handled
# them, you can save this file and test your package like this:
#
#     spack install remora
#
# You can edit this file again by typing:
#
#     spack edit remora
#
# See the Spack documentation for more information on packaging.
# ----------------------------------------------------------------------------

from spack.package import *


import itertools

from spack import *
import os

def process_amrex_constraints():
    """Map constraints when building with external AMReX"""
    a1 = ['+', '~']
    a2 = ['mpi', 'cuda']
    a3 = [[x + y for x in a1] for y in a2]
    for k in itertools.product(*a3):
        if '+cuda' in k:
            for arch in CudaPackage.cuda_arch_values:
                yield ''.join(k) + " cuda_arch=%s" % arch
        else:
            yield ''.join(k)
class Remora(CMakePackage, CudaPackage, ROCmPackage):
    """REMORA is currently under development as a next-generation version of the Regional Ocean Modeling System (ROMS).
      REMORA is built on AMReX, an adaptive mesh refinement software framework, which provides the underlying software
      infrastructure for block structured AMR operations.
     REMORA is designed to run on machines from laptops to multicore CPU and hybrid CPU/GPU systems.
     This documentation is currently under development, there are detailed resources available on the
     ROMS Documentation Portal for the Regional Ocean Modeling System.
    """

    homepage = "https://roms-x.readthedocs.io/en/latest/index.html`"
    url = "https://github.com/iulian787/REMORA/archive/refs/tags/r0.9.tar.gz"
    git = "https://github.com/seahorce-scidac/REMORA.git"
    version("development", branch="development", submodules=True) 

    maintainers("jmsexton03", "hklion", "asalmgren", "iulian787")

    version('develop', branch='development', submodules=True)
#    version('develop', branch='development')

    # Config options
    variant('dimensions', default='3',
            description='Dimensionality', values=('2', '3'))
    variant('shared',  default=False,
            description='Build shared library')
    variant('mpi',          default=True,
            description='Build with MPI support')
    variant('openmp',       default=False,
            description='Build with OpenMP support')
    variant('precision',  default='double',
            description='Real precision (double/single)',
            values=('single', 'double'))
    variant('eb',  default=False,
            description='Build Embedded Boundary classes')
    variant('fortran',  default=False,
            description='Build Fortran API')
    variant('hdf5',  default=False,
            description='Enable HDF5-based I/O')
    variant('tests', default=True,
            description='Activate regression tests')
    variant('netcdf', default=True,
            description='Enable NetCDF support')
    variant('internal-amrex', default=True,
            description='Use AMRex submodule to build')
    variant('fortran', default=False,
            description='Build fortran interfaces')

    conflicts('+openmp', when='+cuda')

    depends_on('amrex')
    depends_on('mpi', when='+mpi')

    for opt in process_amrex_constraints():
        dopt = '+particles' + opt
        depends_on('amrex@develop' + dopt, when='~internal-amrex' + opt)

    depends_on('netcdf-c', when='+netcdf')

    # Build dependencies
    depends_on('mpi', when='+mpi')
    depends_on('cuda@9.0.0:', when='+cuda')
    depends_on('python@2.7:', type='build', when='@:20.04')
    depends_on('cmake@3.5:',  type='build', when='@:18.10.99')
    depends_on('cmake@3.13:', type='build', when='@18.11:')
    depends_on('cmake@3.14:', type='build', when='@19.04:')
    # cmake @3.17: is necessary to handle cuda @11: correctly
    depends_on('cmake@3.17:', type='build', when='^cuda @11:')
    depends_on('hdf5@1.10.4: +mpi', when='+hdf5')
    depends_on('rocrand', type='build', when='+rocm')
    depends_on('rocprim', type='build', when='@21.05: +rocm')

    # these versions of gcc have lambda function issues
    # see https://github.com/spack/spack/issues/22310
    conflicts('%gcc@8.1.0:8.3.0', when='@21.03')
    conflicts('%gcc@8.1.0:8.2.0', when='@21.01:21.02')

    # Check options compatibility
    conflicts('+cuda', when='+rocm', msg='CUDA and HIP support are exclusive')

    def get_cuda_arch_string(self, values):
        if 'none' in values:
            return 'Auto'
        else:
            # Use format x.y instead of CudaPackage xy format
            vf = tuple(float(x) / 10.0 for x in values)
            return ';'.join(str(x) for x in vf)

    for opt in process_amrex_constraints():
        dopt = '+particles' + opt
        depends_on('amrex@develop' + dopt, when='~internal-amrex' + opt)

    depends_on('netcdf-c', when='+netcdf')

    def cmake_args(self):
        spec = self.spec

        define = CMakePackage.define

        vs = ["mpi", "cuda", "openmp", "netcdf",
              "tests", "fortran"]
        args = [
            self.define_from_variant("REMORA_ENABLE_%s" % v.upper(), v)
            for v in vs
        ]

        args += [
            self.define('CMAKE_EXPORT_COMPILE_COMMANDS', True),
            self.define('REMORA_ENABLE_ALL_WARNINGS', True),
            self.define_from_variant('BUILD_SHARED_LIBS', 'shared'),
            self.define_from_variant('REMORA_TEST_WITH_FCOMPARE', 'tests'),
        ]

        if '+cuda' in self.spec:
            amrex_arch = ['{0:.1f}'.format(float(i if i!="none" else 10.0) / 10.0)
                          for i in self.spec.variants['cuda_arch'].value]
            if amrex_arch:
                args.append(self.define('AMReX_CUDA_ARCH', amrex_arch))

        if '+internal-amrex' in self.spec:
            args.append(self.define('REMORA_USE_INTERNAL_AMREX', True))
        else:
            args += [
                self.define('REMORA_USE_INTERNAL_AMREX', False),
                self.define('AMReX_ROOT', self.spec['amrex'].prefix)
            ]

        print(args)

        return args

    @property
    def libs(self):
        libsuffix = {'2': '2d', '3': '3d', 'rz': 'rz'}
        dims = self.spec.variants['dims'].value
        return find_libraries(
            ['liberf.' + libsuffix[dims]], root=self.prefix, recursive=True,
            shared=True
        )
