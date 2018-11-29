import functools
import logging

from timeit import timeit

import numpy as np
import pytest

from psyneulink.core.components.functions.integratorfunctions import SimpleIntegrator
from psyneulink.core.components.functions.transferfunctions import Linear
from psyneulink.core.components.functions.interfacefunctions import Identity
from psyneulink.core.components.mechanisms.processing.compositioninterfacemechanism import CompositionInterfaceMechanism
from psyneulink.core.components.mechanisms.processing.integratormechanism import IntegratorMechanism
from psyneulink.core.components.mechanisms.processing.processingmechanism import ProcessingMechanism
from psyneulink.core.components.mechanisms.processing.transfermechanism import TRANSFER_OUTPUT, TransferMechanism
from psyneulink.core.components.projections.pathway.mappingprojection import MappingProjection
from psyneulink.core.components.states.inputstate import InputState
from psyneulink.core.compositions.composition import Composition, CompositionError
from psyneulink.core.compositions.pathwaycomposition import PathwayComposition
from psyneulink.core.compositions.systemcomposition import SystemComposition
from psyneulink.core.globals.keywords import HARD_CLAMP, INPUT_STATE, NAME, NO_CLAMP, PULSE_CLAMP, SOFT_CLAMP
from psyneulink.core.globals.utilities import CNodeRole
from psyneulink.core.scheduling.condition import AfterNCalls, EveryNPasses
from psyneulink.core.scheduling.condition import EveryNCalls
from psyneulink.core.scheduling.scheduler import Scheduler
from psyneulink.core.scheduling.time import TimeScale
from psyneulink.library.components.mechanisms.processing.transfer.recurrenttransfermechanism import RecurrentTransferMechanism

class TestExecuteCIM:

    def test_identity_function(self):

        I = Identity()

        output = I.execute(2.0)
        assert output == 2.0

        output = I.execute([1.0, 2.0,3.0])
        assert np.allclose([1.0, 2.0,3.0], output)

        output = I.execute([[1.0, 2.0], [3.0]])

        assert np.allclose([1.0, 2.0], output[0])
        assert np.allclose([3.0], output[1])

    def test_standalone_CIM(self):

        cim = CompositionInterfaceMechanism()
        cim.execute(2.0)
        assert np.allclose(cim.value, [2.0])

    def test_assign_value(self):
        cim = CompositionInterfaceMechanism()
        cim.instance_defaults.variable = [2.0]
        cim.execute()
        assert np.allclose(cim.value, [2.0])

    def test_standalone_CIM_multiple_input_states(self):

        cim = CompositionInterfaceMechanism(default_variable=[[0.0], [0.0], [0.0]])
        cim.execute([[1.0], [2.0], [3.0]])
        assert np.allclose(cim.value, [[1.0], [2.0], [3.0]])

    def test_standalone_processing_multiple_input_states(self):

        processing_mech = ProcessingMechanism(default_variable=[[0.0], [0.0], [0.0]])
        processing_mech.execute([[1.0], [2.0], [3.0]])
        assert np.allclose(processing_mech.value, [[1.0], [2.0], [3.0]])


    def test_one_input_state_one_output_state(self):

        comp = Composition()

        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=2.0))

        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=3.0))

        comp.add_c_node(A)
        comp.add_c_node(B)

        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)

        comp._analyze_graph()

        inputs_dict = {
            A: [[5.]],
        }
        sched = Scheduler(composition=comp)
        output = comp.run(
            inputs=inputs_dict,
            scheduler_processing=sched
        )

        assert np.allclose([30], output)

    def test_two_input_states_two_output_states(self):

        comp = Composition()

        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=2.0))

        B = TransferMechanism(name="composition-pytests-B",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=3.0))

        comp.add_c_node(A)
        comp.add_c_node(B)

        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp.add_projection(MappingProjection(sender=A.output_states[1], receiver=B.input_states[1]), A, B)

        comp._analyze_graph()
        inputs_dict = {
            A: [[5.], [6.]],
        }
        sched = Scheduler(composition=comp)
        output = comp.run(
            inputs=inputs_dict,
            scheduler_processing=sched
        )

        assert np.allclose([[30.], [36.]], output)


        # assert np.allclose([30.], comp.output_CIM.output_states[1].value)
        # assert np.allclose([36.], comp.output_CIM.output_states[2].value)

