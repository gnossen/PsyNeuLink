# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.


# **************************************  OptimizationControlMechanism *************************************************

"""

Overview
--------

OptimizationControlMechanism is an abstract class for defining subclasses of `ControlMechanism <ControlMechanism>` that
use an `OptimizationFunction` to find an `allocation_policy <ControlMechanism.allocation_policy>` that maximizes the
Expected Value of Control (EVC) for a given state.  The `OptimizationFunction` uses the OptimizationControlMechanism's
`evaluation_function <OptimizationControlMechanism.evaluation_function>` to evaluate the EVC for samples of
`allocation_policy <ControlMechanism.allocation_policy>`, and retuns the one that yields the greatest EVC.

.. _OptimizationControlMechanism_EVC:

**Expected Value of Control**

All OptimizationControlMechanisms compute the `Expected Value of Control (EVC)
<https://www.ncbi.nlm.nih.gov/pubmed/23889930>`_ --  a cost-benefit analysis that weighs the `costs
<ControlMechanism.costs>` of the `control_signals <ControlMechanism.control_signals>` for a given `allocation_policy
<ControlMechanism.allocation_policy>` against the `outcome <ControlMechanism.outcome>` expected to result from that
policy.  The EVC for an `allocation_policy <ControlMechanism.allocation_policy>` is computed by the
OptimizationControlMechanism's `evaluation_function <OptimizationControlMechanism.evaluation_function>`, using its
`compute_EVC <OptimizationControlMechanism.compute_EVC>` method and some combination of the `costs
<ControlMechanism.costs>` associated with the `allocation_policy <ControlMechanism.allocation_policy>` and the current
state, depending on the particular subclass.  The table `below <OptimizationControlMechanism_Examples>` lists different
types of OptimizationControlMechanisms, followed by a list of models that implement examples of these.  There are two
broad types of OptimizationControlMechanisms: "model-free" and "model-based."

.. _OptimizationControlMechanism_Model_Free:

**Model-Free OptimizationControlMechanisms**

These use a `learning_function <OptimizationControlMechanism_Learning_Function>` to generate a set of
`prediction_weights <OptimizationControlMechanism.prediction_weights>` that can predict, for the current state,
the net outcome of processing for different allocation_policies. The current state, represented in
`current_state <OptimizationControlMechanism.current_state>`, may include information about the inputs or
outputs of other `Mechanisms`, the current  `allocation_policy <ControlMechanism.allocation_policy>`, and/or its
associated `costs <ControlMechanism.costs>`.  The net outcome is represented in `net_outcome
<ControlMechanism.net_outcome>`, and is generated by the Mechanism's `compute_net_outcome_function
<ControlMechanism.compute_net_outome_function>` which is usually the `outcome <ControlMechanism.outcome>` for a given
trial minus the `costs <ControlMechanism.costs>` of the `allocation_policy <ControlMechanism.allocation_policy>` for
that trial. In each trial, `learning_function <OptimizationControlMechanism.learning_function>` updates the
`prediction_weights <OptimizationControlMechanism.prediction_weights>` based on the `current_state
<OptimizationControlMechanism.current_state>` and the `net_outcome <ControlMechanism.net_outcome>` for the previous
trial. The updated weights are then used by the `evaluation_function <OptimizationControlMechanism.evaluation_function>`
to predict the EVC for the current `current_state <OptimizationControlMechanism.current_state>` and a given
`allocation_policy <ControlMechanism.allocation_policy>`.  The OptimizationControlMechainsm's `function
<OptimizationControlMechanism.function>` uses this to find the `allocation_policy <ControlMechanism.allocation_policy>`
that yields the *best* EVC for the current state, and then implements that for the current `trial` of execution.

.. _OptimizationControlMechanism_Model_Based:

**Model-Based OptimizationControlMechanisms**

These are called `controllers <Composition.controllers>`, and are implemented using the `ModelBasedControlMechanism`
subclass.  This has a `run_simulation <ModelBasedControlMechanism.run_simulation>` method, that is used by the
`evaluation_function <OptimizationControlMechanism.evaluation_function>` to empirically determine the `EVC
<OptimizationControlMechanism_EVC>` for a given `allocation_policy <ControlMechanism.allocation_policy>` by running one
or more simulations of the `Composition` to which the ModelBasedControlMechanism belongs. The `learning_function
<OptimizationControlMechanism.learning_function>` may or may not be used in combination with the `run_simulation
<ModelBasedControlMechanism.run_simulation>` method (e.g., for efficiency, or to differentially manage
elements of the `current_state <OptimizationControlMechanism.current_state>` that influence `outcome
<ControlMechanism.outcome>` and/or `costs <ControlMechanism.costs>` in different ways). Like model-free
OptimizationControlMechanisms, their `function <OptimizationControlMechanism.function>` uses the `evaluation_function
<OptimizationControlMechanism.evaluation_function>` to identify the `allocation_policy
<ControlMechanism.allocation_policy>` that yields the greatest EVC, and then implements that for the next `trial`
of execution.


.. _OptimizationControlMechanism_Creation:

Creating an OptimizationControlMechanism
----------------------------------------

An OptimizationControlMechanism can be created in the same was as any `ControlMechanism <ControlMechanism>`.  The only
constraint is that an `OptimizationFunction` (or a function that has the same structure as one) must be specified as
the **function** argument of its constructor.  In addition, a **learning_function** can be specified (see `below
<OptimizationControlMechanism_Learning_Function>`)

.. _OptimizationControlMechanism_Structure:

Structure
---------

An OptimizationControlMechanism has the same structure as a `ControlMechanism`, including a `Projection <Projection>`
to its *OUTCOME* InputState from its `objective_mechanism <ControlMechanism.objective_mechanism>`.  In
addition to its primary `function <OptimizationControlMechanism.function>`, it may also have a `learning_function
<OptimizationControlMechanism.learning_function>`, both of which are described below.

.. _OptimizationControlMechanism_ObjectiveMechanism:

ObjectiveMechanism
^^^^^^^^^^^^^^^^^^

Like any `ControlMechanism`, an OptimizationControlMechanism has an associated `objective_mechanism
<ControlMechanism.objective_mechanism>` that is used to evaluate the outcome of processing for a given trial and pass
the result to the OptimizationControlMechanism, which it places in its `outcome <OptimizationControlMechanism.outcome>`
attribute.  This is used by its `evaluation_function <OptimizationControlMechanism.evaluation_function>`, together with
the `costs <ControlMechanism.costs>` of its `control_signals <ControlMechanism.control_signals>`, to carry out the
`EVC <OptimizationControlMechanism_EVC>` calculation.

.. note::
    The `objective_mechanism is distinct from, and should not be confused with the OptimizationControlMechanism's
    `evaluation_function <OptimizationControlMechanism.evaluation_function>`, which as the `objective_function
    <OptimizationFunction.objective_function>` parameter of its `OptimizationFunction`.  The `objective_mechanism
    <OptimizationControlMechanism.objective_mechanism>` evaluates the outcome of processing without taking into
    account the `costs <ControlMechanism.costs>` of the OptimizationControlMechanism's `control_signals
    <ControlMechanism.control_signals>`, whereas the its `evaluation_function
    <ControlMechanismOptimizationControlMechanism.evaluation_function>` takes these into account in calculating the
    `EVC <OptimizationControlMechanism_EVC>`.

.. _OptimizationControlMechanism_Learning_Function:

Learning Function
^^^^^^^^^^^^^^^^^

An OptimizationControlMechanism may have a `learning_function <OptimizationControlMechanism.learning_function>` used
to learn a set of `prediction_weights <<OptimizationControlMechanism.prediction_weights>` that can predict `net_outcome
<ControlMechanism.net_outcome>` from a `current_state <OptimizationControlMechanism.current_state>`; it is up
to the subclass of the OptimizationControlMechanism to determine the contents of `current_state
<OptimizationControlMechanism.current_state>` (which may include information from other Mechanisms, the
current `allocation_policy <ControlMechanism.allocation_policy>`, or its associated `costs
<ControlMechanism.allocation_policy>`) and how `net_outcome <ControlMechanism.net_outcome>` is computed
(defined by its `compute_net_outcome <ControlMechanism.compute_net_outcome>` function). The `learning_function
<OptimizationControlMechanism.learning_function>` takes as its first argument the `current_state
<OptimizationControlMechanism.current_state>`, and as its second argument the value of `net_oucome
<OptimizationControlMechanism.net_outcome>`. It returns an array with one weight for each element of
`current_state <OptimizationControlMechanism.current_state>`, that is assigned to `prediction_weights
<OptimizationControlMechanism.prediction_weights>`. This is can be used by the OptimizationControlMechanism's primary
`function <OptimizationControlMechanism.function>` to predict the `EVC <OptimizationControlMechanism_EVC>` for a
given `allocation_policy <ControlMechanism.allocation_policy>`, and seek the one that yields the greatest EVC
(see `below <OptimizationControlMechanism_Function>`).

.. _OptimizationControlMechanism_Function:

*Primary Function*
^^^^^^^^^^^^^^^^^^

The `function <OptimizationControlMechanism.function>` of an OptimizationControlMechanism is generally an
`OptimizationFunction`, which in turn has `objective_function <OptimizationFunction.objective_function>`,
`search_function <OptimizationFunction.search_function>` and `search_termination_function
<OptimizationFunction.search_termination_function>` methods, as well as a `search_space
<OptimizationFunction.search_space>` attribute.  The OptimizationControlMechanism must implement an
`evaluation_function <OptimizationControlMechanism.evluation_function>` that is assigned to the
`OptimizationFunction` as its `objective_function <OptimizationFunction.objective_function>` parameter.
This is used to evaluate each `allocation_policy <ControlMechanism.allocation_policy>` generated by the
`search_function <OptimizationFunction.search_function>`, and return the one that yields the greatest `EVC
<OptimizationControlMechanism_EVC>`.

The OptimizationControlMechanism may also implement `search_function <OptimizationControlMechanism.search_function>`
and `search_termination_function <OptimizationControlMechanism.search_termination_function>` methods, as well as a
`allocation_policy_search_space <OptimizationControlMechanism.allocation_policy_search_space>` attribute, that will
also  be passed as parameters to the `OptimizationFunction` when it is constructed.  Any or all of these assignments
can be overriden by specifying the relevant parameters in a constructor for the `OptimizationFunction` assigned as
the **function** argument of the OptimizationControlMechanism's constructor, as long as they are compatible with the
requirements of the OptimizationFunction and OptimizationControlMechanism.  A custom function can also be assigned as
the `function <OptimizationControlMechanism.function>` of an OptimizationControlMechanism, however it must meet the
following requirements:

.. _OptimizationControlMechanism_Custom_Funtion:

    - it must accept as its first argument and return as its result an array with the same shape as the
      OptimizationControlMechanism's `allocation_policy <ControlMechanism.allocation_policy>`.

    - it must implement a `reinitialize` method that accepts as keyword arguments **objective_function**,
      **search_function**, **search_termination_function**, and **search_space**, and implement attributes
      with corresponding names.

.. _OptimizationControlMechanism_Execution:

Execution
---------

When an OptimizationControlMechanism executes, it calls its `learning_function
<OptimizationControlMechanism.learning_function>` if it has one, to update its `prediction_weights
<OptimizationControlMechanism.prediction_weights>`. It then calls its primary `function
<OptimizationControlMechanism.function>` to find the `allocation_policy <ControlMechanism.allocation_policy>` that 
yields the greatest `EVC <OptimizationControlMechanism_EVC>`.  The `function <OptimizationControlMechanism.function>` 
does this by selecting a sample `allocation_policy <ControlMechanism.allocation_policy>` (usually using  
`search_function <OptimizationControlMechanism.search_function>` to select one from `allocation_policy_search_space
<OptimizationControlMechanism.allocation_policy_search_space>`), and evaluating the EVC for that `allocation_policy
<ControlMechanism.allocation_policy>` using the `evaluation_function <OptimizationControlMechanism.evaluation_function>`.
The latter does this either by using the current `current_state <OptimizationControlMechanism.current_state>`
and `prediction_weights <OptimizationControlMechanism.prediction_weights>` to predict the EVC (model-free
OptimizationControlMechanism), or by calling the OptimizationControlMechanism's `run_simulation
<ModelBasedControlMechanism.run_simulation>` to "empirically" generate the `outcome
<OptimizationControlMechanism.outcome>` for the `allocation_policy <ControlMechanism.allocation_policy>` and then
evaluting the EVC for the resulting `outcome <ControlMechanism.outcome>` and `costs <ControlMechanism.costs>` (
model-based OptimizationControlMechanism).  In either case, one or more allocation_policies are
evaluated, and the one that yields the greatest EVC is returned.  The values of that `allocation_policy
<ControlMechanism.allocation_policy>` are assigned as the `variables <ControlSignal.variable>` of the
OptimizationControlMechanism's `control_signals <ControlMechanism.control_signals>`.  These are used by the
`control_signals <ControlMechanism.control_signals>` to compute their `values <ControlSignal.value>`, which are used
by their `ControlProjections <ControlProjection>` to modulate the parameters they control.

.. _OptimizationControlMechanism_Examples:

Examples
--------

The table below lists `model-free <OptimizationControlMechanism_Model_Free>` and `model-based
<OptimizationControlMechanism_Model_Based>` subclasses of OptimizationControlMechanisms, that implement
different combinations of `learning_function <OptimizationControlMechanism.learning_function>` and `function
<OptimizationControlMechanism.function>`.

.. table:: **Model-Free and Model-Based OptimizationControlMechanisms**

   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |                         |     *Model-Free*     |                           *Model-Based*                                                         |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |**Functions**            |`LVOCControlMechanism`| LVOMControlMechanism | MDPControlMechanism |`EVCControlMechanism`| ParameterEstimationMechanism |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |**learning_function**    |     `BayesGLM`       |        `pymc`        |    `BeliefUpdate`   |       *None*        |           `pymc`             |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |**function** *(primary)* |`GradientOptimization`|     `GridSearch`     |       `Sample`      |    `GridSearch`     |           `Sample`           |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |       *search_function* |  *follow_gradient*   |   *traverse_grid*    | *sample_from_dist*  |   *traverse_grid*   |      *sample_from_dist*      |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |    *objective_function* |    *compute_EVC*     |  *run_simulation*,   |  *run_simulation*,  |  *run_simulation*,  |    *run_simulation*,         |
   |                         |                      |  *compute_EVC*       |  *compute_EVC*      |  *compute_EVC*      |    *compute_likelihood*      |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+
   |             *execution* | *iterate w/in trial* |  *once per trial*    | *iterate w/in trial*| *iterate w/in trial*|     *iterate w/in trial*     |
   +-------------------------+----------------------+----------------------+---------------------+---------------------+------------------------------+

The following models provide examples of implementing the OptimizationControlMechanisms in the table above:

`LVOCControlMechanism`\\:  `BustamanteStroopXORLVOCModel`
`EVCControlMechanism`\\:  `UmemotoTaskSwitchingEVCModel`




.. _OptimizationControlMechanism_Class_Reference:

Class Reference
---------------

"""
import typecheck as tc

