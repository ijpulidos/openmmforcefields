"""
System generators that build an OpenMM System object from a Topology object.

"""

################################################################################
# LOGGER
################################################################################

import logging
_logger = logging.getLogger("perses.forcefields.system_generators")

################################################################################
# System generator base class
################################################################################

class SystemGenerator(object):
    """
    Common interface for generating OpenMM Systems from OpenMM Topology objects
    that may contain both biopolymers (with parameters provided by OpenMM) and small molecules
    (with parameters provided by residue template generators).

    Currently, this class supports

    * GAFF, via ``GAFFTemplateGenerator``: see ``GAFFTemplateGenerator.INSTALLED_FORCEFIELDS``
    * SMIRNOFF, via ``SMIRNOFFTemplateGenerator``: see ``SMIRNOFFTemplateGenerator.INSTALLED_FORCEFIELDS``

    .. todo ::

       Once Open Force Field Topology objects support residue definitions, we will also be able
       to support Open Force Field Topology objects (which carry their own Molecule definitions).

    Parameters
    ----------
    forcefield : simtk.openmm.app.ForceField
        The ForceField object used to create new System objects.
        New ffxml files can be read in at any time.
    forcefield_kwargs : dict
        Keyword arguments fed to ``simtk.openmm.app.ForceField.createSystem()`` during System generation.
        These keyword arguments can be modified at any time.
    template_generator : openmmforcefields.generators.SmallMoleculeTemplateGenerator
        The small molecule residue template generator subclass used for small molecules.
    barostat : simtk.openmm.MonteCarloBarostat
        If not None, this container holds the barostat parameters to use for newly created System objects.
    postprocess_system : method
        If not None, this method will be called as ``system = postprocess_system(system)`` to post-process the System object for create_system(topology) before it is returned.
    """
    def __init__(self, forcefields=None, small_molecule_forcefield='openff-1.0.0', forcefield_kwargs=None, barostat=None, molecules=None, cache=None, postprocess_system=None):
        """
        This is a utility class to generate OpenMM Systems from Open Force Field Topology objects using AMBER
        protein force fields and GAFF small molecule force fields.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        forcefields : list of str, optional, default=None
            List of the names of ffxml files that will be used in System creation for the biopolymer.
        small_molecule_forcefield : str, optional, default='openff-1.0.0'
            Small molecule force field to use.
            Must be supported by one of the registered template generators: [GAFFTemplateGenerator, SMIRNOFFTemplateGenerator]
            Supported GAFF force fields include: ['gaff-2.11', 'gaff-2.1', 'gaff-1.81', 'gaff-1.8', 'gaff-1.4']
            (See ``GAFFTemplateGenerator.INSTALLED_FORCEFIELDS`` for a complete list.)
            Supported SMIRNOFF force fields include: [`openff-1.0.0`, `smirnoff99Frosst-1.1.0`]
            (See ``SMIRNOFFTemplateGenerator.INSTALLED_FORCEFIELDS`` for a complete list.)
        forcefield_kwargs : dict, optional, default=None
            Keyword arguments to be passed to ``simtk.openmm.app.ForceField.createSystem()`` during ``System`` object creation.
        barostat : simtk.openmm.MonteCarloBarostat, optional, default=None
            If not None, a new ``MonteCarloBarostat`` with matching parameters (but a different random number seed) will be created and
            added to each newly created ``System``.
        molecules : openforcefield.topology.Molecule or list, optional, default=None
            Can alternatively be an object (such as an OpenEye OEMol or RDKit Mol or SMILES string) that can be used to construct a Molecule.
            Can also be a list of Molecule objects or objects that can be used to construct a Molecule.
            If specified, these molecules will be recognized and parameterized as needed.
            The parameters will be cached in case they are encountered again the future.
        cache : filename, optional, default=None
            If not None, filename for caching small molecule residue templates.
        postprocess_system : method, optiona, default=None
            If not None, this method will be called as ``system = postprocess_system(system)`` to post-process the System object for create_system(topology) before it is returned.

        Examples
        --------

        Here's an example that uses GAFF 2.11 along with the new ``ff14SB`` generation of AMBER force fields
        (and compatible solvent models) to generate an OpenMM ``System`` object from an
        `Open Force Field Topology <https://open-forcefield-toolkit.readthedocs.io/en/latest/api/generated/openforcefield.topology.Topology.html#openforcefield.topology.Topology>`_ object:

        >>> # Define the keyword arguments to feed to ForceField
        >>> from simtk import unit
        >>> from simtk.openmm import app
        >>> # Define standard OpenMM biopolymer and solvent force fields to use

        To initialize the ``SystemGenerator``, we specify the OpenMM force fields, the small molecule force field, and any ``kwargs`` to be fed
        to the OpenMM ``simtk.openmm.app.ForceField.createSystem()`` method:

        >>> from openmmforcefields.generators import SystemGenerator
        >>> amber_forcefields = ['amber/protein.ff14SB.xml', 'amber/tip3p_standard.xml', 'amber/tip3p_HFE_multivalent.xml']
        >>> small_molecule_forcefield = 'gaff-2.11'
        >>> forcefield_kwargs = { 'constraints' : app.HBonds, 'rigidWater' : True, 'removeCMMotion' : False,
        ... 'nonbondedMethod' : app.PME, 'hydrogenMass' : 4*unit.amu }
        >>> system_generator = SystemGenerator(forcefields=amber_forcefields, small_molecule_forcefield=small_molecule_forcefield, forcefield_kwargs=forcefield_kwargs)

        If the ``cache`` argument is specified, parameterized molecules are cached in the corresponding file.

        >>> cache = 'db.json'
        >>> system_generator = SystemGenerator(forcefields=forcefields, small_molecule_forcefield='gaff-2.11', forcefield_kwargs=forcefield_kwargs, cache=cache)

        To use a barostat, you need to define a barostat whose parameters will be copied into each system (with a different random number seed):

        >>> pressure = 1.0 * unit.atmospheres
        >>> temperature = 298.0 * unit.kelvin
        >>> frequency = 25 # steps
        >>> system_generator.barostat = openmm.MonteCarloBarostat(pressure, temperature, frequency)

        Now, you can create an OpenMM ``System`` object from an OpenMM ``Topology`` object and a list of openforcefield ``Molecule`` objects

        >>> system = system_generator.create_system(openmm_topology, molecules=molecules)

        Parameters for multiple force fields can be held in the same cache file.

        To use the `Open Force Field 'openff-1.0.0' ("Parsley") force field <https://openforcefield.org/news/introducing-openforcefield-1.0/>`_ instead,
        simply change the ``small_molecule_forcefield`` parameter to one of the supported ``GAFFTemplateGenerator.INSTALLED_FORCEFIELDS``:

        >>> small_molecule_forcefield = 'openff-1.0.0'
        >>> system_generator = SystemGenerator(forcefields=forcefields, small_molecule_forcefield=small_molecule_forcefield, forcefield_kwargs=forcefield_kwargs)

        For debugging convenience, you can also turn _off_ specific interactions during system creation, such as particle charges:

        >>> system_generator.particle_charges = False # will cause particle charges to be set to zero
        >>> system_generator.exception_charges = False # will zero out all 1-4 charge interactions
        >>> system_generator.particle_epsilons = False # will zero out Lennard-Jones particle-particle interactions
        >>> system_generator.particle_exceptions = False # will zero out all 1-4 Lennard-Jones interactions
        >>> system_generator.torsions = False # will zero out all torsion terms

        """

        # Initialize
        self.barostat = barostat # barostat to copy, or None if no barostat is to be added

        # Post-creation system transformations
        self.particle_charges = True # include particle charges
        self.exception_charges = True # include electrostatics nonzero exceptions
        self.particle_epsilons = True # include LJ particles
        self.exception_epsilons = True # include LJ nonzero exceptions
        self.torsions = True # include torsions

        # Method to use for postprocessing system
        self.postprocess_system = postprocess_system

        # Create OpenMM ForceField object
        forcefields = forcefields if (forcefields is not None) else list()
        from simtk.openmm import app
        self.forcefield = app.ForceField(*forcefields)

        # Cache force fields and settings to use
        self.forcefield_kwargs = forcefield_kwargs if forcefield_kwargs is not None else dict()

        # Create and cache a residue template generator
        from openmmforcefields.generators.template_generators import SmallMoleculeTemplateGenerator
        self.template_generator = None
        if small_molecule_forcefield is not None:
            for template_generator_cls in SmallMoleculeTemplateGenerator.__subclasses__():
                try:
                    _logger.debug(f'Trying {template_generator_cls.__name__} to load {small_molecule_forcefield}')
                    self.template_generator = template_generator_cls(forcefield=small_molecule_forcefield, cache=cache)
                except ValueError as e:
                    _logger.debug(f'  {template_generator_cls.__name__} cannot load {small_molecule_forcefield}')
                    _logger.debug(e)
            if self.template_generator is None:
                msg = f"No registered small molecule template generators could load force field '{small_molecule_forcefield}'\n"
                msg += f"Available installed force fields are:\n"
                for template_generator_cls in SmallMoleculeTemplateGenerator.__subclasses__():
                    msg += f'  {template_generator_cls.__name__}: {template_generator_cls.INSTALLED_FORCEFIELDS}\n'
                raise ValueError(msg)
            self.forcefield.registerTemplateGenerator(self.template_generator.generator)

        # Inform the template generator about any specified molecules
        self.add_molecules(molecules)

    def add_molecules(self, molecules):
        """
        Add molecules to registered template generator

        Parameters
        ----------
        molecules : openforcefield.topology.Molecule or list, optional, default=None
            Can alternatively be an object (such as an OpenEye OEMol or RDKit Mol or SMILES string) that can be used to construct a Molecule.
            Can also be a list of Molecule objects or objects that can be used to construct a Molecule.
            If specified, these molecules will be recognized and parameterized as needed.
            The parameters will be cached in case they are encountered again the future.

        """
        if self.template_generator is None:
            raise ValueError("You must have a small molecule residue template generator registered to add small molecules")

        self.template_generator.add_molecules(molecules)

    def _modify_forces(self, system):
        """
        Add barostat and modify forces if requested.
        """
        # Add barostat if requested.
        if self.barostat is not None:
            import numpy as np
            from simtk import openmm
            MAXINT = np.iinfo(np.int32).max

            # Determine pressure, temperature, and frequency
            pressure = self.barostat.getDefaultPressure()
            if hasattr(self.barostat, 'getDefaultTemperature'):
                temperature = self.barostat.getDefaultTemperature()
            else:
                temperature = self.barostat.getTemperature()
            frequency = self.barostat.getFrequency()

            # Create the barostat
            # TODO: Make sure we can support other kinds of barostats?
            barostat = openmm.MonteCarloBarostat(pressure, temperature, frequency)
            seed = np.random.randint(MAXINT)
            barostat.setRandomNumberSeed(seed)
            system.addForce(barostat)

        # Modify forces if requested
        for force in system.getForces():
            if force.__class__.__name__ == 'NonbondedForce':
                for index in range(force.getNumParticles()):
                    charge, sigma, epsilon = force.getParticleParameters(index)
                    if not self.particle_charges:
                        charge *= 0
                    if not self.particle_epsilons:
                        epsilon *= 0
                    force.setParticleParameters(index, charge, sigma, epsilon)
                for index in range(force.getNumExceptions()):
                    p1, p2, chargeProd, sigma, epsilon = force.getExceptionParameters(index)
                    if not self.exception_charges:
                        chargeProd *= 0
                    if not self.exception_epsilons:
                        epsilon *= 0
                    force.setExceptionParameters(index, p1, p2, chargeProd, sigma, epsilon)
            elif force.__class__.__name__ == 'PeriodicTorsionForce':
                for index in range(force.getNumTorsions()):
                    p1, p2, p3, p4, periodicity, phase, K = force.getTorsionParameters(index)
                    if not self.torsions:
                        K *= 0
                    force.setTorsionParameters(index, p1, p2, p3, p4, periodicity, phase, K)

    def create_system(self, topology, molecules=None):
        """
        Create a system from the specified topology.

        .. todo :: Add support for openforcefield Topology objects once they can be converted to OpenMM Topology objects.

        Parameters
        ----------
        topology : openmmtools.topology.Topology object
            The topology describing the system to be created
        molecules : openforcefield.topology.Molecule or list of Molecules, optional, default=None
            Can alternatively be an object (such as an OpenEye OEMol or RDKit Mol or SMILES string) that can be used to construct a Molecule.
            Can also be a list of Molecule objects or objects that can be used to construct a Molecule.
            If specified, these molecules will be recognized and parameterized with antechamber as needed.
            The parameters will be cached in case they are encountered again the future.

        Returns
        -------
        system : simtk.openmm.System
            A system object generated from the topology

        """
        # Inform the template generator about any specified molecules
        if (self.template_generator is not None) and (molecules is not None):
            self.template_generator.add_molecules(molecules)

        # Build the System
        system = self.forcefield.createSystem(topology, **self.forcefield_kwargs)

        # Modify other forces as requested
        self._modify_forces(system)

        # Post-process the System if requested
        if self.postprocess_system is not None:
            system = self.postprocess_system(system)

        return system