class TestConnectCompositionsViaCIMS:

    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm)])
    def test_connect_compositions_with_simple_states(self, mode):

        comp1 = Composition(name="first_composition")

        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=2.0))

        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=3.0))

        comp1.add_c_node(A)
        comp1.add_c_node(B)

        comp1.add_projection(MappingProjection(sender=A, receiver=B), A, B)

        comp1._analyze_graph()
        inputs_dict = {
            A: [[5.]],
        }


        sched = Scheduler(composition=comp1)

        comp2 = Composition(name="second_composition")

        A2 = TransferMechanism(name="composition-pytests-A2",
                              function=Linear(slope=2.0))

        B2 = TransferMechanism(name="composition-pytests-B2",
                              function=Linear(slope=3.0))

        comp2.add_c_node(A2)
        comp2.add_c_node(B2)

        comp2.add_projection(MappingProjection(sender=A2, receiver=B2), A2, B2)

        comp2._analyze_graph()
        sched = Scheduler(composition=comp2)

        comp3 = Composition(name="outer_composition")
        comp3.add_c_node(comp1)
        comp3.add_c_node(comp2)
        comp3.add_projection(MappingProjection(), comp1, comp2)

        # comp1:
        # input = 5.0
        # mechA: 2.0*5.0 = 10.0
        # mechB: 3.0*10.0 = 30.0
        # output = 30.0

        # comp2:
        # input = 30.0
        # mechA2: 2.0*30.0 = 60.0
        # mechB2: 3.0*60.0 = 180.0
        # output = 180.0

        # comp3:
        # input = 5.0
        # output = 180.0
        res = comp3.run(inputs={comp1: [[5.]]}, bin_execute=mode)
        assert np.allclose(res, [[[180.0]]])
        if mode == 'Python':
            assert np.allclose(comp1.output_state.parameters.value.get(comp3), [30.0])
            assert np.allclose(comp2.output_state.parameters.value.get(comp3), [180.0])
            assert np.allclose(comp3.output_state.parameters.value.get(comp3), [180.0])

    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm)])
    def test_connect_compositions_with_complicated_states(self, mode):

        inner_composition_1 = Composition(name="inner_composition_1")

        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=2.0))

        B = TransferMechanism(name="composition-pytests-B",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=3.0))

        inner_composition_1.add_c_node(A)
        inner_composition_1.add_c_node(B)

        inner_composition_1.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inner_composition_1.add_projection(MappingProjection(sender=A.output_states[1], receiver=B.input_states[1]), A,
                                           B)

        inner_composition_1._analyze_graph()

        inner_composition_2 = Composition(name="inner_composition_2")

        A2 = TransferMechanism(name="composition-pytests-A2",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=2.0))

        B2 = TransferMechanism(name="composition-pytests-B2",
                              default_variable=[[0.0], [0.0]],
                              function=Linear(slope=3.0))

        inner_composition_2.add_c_node(A2)
        inner_composition_2.add_c_node(B2)

        inner_composition_2.add_projection(MappingProjection(sender=A2, receiver=B2), A2, B2)
        inner_composition_2.add_projection(MappingProjection(sender=A2.output_states[1], receiver=B2.input_states[1]),
                                           A2, B2)

        inner_composition_2._analyze_graph()

        outer_composition = Composition(name="outer_composition")

        outer_composition.add_c_node(inner_composition_1)
        outer_composition.add_c_node(inner_composition_2)

        outer_composition.add_projection(projection=MappingProjection(), sender=inner_composition_1,
                                         receiver=inner_composition_2)
        outer_composition.add_projection(
            projection=MappingProjection(sender=inner_composition_1.output_CIM.output_states[1],
                                         receiver=inner_composition_2.input_CIM.input_states[1]),
            sender=inner_composition_1, receiver=inner_composition_2)

        sched = Scheduler(composition=outer_composition)
        outer_composition._analyze_graph()
        output = outer_composition.run(
            inputs={inner_composition_1: [[[5.0], [50.0]]]},
            scheduler_processing=sched,
            bin_execute=mode
        )

        assert np.allclose(output, [[[180.], [1800.]]])
        if mode == 'Python':
            assert np.allclose(inner_composition_1.get_output_values(outer_composition), [[30.], [300.]])
            assert np.allclose(inner_composition_2.get_output_values(outer_composition), [[180.], [1800.]])
            assert np.allclose(outer_composition.get_output_values(outer_composition), [[180.], [1800.]])

    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm)])
    def test_compositions_as_origin_nodes(self, mode):

        inner_composition_1 = Composition(name="inner_composition_1")

        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=0.5))

        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=2.0))

        C = TransferMechanism(name="composition-pytests-C",
                              function=Linear(slope=3.0))

        inner_composition_1.add_c_node(A)
        inner_composition_1.add_c_node(B)
        inner_composition_1.add_c_node(C)

        inner_composition_1.add_projection(MappingProjection(), A, C)
        inner_composition_1.add_projection(MappingProjection(), B, C)

        inner_composition_1._analyze_graph()

        inner_composition_2 = Composition(name="inner_composition_2")

        A2 = TransferMechanism(name="composition-pytests-A2",
                               function=Linear(slope=0.25))

        B2 = TransferMechanism(name="composition-pytests-B2",
                               function=Linear(slope=1.0))

        inner_composition_2.add_c_node(A2)
        inner_composition_2.add_c_node(B2)

        inner_composition_2.add_projection(MappingProjection(), A2, B2)

        inner_composition_2._analyze_graph()

        mechanism_d = TransferMechanism(name="composition-pytests-D",
                                        function=Linear(slope=3.0))

        outer_composition = Composition(name="outer_composition")

        outer_composition.add_c_node(inner_composition_1)
        outer_composition.add_c_node(inner_composition_2)
        outer_composition.add_c_node(mechanism_d)

        outer_composition.add_projection(projection=MappingProjection(), sender=inner_composition_1,
                                         receiver=mechanism_d)
        outer_composition.add_projection(projection=MappingProjection(), sender=inner_composition_2,
                                         receiver=mechanism_d)

        sched = Scheduler(composition=outer_composition)
        outer_composition._analyze_graph()

        # FIX: order of input states on inner composition 1 is not stable
        output = outer_composition.run(
            inputs={
                # inner_composition_1: [[2.0], [1.0]],
                inner_composition_1: {A: [2.0],
                                          B: [1.0]},
                inner_composition_2: [[12.0]]},
            scheduler_processing=sched,
            bin_execute=mode
        )
        assert np.allclose(output, [[[36.]]])

        if mode == 'Python':
            assert np.allclose(A.get_output_values(outer_composition), [[1.0]])
            assert np.allclose(B.get_output_values(outer_composition), [[2.0]])
            assert np.allclose(C.get_output_values(outer_composition), [[9.0]])
            assert np.allclose(A2.get_output_values(outer_composition), [[3.0]])
            assert np.allclose(B2.get_output_values(outer_composition), [[3.0]])
            assert np.allclose(inner_composition_1.get_output_values(outer_composition), [[9.0]])
            assert np.allclose(inner_composition_2.get_output_values(outer_composition), [[3.0]])
            assert np.allclose(mechanism_d.get_output_values(outer_composition), [[36.0]])
            assert np.allclose(outer_composition.get_output_values(outer_composition), [[36.0]])

    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm)])
    def test_compositions_as_origin_nodes_multiple_trials(self, mode):

        inner_composition_1 = Composition(name="inner_composition_1")

        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=0.5))

        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=2.0))

        C = TransferMechanism(name="composition-pytests-C",
                              function=Linear(slope=3.0))

        inner_composition_1.add_c_node(A)
        inner_composition_1.add_c_node(B)
        inner_composition_1.add_c_node(C)

        inner_composition_1.add_projection(MappingProjection(), A, C)
        inner_composition_1.add_projection(MappingProjection(), B, C)

        inner_composition_1._analyze_graph()

        inner_composition_2 = Composition(name="inner_composition_2")

        A2 = TransferMechanism(name="composition-pytests-A2",
                               function=Linear(slope=0.25))

        B2 = TransferMechanism(name="composition-pytests-B2",
                               function=Linear(slope=1.0))

        inner_composition_2.add_c_node(A2)
        inner_composition_2.add_c_node(B2)

        inner_composition_2.add_projection(MappingProjection(), A2, B2)

        inner_composition_2._analyze_graph()

        mechanism_d = TransferMechanism(name="composition-pytests-D",
                                        function=Linear(slope=3.0))

        outer_composition = Composition(name="outer_composition")

        outer_composition.add_c_node(inner_composition_1)
        outer_composition.add_c_node(inner_composition_2)
        outer_composition.add_c_node(mechanism_d)

        outer_composition.add_projection(projection=MappingProjection(), sender=inner_composition_1,
                                         receiver=mechanism_d)
        outer_composition.add_projection(projection=MappingProjection(), sender=inner_composition_2,
                                         receiver=mechanism_d)

        sched = Scheduler(composition=outer_composition)
        outer_composition._analyze_graph()

        # FIX: order of input states on inner composition 1 is not stable
        output = outer_composition.run(
            inputs={
                inner_composition_1: {A: [[2.0], [1.5], [2.5]],
                                      B: [[1.0], [1.5], [1.5]]},
                inner_composition_2: [[12.0], [11.5], [12.5]]},
            scheduler_processing=sched,
            bin_execute=mode
        )
        print(output)
        # trial 0:
        # inner composition 1 = (0.5*2.0 + 2.0*1.0) * 3.0 = 9.0
        # inner composition 2 = 0.25*12.0 = 3.0
        # outer composition = (3.0 + 9.0) * 3.0 = 36.0

        # trial 1:
        # inner composition 1 = (0.5*1.5 + 2.0*1.5) * 3.0 = 11.25
        # inner composition 2 = 0.25*11.5 = 2.875
        # outer composition = (2.875 + 11.25) * 3.0 = 42.375

        # trial 2:
        # inner composition 1 = (0.5*2.5 + 2.0*1.5) * 3.0 = 12.75
        # inner composition 2 = 0.25*12.5 = 3.125
        # outer composition = (3.125 + 12.75) * 3.0 = 47.625

        assert np.allclose(output, [[np.array([36.])],
                                    [np.array([42.375])],
                                    [np.array([47.625])]])

    def test_input_specification_multiple_nested_compositions(self):

        # level_0 composition --------------------------------- innermost composition
        level_0 = Composition(name="level_0")

        A0 = TransferMechanism(name="composition-pytests-A0",
                               default_variable=[[0.], [0.]],
                               function=Linear(slope=1.))
        B0 = TransferMechanism(name="composition-pytests-B0",
                               function=Linear(slope=2.))

        level_0.add_c_node(A0)
        level_0.add_c_node(B0)
        level_0.add_projection(MappingProjection(), A0, B0)
        level_0.add_projection(MappingProjection(sender=A0.output_states[1], receiver=B0), A0, B0)
        level_0._analyze_graph()

        # level_1 composition ---------------------------------
        level_1 = Composition(name="level_1")

        A1 = TransferMechanism(name="composition-pytests-A1",
                              function=Linear(slope=1.))
        B1 = TransferMechanism(name="composition-pytests-B1",
                              function=Linear(slope=2.))

        level_1.add_c_node(level_0)
        level_1.add_c_node(A1)
        level_1.add_c_node(B1)
        level_1.add_projection(MappingProjection(), level_0, B1)
        level_1.add_projection(MappingProjection(), A1, B1)
        level_1._analyze_graph()

        # level_2 composition --------------------------------- outermost composition
        level_2 = Composition(name="level_2")

        A2 = TransferMechanism(name="composition-pytests-A2",
                               size=2,
                               function=Linear(slope=1.))
        B2 = TransferMechanism(name="composition-pytests-B2",
                               function=Linear(slope=2.))

        level_2.add_c_node(level_1)
        level_2.add_c_node(A2)
        level_2.add_c_node(B2)
        level_2.add_projection(MappingProjection(), level_1, B2)
        level_2.add_projection(MappingProjection(), A2, B2)
        level_2._analyze_graph()

        sched = Scheduler(composition=level_2)

        # FIX: order of input states in each inner composition (level_0 and level_1)
        level_2.run(inputs={A2: [[1.0, 2.0]],
                            level_1: {A1: [[1.0]],
                                      level_0: {A0: [[1.0], [2.0]]}}},
                    scheduler_processing=sched)

        # level_0 output = 2.0 * (1.0 + 2.0) = 6.0
        assert np.allclose(level_0.get_output_values(level_2), [6.0])
        # level_1 output = 2.0 * (1.0 + 6.0) = 14.0
        assert np.allclose(level_1.get_output_values(level_2), [14.0])
        # level_2 output = 2.0 * (1.0 + 2.0 + 14.0) = 34.0
        assert np.allclose(level_2.get_output_values(level_2), [34.0])