import numpy as np

from psyneulink.core.components.functions.function import \
    ModulationParam, _is_modulation_param, is_function_type, OBJECTIVE_FUNCTION, \
    SEARCH_SPACE, SEARCH_FUNCTION, SEARCH_TERMINATION_FUNCTION
from psyneulink.core.components.mechanisms.adaptive.control.controlmechanism import ControlMechanism
from psyneulink.core.components.mechanisms.processing.objectivemechanism import \
    ObjectiveMechanism, MONITORED_OUTPUT_STATES
from psyneulink.core.components.states.parameterstate import ParameterState
from psyneulink.core.components.states.modulatorysignals.controlsignal import ControlSignalCosts, ControlSignal
from psyneulink.core.globals.keywords import \
    DEFAULT_VARIABLE, PARAMETER_STATES, OBJECTIVE_MECHANISM, OPTIMIZATION_CONTROL_MECHANISM
from psyneulink.core.globals.preferences.componentpreferenceset import is_pref_set
from psyneulink.core.globals.preferences.preferenceset import PreferenceLevel
from psyneulink.core.globals.utilities import is_iterable

__all__ = [
    'OptimizationControlMechanism', 'OptimizationControlMechanismError'
]

class OptimizationControlMechanismError(Exception):
    def __init__(self, error_value):
        self.error_value = error_value

    def __str__(self):
        return repr(self.error_value)

    