################################################################################
# Dummy system generator
################################################################################

class DummySystemGenerator(SystemGenerator):
    """
    Dummy force field that can add basic parameters to any system for testing purposes.

    * All particles are assigned carbon mass
    * All particles interact with a repulsive potential
    * All bonds have equilibrium length 1 A
    * All angles have equilibrium angle dependent on number of substituents of central atom
        * 2, 3 bonds: 120 degrees
        * 4 bonds: 109.8 degrees
        * 5 or more bonds: 90 degrees
    * Torsions are added with periodicity 3, but no barrier height

    """
    def create_system(self, topology, **kwargs):
        """
        Create a System object with simple parameters from the provided Topology

        Any kwargs are ignored.

        Parameters
        ----------
        topology : openforcefield.topology.Topology
            The Topology to be parameterized

        Returns
        -------
        system : simtk.openmm.System
            The System object

        """
        # TODO: Allow periodicity to be determined from topology

        from openmmtools.constants import kB
        kT = kB * 300*unit.kelvin # hard-coded temperature for setting energy scales

        # Create a System
        system = openmm.System()

        # Add particles
        mass = 12.0 * unit.amu
        for atom in topology.atoms:
            system.addParticle(mass)

        # Add simple repulsive interactions
        # TODO: Use softcore repulsive interaction; Gaussian times switch?
        nonbonded = openmm.CustomNonbondedForce('100/(r/0.1)^4')
        nonbonded.setNonbondedMethod(openmm.CustomNonbondedForce.CutoffNonPeriodic);
        nonbonded.setCutoffDistance(1*unit.nanometer)
        system.addForce(nonbonded)
        for atom in topology.atoms:
            nonbonded.addParticle([])

        # Build a list of which atom indices are bonded to each atom
        bondedToAtom = []
        for atom in topology.atoms():
            bondedToAtom.append(set())
        for (atom1, atom2) in topology.bonds():
            bondedToAtom[atom1.index].add(atom2.index)
            bondedToAtom[atom2.index].add(atom1.index)
        return bondedToAtom

        # Add bonds
        bond_force = openmm.HarmonicBondForce()
        r0 = 1.0 * unit.angstroms
        sigma_r = 0.1 * unit.angstroms
        Kr = kT / sigma_r**2
        for atom1, atom2 in topology.bonds():
            bond_force.addBond(atom1.index, atom2.index, r0, Kr)
        system.addForce(bond_force)

        # Add angles
        uniqueAngles = set()
        for bond in topology.bonds():
            for atom in bondedToAtom[bond.atom1]:
                if atom != bond.atom2:
                    if atom < bond.atom2:
                        uniqueAngles.add((atom, bond.atom1, bond.atom2))
                    else:
                        uniqueAngles.add((bond.atom2, bond.atom1, atom))
            for atom in bondedToAtom[bond.atom2]:
                if atom != bond.atom1:
                    if atom > bond.atom1:
                        uniqueAngles.add((bond.atom1, bond.atom2, atom))
                    else:
                        uniqueAngles.add((atom, bond.atom2, bond.atom1))
        angles = sorted(list(uniqueAngles))
        theta0 = 109.5 * unit.degrees # TODO: Adapt based on number of bonds to each atom?
        sigma_theta = 10 * unit.degrees
        Ktheta = kT / sigma_theta**2
        angle_force = openmm.HarmonicAngleForce()
        for (atom1, atom2, atom3) in angles:
            angles.addAngle(atom1.index, atom2.index, atom3.index, theta0, Ktheta)
        system.addForce(angle_force)

        # Make a list of all unique proper torsions
        uniquePropers = set()
        for angle in angles:
            for atom in bondedToAtom[angle[0]]:
                if atom not in angle:
                    if atom < angle[2]:
                        uniquePropers.add((atom, angle[0], angle[1], angle[2]))
                    else:
                        uniquePropers.add((angle[2], angle[1], angle[0], atom))
            for atom in bondedToAtom[angle[2]]:
                if atom not in angle:
                    if atom > angle[0]:
                        uniquePropers.add((angle[0], angle[1], angle[2], atom))
                    else:
                        uniquePropers.add((atom, angle[2], angle[1], angle[0]))
        propers = sorted(list(uniquePropers))
        torsion_force = openmm.PeriodicTorsionForce()
        periodicity = 3
        phase = 0.0 * unit.degrees
        Kphi = 0.0 * kT
        for (atom1, atom2, atom3, atom4) in propers:
            torsion_force.add_torsion(atom1.index, atom2.index, atom3.index, atom4.index, periodicity, phase, Kphi)
        system.addForce(torsion_force)

        return system