class TestInputCIMOutputStateToOriginOneToMany:

    def test_one_to_two(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(C)

        comp.external_input_sources = {C: A}

        comp.run(inputs={A: [[1.23]]})

        assert np.allclose(A.parameters.value.get(comp), [[1.23]])
        assert np.allclose(B.parameters.value.get(comp), [[1.23]])
        assert np.allclose(C.parameters.value.get(comp), [[1.23]])

    def test_non_origin_receiver(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(C)

        comp.external_input_sources = {C: A,
                                       B: A}

        comp.run(inputs={A: [[1.23]]})

        assert np.allclose(A.parameters.value.get(comp), [[1.23]])
        assert np.allclose(B.parameters.value.get(comp), [[2.46]])
        assert np.allclose(C.parameters.value.get(comp), [[1.23]])

    def test_incorrect_origin_input_source_spec(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(C)

        comp.external_input_sources = {C: B}

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs={A: [[1.23]]})
        assert "External input source" in str(error_text) and "specified for C is not valid" in str(error_text)


    def test_origin_input_source_true_no_input(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C',
                                default_variable=[[4.56]])

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(C)

        comp.external_input_sources = {C: True}

        comp.run(inputs={A: [[1.23]]})

        assert np.allclose(A.parameters.value.get(comp), [[1.23]])
        assert np.allclose(B.parameters.value.get(comp), [[1.23]])
        assert np.allclose(C.parameters.value.get(comp), [[4.56]])

    def test_mix_and_match_input_sources(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])
        C = ProcessingMechanism(name='C',
                                default_variable=[[0.], [0.], [0.]])

        input_dict = {A: [[2.0]],
                      B: [[3.0], [1.0]]}

        external_input_sources = {C: [B.input_states[1],
                                    A,
                                    B.input_states[0]]}

        comp = Composition(name="comp")

        comp.add_c_node(A)
        comp.add_c_node(B)
        comp.add_c_node(C)

        comp.external_input_sources = external_input_sources

        comp.run(inputs=input_dict)

        assert np.allclose(A.parameters.value.get(comp), [[2.]])
        assert np.allclose(B.parameters.value.get(comp), [[3.], [1.]])
        assert np.allclose(C.parameters.value.get(comp), [[1.], [2.], [3.]])

    def test_mix_and_match_input_sources_invalid_shape(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])
        C = ProcessingMechanism(name='C',
                                default_variable=[[0.], [0.], [0.], [0.]])

        input_dict = {A: [[2.0]],
                      B: [[3.0], [1.0]]}

        external_input_sources = {C: [B.input_states[1],
                                    A,
                                    B.input_states[0]]}

        comp = Composition(name="comp")

        comp.add_c_node(A)
        comp.add_c_node(B)
        comp.add_c_node(C)

        comp.external_input_sources = external_input_sources

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs=input_dict)
        assert "has an incompatible number of external input states" in str(error_text.value)

    def test_mix_and_match_input_sources_invalid_source(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])
        C = ProcessingMechanism(name='C',
                                default_variable=[[0.], [0.], [0.]])
        D = ProcessingMechanism(name='D')

        input_dict = {A: [[2.0]],
                      B: [[3.0], [1.0]]}

        external_input_sources = {C: [B.input_states[1],
                                    D,
                                    B.input_states[0]]}

        comp = Composition(name="comp")

        comp.add_c_node(A)
        comp.add_c_node(B)
        comp.add_linear_processing_pathway([C, D])

        comp.external_input_sources = external_input_sources

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs=input_dict)
        assert "source which is not an origin node or an InputState of an origin node" in str(error_text.value)

    def test_input_sources_invalid_origin_source(self):
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])
        C = ProcessingMechanism(name='C',
                                default_variable=[[0.], [0.], [0.]])
        D = ProcessingMechanism(name='D')

        input_dict = {A: [[2.0]],
                      B: [[3.0], [1.0]]}

        external_input_sources = {C: [B.input_states[1],
                                    D,
                                    B.input_states[0]],
                                D: [C.input_states[0]]}

        comp = Composition(name="comp")

        comp.add_c_node(A)
        comp.add_c_node(B)
        comp.add_c_node(C)
        comp.add_c_node(D)

        comp.external_input_sources = external_input_sources

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs=input_dict)
        assert "already borrowing input from yet another origin node" in str(error_text.value)

    def test_non_origin_partial_input_spec(self):
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])

        comp.external_input_sources = {B: [None, A]}
        comp.run(inputs={A: [[1.23]]})
        assert np.allclose(B.get_input_values(comp), [[2.46], [1.23]])

    def test_non_origin_too_many_input_states(self):
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.]])
        C = ProcessingMechanism(name='C')

        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(C)

        comp.external_input_sources = {B: [A, C]}
        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs={A: [[1.23]],
                             C: [[4.0]]})
        assert "too many external input states" in str(error_text.value)

    def test_origin_partial_input_spec(self):
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])

        comp = Composition(name='comp')

        comp.add_c_node(A)
        comp.add_c_node(B)

        comp.external_input_sources = {B: [None, A]}

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs={A: [[1.23]]})
        assert "incompatible number of external input states" in str(error_text.value)

    def test_specify_external_input_sources_on_mechanism_nonorigin(self):
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.], [0.]])
        comp = Composition(name='comp')

        comp.add_linear_processing_pathway([A, B])
        comp.add_c_node(B, external_input_source=[None, A])
        comp.run(inputs={A: [[1.23]]})
        assert np.allclose(B.get_input_values(comp), [[2.46], [1.23]])

    def test_specify_external_input_sources_on_mechanism_origin(self):
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                default_variable=[[0.]])
        comp = Composition(name='comp')

        comp.add_c_node(A)
        comp.add_c_node(B, external_input_source=A)

        comp.run(inputs={A: [[1.23]]})
        assert np.allclose(B.get_input_values(comp), [[1.23]])

    def test_external_input_sources_ALL(self):
        from psyneulink.core.globals.keywords import ALL
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')
        D = ProcessingMechanism(name='D',
                                default_variable=[[0.], [0.]])
        comp = Composition(name='comp')

        comp.add_c_node(A)
        comp.add_c_node(B, external_input_source=A)
        comp.add_c_node(C)
        comp.add_c_node(D, external_input_source=ALL)
        comp.add_linear_processing_pathway([C, D])

        comp.run(inputs={A: [[1.23]],
                         C: [[4.0]]})
        assert np.allclose(D.get_input_values(comp), [[5.23], [4.0]])