class OptimizationControlMechanism(ControlMechanism):
    """OptimizationControlMechanism(                       \
    objective_mechanism=None,                              \
    learning_function=None,                                \
    evaluation_function=None,                               \
    search_function=None,                                  \
    search_termination_function=None,                      \
    search_space=None,                                     \
    function=None,                                         \
    control_signals=None,                                  \
    modulation=ModulationParam.MULTIPLICATIVE,             \
    params=None,                                           \
    name=None,                                             \
    prefs=None)

    Subclass of `ControlMechanism <ControlMechanism>` that adjusts its `ControlSignals <ControlSignal>` to optimize
    performance of the `Composition` to which it belongs

    .. note::
       OptimizationControlMechanism is an abstract class and should NEVER be instantiated by a call to its constructor.
       It should be instantiated using the constructor for a subclass.

    Arguments
    ---------

    objective_mechanism : ObjectiveMechanism or List[OutputState specification]
        specifies either an `ObjectiveMechanism` to use for the OptimizationControlMechanism, or a list of the 
        `OutputState <OutputState>`\\s it should monitor; if a list of `OutputState specifications
        <ObjectiveMechanism_Monitored_Output_States>` is used, a default ObjectiveMechanism is created and the list
        is passed to its **monitored_output_states** argument.

    learning_function : LearningFunction, function or method
        specifies a function used to learn to predict the `EVC <OptimizationControlMechanism_EVC>` from
        the current `current_state <OptimizationControlMechanism.current_state>` (see
        `OptimizationControlMechanism_Learning_Function` for details).

    evaluation_function : function or method
        specifies the function used to evaluate the `EVC <OptimizationControlMechanism_EVC>` for a given
        `allocation_policy <ControlMechanism.allocation_policy>`. It is assigned as the `objective_function 
        <OptimizationFunction.objective_function>` parameter of `function  <OptimizationControlMechanism.function>`, 
        unless that is specified in the constructor for an  OptimizationFunction assigned to the **function** 
        argument of the OptimizationControlMechanism's constructor.  Often it is assigned directy to the 
        OptimizationControlMechanism's `compute_EVC <OptimizationControlMechanism.compute_EVC>` method;  in some 
        cases it may implement additional operations, but should always call `compute_EVC 
        <OptimizationControlMechanism.compute_EVC>`. A custom function can be assigned, but it must take as its 
        first argument an array with the same shape as the OptimizationControlMechanism's `allocation_policy 
        <ControlMechanism.allocation_policy>`, and return the following four values: an array containing the 
        `allocation_policy <ControlMechanism.allocation_policy>` that generated the optimal `EVC
        <OptimizationControlMechanism_EVC>`; an array containing that EVC value;  a list containing each
        `allocation_policy <ControlMechanism.allocation_policy>` sampled if `function 
        <OptimizationControlMechanism.function>` has a `save_samples <OptimizationFunction.save_samples>` attribute 
        and it is `True`, otherwise it should return an empty list; and a list containing the EVC values for each 
        `allocation_policy <ControlMechanism.allocation_policy>` sampled if the function has a `save_values 
        <OptimizationFunction.save_values>` attribute and it is `True`, otherwise it should return an empty list.

    search_function : function or method
        specifies the function assigned to `function <OptimizationControlMechanism.function>` as its 
        `search_function <OptimizationFunction.search_function>` parameter, unless that is specified in a 
        constructor for `function <OptimizationControlMechanism.function>`.  It must take as its arguments 
        an array with the same shape as `allocation_policy <ControlMechanism.allocation_policy>` and an integer
        (indicating the iteration of the `optimization process <OptimizationFunction_Process>`), and return 
        an array with the same shape as `allocation_policy <ControlMechanism.allocation_policy>`.

    search_termination_function : function or method
        specifies the function assigned to `function <OptimizationControlMechanism.function>` as its 
        `search_termination_function <OptimizationFunction.search_termination_function>` parameter, unless that is 
        specified in a constructor for `function <OptimizationControlMechanism.function>`.  It must take as its 
        arguments an array with the same shape as `allocation_policy <ControlMechanism.allocation_policy>` and two 
        integers (the first representing the `EVC <OptimizationControlMechanism_EVC>` value for the current 
        `allocation_policy <ControlMechanism.allocation_policy>`, and the second the current iteration of the 
        `optimization process <OptimizationFunction_Process>`;  it must return `True` or `False`.
        
    search_space : list or ndarray
        specifies the `search_space <OptimizationFunction.search_space>` parameter for `function 
        <OptimizationControlMechanism.function>`, unless that is specified in a constructor for `function 
        <OptimizationControlMechanism.function>`.  Each item must have the same shape as `allocation_policy 
        <ControlMechanism.allocation_policy>`.
        
    function : OptimizationFunction, function or method
        specifies the function used to optimize the `allocation_policy <ControlMechanism.allocation_policy>`;  
        must take as its sole argument an array with the same shape as `allocation_policy 
        <ControlMechanism.allocation_policy>`, and return a similar array (see `Primary Function 
        <OptimizationControlMechanism>` for additional details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that can be used to specify the parameters for the
        Mechanism, its `learning_function <OptimizationControlMechanism.learning_function>`, and/or a custom function and its parameters.  Values
        specified for parameters in the dictionary override any assigned to those parameters in arguments of the
        constructor.

    name : str : default see `name <OptimizationControlMechanism.name>`
        specifies the name of the OptimizationControlMechanism.

    prefs : PreferenceSet or specification dict : default Mechanism.classPreferences
        specifies the `PreferenceSet` for the OptimizationControlMechanism; see `prefs
        <OptimizationControlMechanism.prefs>` for details.

    Attributes
    ----------
    current_state : 1d ndarray
        array passed to `learning_function <OptimizationControlMechanism.learning_function>` if that is implemented.

    prediction_weights : 1d ndarray
        weights assigned to each term of `current_state <OptimizationControlMechanism.current_state>`
        by `learning_function <OptimizationControlMechanism.learning_function>`.

    learning_function : LearningFunction, function or method
        takes `current_state <OptimizationControlMechanism.current_state>` as its first argument, and
        `net_outcome <ControlMechanism.net_outcome>` as its second argument, and returns an updated set of 
        `prediction_weights <OptimizationControlMechanism.prediction_weights>` (see  
        `OptimizationControlMechanism_Learning_Function` for additional details).

    function : OptimizationFunction, function or method
        takes current `allocation_policy <ControlMechanism.allocation_policy>` (as initializer),
        uses its `search_function <OptimizationFunction.search_function>` to select samples of `allocation_policy
        <ControlMechanism.allocation_policy>` from its `search_space <OptimizationControlMechanism.search_space>`,
        evaluates these using its `evaluation_function <OptimizationControlMechanism.evaluation_function>`, and returns
        the one that yields the greatest `EVC <OptimizationControlMechanism_EVC>`  (see `Primary Function
        <OptimizationControlMechanism_Function>` for additional details).

    evaluation_function : function or method
        returns `EVC <OptimizationControlMechanism_EVC>` for either the `current_state
        <OptimizationControlMechanism.current_state>` (model-free OptimizationControlMechanism) or an
        `allocation_policy <ControlMechanism.allocation_policy>` (model-based); assigned as the `objective_function
        <OptimizationFunction.objective_function>` parameter of `function <OptimizationControlMechanism.function>`.
        
    search_function : function or method
        `search_function <OptimizationFunction.search_function>` assigned to `function 
        <OptimizationControlMechanism.function>`; used to select samples of `allocation_policy
        <ControlMechanism.allocation_policy>` to evaluate by `evaluation_function
        <OptimizationControlMechanism.evaluation_function>`.

    search_termination_function : function or method
        `search_termination_function <OptimizationFunction.search_termination_function>` assigned to
        `function <OptimizationControlMechanism.function>`;  determines when to terminate the 
        `optimization process <OptimizationFunction_Process>`.
        
    allocation_policy_search_space : list or ndarray
        `search_space <OptimizationFunction.search_space>` assigned to `function 
        <OptimizationControlMechanism.function>`;  determines the samples of
        `allocation_policy <ControlMechanism.allocation_policy>` evaluated by the `evaluation_function
        <OptimizationControlMechanism.evaluation_function>`.

    saved_samples : list
        contains all values of `allocation_policy <ControlMechanism.allocation_policy>` sampled by `function
        <OptimizationControlMechanism.function>` if its `save_samples <OptimizationFunction.save_samples>` parameter
        is `True`;  otherwise list is empty.

    saved_values : list
        contains values of EVC associated with all samples of `allocation_policy <ControlMechanism.allocation_policy>` 
         evaluated by by `function <OptimizationControlMechanism.function>` if its `save_values 
         <OptimizationFunction.save_samples>` parameter is `True`;  otherwise list is empty.

    name : str
        name of the OptimizationControlMechanism; if it is not specified in the **name** argument of the constructor, a
        default is assigned by MechanismRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict
        the `PreferenceSet` for the OptimizationControlMechanism; if it is not specified in the **prefs** argument of
        the constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentType = OPTIMIZATION_CONTROL_MECHANISM
    # initMethod = INIT_FULL_EXECUTE_METHOD
    # initMethod = INIT_EXECUTE_METHOD_ONLY

    classPreferenceLevel = PreferenceLevel.SUBTYPE
    # classPreferenceLevel = PreferenceLevel.TYPE
    # Any preferences specified below will override those specified in TypeDefaultPreferences
    # Note: only need to specify setting;  level will be assigned to Type automatically
    # classPreferences = {
    #     kwPreferenceSetName: 'DefaultControlMechanismCustomClassPreferences',
    #     kp<pref>: <setting>...}

    # FIX: ADD OTHER Params() HERE??
    class Params(ControlMechanism.Params):
        function = None

    paramClassDefaults = ControlMechanism.paramClassDefaults.copy()
    paramClassDefaults.update({PARAMETER_STATES: NotImplemented}) # This suppresses parameterStates

    @tc.typecheck
    def __init__(self,
                 objective_mechanism:tc.optional(tc.any(ObjectiveMechanism, list))=None,
                 origin_objective_mechanism=False,
                 terminal_objective_mechanism=False,
                 # learning_function=None,
                 function:tc.optional(tc.any(is_function_type))=None,
                 search_function:tc.optional(tc.any(is_function_type))=None,
                 search_termination_function:tc.optional(tc.any(is_function_type))=None,
                 search_space:tc.optional(tc.any(list, np.ndarray))=None,
                 control_signals:tc.optional(tc.any(is_iterable, ParameterState, ControlSignal))=None,
                 modulation:tc.optional(_is_modulation_param)=ModulationParam.MULTIPLICATIVE,
                 params=None,
                 name=None,
                 prefs:is_pref_set=None,
                 **kwargs):
        '''Abstract class that implements OptimizationControlMechanism'''

        if kwargs:
                for i in kwargs.keys():
                    raise OptimizationControlMechanismError("Unrecognized arg in constructor for {}: {}".
                                                            format(self.__class__.__name__, repr(i)))
        # self.learning_function = learning_function
        self.search_function = search_function
        self.search_termination_function = search_termination_function
        self.search_space = search_space

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(origin_objective_mechanism=origin_objective_mechanism,
                                                  terminal_objective_mechanism=terminal_objective_mechanism,
                                                  params=params)

        super().__init__(system=None,
                         objective_mechanism=objective_mechanism,
                         function=function,
                         control_signals=control_signals,
                         modulation=modulation,
                         params=params,
                         name=name,
                         prefs=prefs)

    def _validate_params(self, request_set, target_set=None, context=None):
        '''Insure that specification of ObjectiveMechanism has projections to it'''

        super()._validate_params(request_set=request_set, target_set=target_set, context=context)

        # KAM Removed the exception below 11/6/2018 because it was rejecting valid
        # monitored_output_state spec on ObjectiveMechanism

        # if (OBJECTIVE_MECHANISM in request_set and
        #         isinstance(request_set[OBJECTIVE_MECHANISM], ObjectiveMechanism)
        #         and not request_set[OBJECTIVE_MECHANISM].path_afferents):
        #     raise OptimizationControlMechanismError("{} specified for {} ({}) must be assigned one or more {}".
        #                                             format(ObjectiveMechanism.__name__, self.name,
        #                                                    request_set[OBJECTIVE_MECHANISM],
        #                                                    repr(MONITORED_OUTPUT_STATES)))

    def _instantiate_control_signal(self, control_signal, context=None):
        '''Implement ControlSignalCosts.DEFAULTS as default for cost_option of ControlSignals
        OptimizationControlMechanism requires use of at least one of the cost options
        '''
        control_signal = super()._instantiate_control_signal(control_signal, context)

        if control_signal.cost_options is None:
            control_signal.cost_options = ControlSignalCosts.DEFAULTS
            control_signal._instantiate_cost_attributes()
        return control_signal

    def _instantiate_attributes_after_function(self, context=None):
        '''Instantiate OptimizationControlMechanism attributes and assign parameters to learning_function & function'''

        super()._instantiate_attributes_after_function(context=context)

        # if self.learning_function:
        #     self._instantiate_learning_function()

        # Assign parameters to function (OptimizationFunction) that rely on OptimizationControlMechanism
        self.function_object.reinitialize({DEFAULT_VARIABLE: self.allocation_policy,
                                           OBJECTIVE_FUNCTION: self.evaluation_function,
                                           SEARCH_FUNCTION: self.search_function,
                                           SEARCH_TERMINATION_FUNCTION: self.search_termination_function,
                                           SEARCH_SPACE: self.get_allocation_policy_search_space()})

        self.evaluation_function = self.function_object.objective_function
        self.search_function = self.function_object.search_function
        self.search_termination_function = self.function_object.search_termination_function
        self.search_space = self.function_object.search_space

    def get_allocation_policy_search_space(self):

        control_signal_sample_lists = []
        for control_signal in self.control_signals:
            control_signal_sample_lists.append(control_signal.allocation_samples)

        # Construct allocation_policy_search_space:  set of all permutations of ControlProjection allocations
        #                                     (one sample from the allocationSample of each ControlProjection)
        # Reference for implementation below:
        # http://stackoverflow.com/questions/1208118/using-numpy-to-build-an-array-of-all-combinations-of-two-arrays
        self.allocation_policy_search_space = \
            np.array(np.meshgrid(*control_signal_sample_lists)).T.reshape(-1,len(self.control_signals))

        # Insure that ControlSignal in each sample is in its own 1d array
        re_shape = (self.allocation_policy_search_space.shape[0], self.allocation_policy_search_space.shape[1], 1)
        return self.allocation_policy_search_space.reshape(re_shape)

    def _execute(self, variable=None, runtime_params=None, context=None):
        '''Find allocation_policy that optimizes evaluation_function.'''

        raise OptimizationControlMechanismError("PROGRAM ERROR: {} must implement its own {} method".
                                                format(self.__class__.__name__, repr('_execute')))
    def evaluation_function(self, allocation_policy):
        '''Compute outcome for a given allocation_policy.'''

        raise OptimizationControlMechanismError("PROGRAM ERROR: {} must implement an {} method".
                                                format(self.__class__.__name__, repr('evaluation_function')))
