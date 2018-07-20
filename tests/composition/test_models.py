import psyneulink as pnl
import numpy as np

class TestStroopModels:

    # This implements the model by Cohen, J. D., & Huston, T. A. (1994). Progress in the use of interactive
    # models for understanding attention and performance. In C. Umilta & M. Moscovitch(Eds.),
    # AttentionandperformanceXV(pp.453-456). Cam- bridge, MA: MIT Press.
    # The model aims to capute top-down effects of selective attention and the bottom-up effects of attentional capture.

    def test_cohen_huston_1994(self):

        # Define Variables -------------------------------------------------------------------------------------
        rate = 0.1  # modified from the original code from 0.01 to 0.1
        inhibition = -2.0  # lateral inhibition
        bias = 4.0  # bias is positive since Logistic equation has - sing already implemented
        threshold = 0.55  # modified from original code from 0.6 to 0.55 because incongruent condition won't reach 0.6
        settle_trials = 50  # cycles until model settles

        # Create mechanisms ------------------------------------------------------------------------------------

        #   Linear input units, colors: ('red', 'green'), words: ('RED','GREEN')

        colors_input_layer = pnl.TransferMechanism(
            size=3,
            function=pnl.Linear,
            name='COLORS_INPUT'
        )

        words_input_layer = pnl.TransferMechanism(
            size=3,
            function=pnl.Linear,
            name='WORDS_INPUT'
        )

        task_input_layer = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='TASK_INPUT'
        )

        #   Task layer, tasks: ('name the color', 'read the word')
        task_layer = pnl.RecurrentTransferMechanism(
            size=2,
            function=pnl.Logistic(),
            hetero=-2,
            integrator_mode=True,
            integration_rate=0.1,
            name='TASK'
        )

        #   Hidden layer units, colors: ('red','green') words: ('RED','GREEN')
        colors_hidden_layer = pnl.RecurrentTransferMechanism(
            size=3,
            function=pnl.Logistic(bias=4.0),
            integrator_mode=True,
            hetero=-2.0,
            # noise=pnl.NormalDist(mean=0.0, standard_dev=.0).function,
            integration_rate=0.1,  # cohen-huston text says 0.01
            name='COLORS HIDDEN'
        )

        words_hidden_layer = pnl.RecurrentTransferMechanism(
            size=3,
            function=pnl.Logistic(bias=4.0),
            hetero=-2,
            integrator_mode=True,
            # noise=pnl.NormalDist(mean=0.0, standard_dev=.05).function,
            integration_rate=0.1,
            name='WORDS HIDDEN'
        )
        #   Response layer, responses: ('red', 'green'): RecurrentTransferMechanism for self inhibition matrix
        response_layer = pnl.RecurrentTransferMechanism(
            size=2,
            function=pnl.Logistic(),
            hetero=-2.0,
            integrator_mode=True,
            integration_rate=0.1,
            name='RESPONSE'
        )
        # Connect mechanisms --------------------------------------------------------------------------------------------------
        # (note that response layer projections are set to all zero first for initialization

        color_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        word_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        task_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0],
                [0.0, 1.0]
            ])
        )

        color_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [4.0, 0.0],
                [4.0, 0.0],
                [4.0, 0.0]
            ])
        )

        task_color_weights = pnl.MappingProjection(
            matrix=np.array([
                [4.0, 4.0, 4.0],
                [0.0, 0.0, 0.0]
            ])
        )

        word_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 4.0],
                [0.0, 4.0],
                [0.0, 4.0]
            ])
        )

        task_word_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [4.0, 4.0, 4.0]
            ])
        )

        response_color_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        response_word_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        color_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.5, 0.0],
                [0.0, 1.5],
                [0.0, 0.0]
            ])
        )
        word_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [2.5, 0.0],
                [0.0, 2.5],
                [0.0, 0.0]
            ])
        )
        bidirectional_stroop = pnl.Composition(name="bidirectional_stroop")

        color_response_pathway = [colors_input_layer,
                                  color_input_weights,
                                  colors_hidden_layer,
                                  color_response_weights,
                                  response_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=color_response_pathway)

        color_response_pathway_2 = [response_layer,
                                    response_color_weights,
                                    colors_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=color_response_pathway_2)


        word_response_pathway = [words_input_layer,
                                 word_input_weights,
                                 words_hidden_layer,
                                 word_response_weights,
                                 response_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=word_response_pathway)

        word_response_pathway_2 = [response_layer,
                                   response_word_weights,
                                   words_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=word_response_pathway_2)


        task_color_response_pathway = [task_input_layer,
                                       task_input_weights,
                                       task_layer,
                                       task_color_weights,
                                       colors_hidden_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_color_response_pathway)

        task_color_response_pathway_2 = [colors_hidden_layer,
                                         color_task_weights,
                                         task_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_color_response_pathway_2)

        task_word_response_pathway = [task_input_layer,
                                      task_layer,
                                      task_word_weights,
                                      words_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=task_word_response_pathway)

        task_word_response_pathway_2 = [words_hidden_layer,
                                        word_task_weights,
                                        task_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_word_response_pathway_2)
        bidirectional_stroop.add_required_c_node_role(task_layer, pnl.CNodeRole.TERMINAL)
        bidirectional_stroop._analyze_graph()

        input_dict = {colors_input_layer: [0, 0, 0],
                      words_input_layer: [0, 0, 0],
                      task_input_layer: [0, 1]}

        bidirectional_stroop.run(inputs=input_dict)
        print(bidirectional_stroop.get_c_nodes_by_role(pnl.CNodeRole.TERMINAL))
        print(bidirectional_stroop.output_values)

    def test_DDM(self):
        myMechanism = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=(1.0),
                threshold=(10.0),
                starting_point=0.0,
            ),
            name='My_DDM',
        )

        myMechanism_2 = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=2.0,
                threshold=20.0),
            name='My_DDM_2'
        )

        myMechanism_3 = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=3.0,
                threshold=30.0
            ),
            name='My_DDM_3',
        )

        z = pnl.Composition()
        z.add_linear_processing_pathway([myMechanism,
                                        pnl.MappingProjection(matrix=pnl.IDENTITY_MATRIX),
                                        myMechanism_2,
                                         pnl.MappingProjection(matrix=pnl.FULL_CONNECTIVITY_MATRIX),
                                        myMechanism_3])

        result = z.run(inputs={myMechanism: [[40]]})[0][0]

        expected_output = [
            (myMechanism.input_states[0].value, np.array([40.])),
            (myMechanism.output_states[0].value, np.array([10.])),
            (myMechanism_2.input_states[0].value, np.array([10.])),
            (myMechanism_2.output_states[0].value, np.array([20.])),
            (myMechanism_3.input_states[0].value, np.array([20.])),
            (myMechanism_3.output_states[0].value, np.array([30.])),
            (result, np.array([30.])),
        ]

        for i in range(len(expected_output)):
            val, expected = expected_output[i]
            # setting absolute tolerance to be in accordance with reference_output precision
            # if you do not specify, assert_allcose will use a relative tolerance of 1e-07,
            # which WILL FAIL unless you gather higher precision values to use as reference
            np.testing.assert_allclose(val, expected, atol=1e-08, err_msg='Failed on expected_output[{0}]'.format(i))