class TestInputSpec:

    def test_valid_mismatched_input_lens(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")

        comp = Composition(name="COMP")

        comp.add_linear_processing_pathway([A, C])
        comp.add_linear_processing_pathway([B, C])

        inputs_to_A = [[1.0]]                           # same (1.0) on every trial
        inputs_to_B = [[1.0], [2.0], [3.0], [4.0]]      # increment on every trial

        results_A = []
        results_B = []
        results_C = []

        def call_after_trial():
            results_A.append(A.parameters.value.get(comp))
            results_B.append(B.parameters.value.get(comp))
            results_C.append(C.parameters.value.get(comp))

        comp.run(inputs={A: inputs_to_A,
                         B: inputs_to_B},
                 call_after_trial=call_after_trial)

        assert np.allclose(results_A, [[[1.0]], [[1.0]], [[1.0]], [[1.0]]])
        assert np.allclose(results_B, [[[1.0]], [[2.0]], [[3.0]], [[4.0]]])
        assert np.allclose(results_C, [[[2.0]], [[3.0]], [[4.0]], [[5.0]]])

    def test_valid_only_one_node_provides_input_spec(self):
        A = ProcessingMechanism(name="A",
                                default_variable=[[1.5]])   # default variable will be used as input to this origin node
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")

        comp = Composition(name="COMP")

        comp.add_linear_processing_pathway([A, C])
        comp.add_linear_processing_pathway([B, C])

        inputs_to_B = [[1.0], [2.0], [3.0], [4.0]]      # increment on every trial

        results_A = []
        results_B = []
        results_C = []

        def call_after_trial():
            results_A.append(A.parameters.value.get(comp))
            results_B.append(B.parameters.value.get(comp))
            results_C.append(C.parameters.value.get(comp))

        comp.run(inputs={B: inputs_to_B},
                 call_after_trial=call_after_trial)

        assert np.allclose(results_A, [[[1.5]], [[1.5]], [[1.5]], [[1.5]]])
        assert np.allclose(results_B, [[[1.0]], [[2.0]], [[3.0]], [[4.0]]])
        assert np.allclose(results_C, [[[2.5]], [[3.5]], [[4.5]], [[5.5]]])

    def test_invalid_mismatched_input_lens(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")

        comp = Composition(name="COMP")

        comp.add_linear_processing_pathway([A, C])
        comp.add_linear_processing_pathway([B, C])

        inputs_to_A = [[1.0], [2.0]]                    # 2 input specs
        inputs_to_B = [[1.0], [2.0], [3.0], [4.0]]      # 4 input specs

        with pytest.raises(CompositionError) as error_text:
            comp.run(inputs={A: inputs_to_A,
                             B: inputs_to_B})
        assert "input dictionary for COMP contains input specifications of different lengths" in str(error_text.value)

    def test_valid_input_float(self):
        A = ProcessingMechanism(name="A")
        comp = Composition(name="comp")
        comp.add_c_node(A)

        comp.run(inputs={A: 5.0})
        assert np.allclose(comp.results, [[5.0]])

        comp.run(inputs={A: [5.0, 10.0, 15.0]})
        assert np.allclose(comp.results, [[[5.0]], [[5.0]], [[10.0]], [[15.0]]])