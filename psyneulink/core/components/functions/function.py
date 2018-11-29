#
# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
#
# ***********************************************  Function ************************************************************

"""
Function
  * `Function_Base`

Example function:
  * `ArgumentTherapy`

.. _Function_Overview:

Overview
--------

A Function is a `Component <Component>` that "packages" a function (in its `function <Function_Base.function>` method)
for use by other Components.  Every Component in PsyNeuLink is assigned a Function; when that Component is executed, its
Function's `function <Function_Base.function>` is executed.  The `function <Function_Base.function>` can be any callable
operation, although most commonly it is a mathematical operation (and, for those, almost always uses a call to one or
more numpy functions).  There are two reasons PsyNeuLink packages functions in a Function Component:

* **Manage parameters** -- parameters are attributes of a Function that either remain stable over multiple calls to the
  function (e.g., the `gain <Logistic.gain>` or `bias <Logistic.bias>` of a `Logistic` function, or the learning rate
  of a learning function); or, if they change, they do so less frequently or under the control of different factors
  than the function's variable (i.e., its input).  As a consequence, it is useful to manage these separately from the
  function's variable, and not have to provide them every time the function is called.  To address this, every
  PsyNeuLink Function has a set of attributes corresponding to the parameters of the function, that can be specified at
  the time the Function is created (in arguments to its constructor), and can be modified independently
  of a call to its :keyword:`function`. Modifications can be directly (e.g., in a script), or by the operation of other
  PsyNeuLink Components (e.g., `AdaptiveMechanisms`) by way of `ControlProjections <ControlProjection>`.
..
* **Modularity** -- by providing a standard interface, any Function assigned to a Components in PsyNeuLink can be
  replaced with other PsyNeuLink Functions, or with user-written custom functions so long as they adhere to certain
  standards (the PsyNeuLink :ref:`Function API <LINK>`).

.. _Function_Creation:

Creating a Function
-------------------

A Function can be created directly by calling its constructor.  Functions are also created automatically whenever
any other type of PsyNeuLink Component is created (and its :keyword:`function` is not otherwise specified). The
constructor for a Function has an argument for its `variable <Function_Base.variable>` and each of the parameters of
its `function <Function_Base.function>`.  The `variable <Function_Base.variable>` argument is used both to format the
input to the `function <Function_Base.function>`, and assign its default value.  The arguments for each parameter can
be used to specify the default value for that parameter; the values can later be modified in various ways as described
below.

.. _Function_Structure:

Structure
---------

.. _Function_Core_Attributes:

*Core Attributes*
~~~~~~~~~~~~~~~~~

Every Function has the following core attributes:

* `variable <Function_Base.variable>` -- provides the input to the Function's `function <Function_Base.function>`.
..
* `function <Function_Base.function>` -- determines the computation carried out by the Function; it must be a
  callable object (that is, a python function or method of some kind). Unlike other PsyNeuLink `Components
  <Component>`, it *cannot* be (another) Function object (it can't be "turtles" all the way down!). If the Function
  has been assigned to another `Component`, then its `function <Function_Base.function>` is also assigned as the
  the `function <Component.function>` attribute of the Component to which it has been assigned (i.e., its
  `owner <Function_Base.owner>`.

A Function also has an attribute for each of the parameters of its `function <Function_Base.function>`.

*Owner*
~~~~~~~

If a Function has been assigned to another `Component`, then it also has an `owner <Function_Base.owner>` attribute
that refers to that Component.  The Function itself is assigned as the Component's
`function_object <Component.function_object>` attribute.  Each of the Function's attributes is also assigned
as an attribute of the `owner <Function_Base.owner>`, and those are each associated with with a
`parameterState <ParameterState>` of the `owner <Function_Base.owner>`.  Projections to those parameterStates can be
used by `ControlProjections <ControlProjection>` to modify the Function's parameters.


COMMENT:
.. _Function_Output_Type_Conversion:

If the `function <Function_Base.function>` returns a single numeric value, and the Function's class implements
FunctionOutputTypeConversion, then the type of value returned by its `function <Function>` can be specified using the
`output_type` attribute, by assigning it one of the following `FunctionOutputType` values:
    * FunctionOutputType.RAW_NUMBER: return "exposed" number;
    * FunctionOutputType.NP_1D_ARRAY: return 1d np.array
    * FunctionOutputType.NP_2D_ARRAY: return 2d np.array.

To implement FunctionOutputTypeConversion, the Function's FUNCTION_OUTPUT_TYPE_CONVERSION parameter must set to True,
and function type conversion must be implemented by its `function <Function_Base.function>` method
(see `Linear` for an example).
COMMENT

.. _Function_Modulatory_Params:

*Modulatory Parameters*
~~~~~~~~~~~~~~~~~~~~~~~

Some classes of Functions also implement a pair of modulatory parameters: `multiplicative_param` and `additive_param`.
Each of these is assigned the name of one of the function's parameters. These are used by `ModulatorySignals
<ModulatorySignal>` to modulate the output of the function (see `figure <ModulatorySignal_Detail_Figure>`).  For
example, they are used by `GatingSignals <GatingSignal>` to modulate the `function <State_Base.function>` of an
`InputState` or `OutputState`, and thereby its `value <State_Base.value>`; and by the `ControlSignal(s) <ControlSignal>`
of an `LCControlMechanism` to modulate the `multiplicative_param` of the `function <TransferMechanism.function>` of a
`TransferMechanism`.


.. _Function_Execution:

Execution
---------

Functions are not executable objects, but their `function <Function_Base.function>` can be called.   This can be done
directly.  More commonly, however, they are called when their `owner <Function_Base.owner>` is executed.  The parameters
of the `function <Function_Base.function>` can be modified when it is executed, by assigning a
`parameter specification dictionary <ParameterState_Specification>` to the **params** argument in the
call to the `function <Function_Base.function>`.

For `Mechanisms <Mechanism>`, this can also be done by specifying `runtime_params <Run_Runtime_Parameters>` in the `Run`
method of their `Composition`.

Class Reference
---------------

"""

import numbers
import numpy as np
import warnings

from collections import namedtuple
from enum import Enum, IntEnum
from random import randint

from psyneulink.core import llvm as pnlvm
from psyneulink.core.components.component import function_type, method_type
from psyneulink.core.components.shellclasses import Function, Mechanism
from psyneulink.core.globals.context import ContextFlags
from psyneulink.core.globals.keywords import ARGUMENT_THERAPY_FUNCTION, EXAMPLE_FUNCTION_TYPE, FUNCTION, FUNCTION_OUTPUT_TYPE, FUNCTION_OUTPUT_TYPE_CONVERSION, \
    NAME, PARAMETER_STATE_PARAMS, \
    kwComponentCategory, kwPreferenceSetName
from psyneulink.core.globals.parameters import Param
from psyneulink.core.globals.preferences.componentpreferenceset import is_pref_set, kpReportOutputPref
from psyneulink.core.globals.preferences.preferenceset import PreferenceEntry, PreferenceLevel
from psyneulink.core.globals.registry import register_category
from psyneulink.core.globals.utilities import object_has_single_value, parameter_spec, safe_len

__all__ = [
    'ADDITIVE', 'ADDITIVE_PARAM', 'AdditiveParam', 'ArgumentTherapy', 'DISABLE', 'DISABLE_PARAM', 'EPSILON',
    'Function_Base', 'function_keywords', 'FunctionError', 'FunctionOutputType', 'FunctionRegistry',
    'get_param_value_for_function', 'get_param_value_for_keyword', 'is_Function', 'is_function_type',
    'ModulatedParam','ModulationParam', 'MULTIPLICATIVE', 'MULTIPLICATIVE_PARAM','MultiplicativeParam',
    'OVERRIDE', 'OVERRIDE_PARAM', 'PERTINACITY', 'PROPENSITY'
]


EPSILON = np.finfo(float).eps

FunctionRegistry = {}

function_keywords = {FUNCTION_OUTPUT_TYPE, FUNCTION_OUTPUT_TYPE_CONVERSION}


class FunctionError(Exception):
    def __init__(self, error_value):
        self.error_value = error_value

    def __str__(self):
        return repr(self.error_value)


class FunctionOutputType(IntEnum):
    RAW_NUMBER = 0
    NP_1D_ARRAY = 1
    NP_2D_ARRAY = 2


# Typechecking *********************************************************************************************************

# TYPE_CHECK for Function Instance or Class
def is_Function(x):
    if not x:
        return False
    elif isinstance(x, Function):
        return True
    elif issubclass(x, Function):
        return True
    else:
        return False


def is_function_type(x):
    if not x:
        return False
    elif isinstance(x, (Function, function_type, method_type)):
        return True
    elif issubclass(x, Function):
        return True
    else:
        return False


# Modulatory Parameters ************************************************************************************************

ADDITIVE_PARAM = 'additive_param'
MULTIPLICATIVE_PARAM = 'multiplicative_param'
OVERRIDE_PARAM = 'OVERRIDE'
DISABLE_PARAM = 'DISABLE'


class MultiplicativeParam():
    attrib_name = MULTIPLICATIVE_PARAM
    name = 'MULTIPLICATIVE'
    init_val = 1
    reduce = lambda x: np.product(np.array(x), axis=0)


class AdditiveParam():
    attrib_name = ADDITIVE_PARAM
    name = 'ADDITIVE'
    init_val = 0
    reduce = lambda x: np.sum(np.array(x), axis=0)


# class OverrideParam():
#     attrib_name = OVERRIDE_PARAM
#     name = 'OVERRIDE'
#     init_val = None
#     reduce = lambda x : None
#
# class DisableParam():
#     attrib_name = OVERRIDE_PARAM
#     name = 'DISABLE'
#     init_val = None
#     reduce = lambda x : None


# IMPLEMENTATION NOTE:  USING A namedtuple DOESN'T WORK, AS CAN'T COPY PARAM IN Component._validate_param
# ModulationType = namedtuple('ModulationType', 'attrib_name, name, init_val, reduce')


class ModulationParam():
    """Specify parameter of a `Function <Function>` for `modulation <ModulatorySignal_Modulation>` by a ModulatorySignal

    COMMENT:
        Each term specifies a different type of modulation used by a `ModulatorySignal <ModulatorySignal>`.  The first
        two refer to classes that define the following terms:
            * attrib_name (*ADDITIVE_PARAM* or *MULTIPLICATIVE_PARAM*):  specifies which meta-parameter of the function
              to use for modulation;
            * name (str): name of the meta-parameter
            * init_val (int or float): value with which to initialize the parameter being modulated if it is not otherwise
              specified
            * reduce (function): the manner by which to aggregate multiple ModulatorySignals of that type, if the
              `ParameterState` receives more than one `ModulatoryProjection <ModulatoryProjection>` of that type.
    COMMENT

    Attributes
    ----------

    MULTIPLICATIVE
        assign the `value <ModulatorySignal.value>` of the ModulatorySignal to the *MULTIPLICATIVE_PARAM*
        of the State's `function <State_Base.function>`

    ADDITIVE
        assign the `value <ModulatorySignal.value>` of the ModulatorySignal to the *ADDITIVE_PARAM*
        of the State's `function <State_Base.function>`

    OVERRIDE
        assign the `value <ModulatorySignal.value>` of the ModulatorySignal directly to the State's
        `value <State_Base.value>` (ignoring its `variable <State_Base.variable>` and `function <State_Base.function>`)

    DISABLE
        ignore the ModulatorySignal when calculating the State's `value <State_Base.value>`
    """
    MULTIPLICATIVE = MultiplicativeParam
    # MULTIPLICATIVE = ModulationType(MULTIPLICATIVE_PARAM,
    #                                 'MULTIPLICATIVE',
    #                                 1,
    #                                 lambda x : np.product(np.array(x), axis=0))
    ADDITIVE = AdditiveParam
    # ADDITIVE = ModulationType(ADDITIVE_PARAM,
    #                           'ADDITIVE',
    #                           0,
    #                           lambda x : np.sum(np.array(x), axis=0))
    OVERRIDE = OVERRIDE_PARAM
    # OVERRIDE = OverrideParam
    DISABLE = DISABLE_PARAM
    # DISABLE = DisableParam


MULTIPLICATIVE = ModulationParam.MULTIPLICATIVE
ADDITIVE = ModulationParam.ADDITIVE
OVERRIDE = ModulationParam.OVERRIDE
DISABLE = ModulationParam.DISABLE


def _is_modulation_param(val):
    if val in ModulationParam.__dict__.values():
        return True
    else:
        return False


ModulatedParam = namedtuple('ModulatedParam', 'meta_param, function_param, function_param_val')


def _get_modulated_param(owner, mod_proj, execution_context=None):
    """Return ModulationParam object, function param name and value of param modulated by ModulatoryProjection
    """

    from psyneulink.core.components.projections.modulatory.modulatoryprojection import ModulatoryProjection_Base

    if not isinstance(mod_proj, ModulatoryProjection_Base):
        raise FunctionError('mod_proj ({0}) is not a ModulatoryProjection_Base'.format(mod_proj))

    # Get function "meta-parameter" object specified in the Projection sender's modulation attribute
    function_mod_meta_param_obj = mod_proj.sender.modulation

    # # MODIFIED 6/27/18 OLD
    # # Get the actual parameter of owner.function_object to be modulated
    # function_param_name = owner.function_object.params[function_mod_meta_param_obj.attrib_name]
    # # Get the function parameter's value
    # function_param_value = owner.function_object.params[function_param_name]
    # # MODIFIED 6/27/18 NEW:
    if function_mod_meta_param_obj in {OVERRIDE, DISABLE}:
        # function_param_name = function_mod_meta_param_obj
        from psyneulink.core.globals.utilities import Modulation
        function_mod_meta_param_obj = getattr(Modulation, function_mod_meta_param_obj)
        function_param_name = function_mod_meta_param_obj
        function_param_value = mod_proj.sender.parameters.value.get(execution_context)
    else:
        # Get the actual parameter of owner.function_object to be modulated
        function_param_name = owner.function_object.params[function_mod_meta_param_obj.attrib_name]
        # Get the function parameter's value
        function_param_value = owner.function_object.params[function_param_name]
    # # MODIFIED 6/27/18 NEWER:
    # from psyneulink.core.globals.utilities import Modulation
    # mod_spec = function_mod_meta_param_obj.attrib_name
    # if mod_spec == OVERRIDE_PARAM:
    #     function_param_name = mod_spec
    #     function_param_value = mod_proj.sender.value
    # elif mod_spec == DISABLE_PARAM:
    #     function_param_name = mod_spec
    #     function_param_value = None
    # else:
    #     # Get name of the actual parameter of owner.function_object to be modulated
    #     function_param_name = owner.function_object.params[mod_spec]
    #     # Get the function parameter's value
    #     function_param_value = owner.function_object.params[mod_spec]
    # MODIFIED 6/27/18 END

    # Return the meta_parameter object, function_param name, and function_param_value
    return ModulatedParam(function_mod_meta_param_obj, function_param_name, function_param_value)


# *******************************   get_param_value_for_keyword ********************************************************

def get_param_value_for_keyword(owner, keyword):
    """Return the value for a keyword used by a subclass of Function

    Parameters
    ----------
    owner : Component
    keyword : str

    Returns
    -------
    value

    """
    try:
        function_val = owner.params[FUNCTION]
        if function_val is None:
            # paramsCurrent will go directly to an attribute value first before
            # returning what's actually in its dictionary, so fall back
            try:
                keyval = owner.params.data[FUNCTION].keyword(owner, keyword)
            except KeyError:
                keyval = None
        else:
            keyval = function_val.keyword(owner, keyword)
        return keyval
    except FunctionError as e:
        # assert(False)
        # prefs is not always created when this is called, so check
        try:
            owner.prefs
            has_prefs = True
        except AttributeError:
            has_prefs = False

        if has_prefs and owner.prefs.verbosePref:
            print("{} of {}".format(e, owner.name))
        # return None
        else:
            raise FunctionError(e)
    except AttributeError:
        # prefs is not always created when this is called, so check
        try:
            owner.prefs
            has_prefs = True
        except AttributeError:
            has_prefs = False

        if has_prefs and owner.prefs.verbosePref:
            print("Keyword ({}) not recognized for {}".format(keyword, owner.name))
        return None


def get_param_value_for_function(owner, function):
    try:
        return owner.paramsCurrent[FUNCTION].param_function(owner, function)
    except FunctionError as e:
        if owner.prefs.verbosePref:
            print("{} of {}".format(e, owner.name))
        return None
    except AttributeError:
        if owner.prefs.verbosePref:
            print("Function ({}) can't be evaluated for {}".format(function, owner.name))
        return None

# Parameter Mixins *****************************************************************************************************

# KDM 6/21/18: Below is left in for consideration; doesn't really gain much to justify relaxing the assumption
# that every Params class has a single parent

# class ScaleOffsetParamMixin:
#     scale = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
#     offset = Param(1.0, modulable=True, aliases=[ADDITIVE_PARAM])


# Function Definitions *************************************************************************************************


# KDM 8/9/18: below is added for future use when function methods are completely functional
# used as a decorator for Function methods
# def enable_output_conversion(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         result = func(*args, **kwargs)
#         return convert_output_type(result)
#     return wrapper


class Function_Base(Function):
    """
    Function_Base(           \
         default_variable,   \
         params=None,        \
         owner=None,         \
         name=None,          \
         prefs=None          \
    )

    Implement abstract class for Function category of Component class

    COMMENT:
        Description:
            Functions are used to "wrap" functions used used by other components;
            They are defined here (on top of standard libraries) to provide a uniform interface for managing parameters
             (including defaults)
            NOTE:   the Function category definition serves primarily as a shell, and as an interface to the Function
                       class, to maintain consistency of structure with the other function categories;
                    it also insures implementation of .function for all Function Components
                    (as distinct from other Function subclasses, which can use a FUNCTION param
                        to implement .function instead of doing so directly)
                    Function Components are the end of the recursive line; as such:
                        they don't implement functionParams
                        in general, don't bother implementing function, rather...
                        they rely on Function_Base.function which passes on the return value of .function

        Variable and Parameters:
        IMPLEMENTATION NOTE:  ** DESCRIBE VARIABLE HERE AND HOW/WHY IT DIFFERS FROM PARAMETER
            - Parameters can be assigned and/or changed individually or in sets, by:
              - including them in the initialization call
              - calling the _instantiate_defaults method (which changes their default values)
              - including them in a call the function method (which changes their values for just for that call)
            - Parameters must be specified in a params dictionary:
              - the key for each entry should be the name of the parameter (used also to name associated Projections)
              - the value for each entry is the value of the parameter

        Return values:
            The output_type can be used to specify type conversion for single-item return values:
            - it can only be used for numbers or a single-number list; other values will generate an exception
            - if self.output_type is set to:
                FunctionOutputType.RAW_NUMBER, return value is "exposed" as a number
                FunctionOutputType.NP_1D_ARRAY, return value is 1d np.array
                FunctionOutputType.NP_2D_ARRAY, return value is 2d np.array
            - it must be enabled for a subclass by setting params[FUNCTION_OUTPUT_TYPE_CONVERSION] = True
            - it must be implemented in the execute method of the subclass
            - see Linear for an example

        MechanismRegistry:
            All Function functions are registered in FunctionRegistry, which maintains a dict for each subclass,
              a count for all instances of that type, and a dictionary of those instances

        Naming:
            Function functions are named by their componentName attribute (usually = componentType)

        Class attributes:
            + componentCategory: kwComponentCategory
            + className (str): kwMechanismFunctionCategory
            + suffix (str): " <className>"
            + registry (dict): FunctionRegistry
            + classPreference (PreferenceSet): ComponentPreferenceSet, instantiated in __init__()
            + classPreferenceLevel (PreferenceLevel): PreferenceLevel.CATEGORY
            + paramClassDefaults (dict): {FUNCTION_OUTPUT_TYPE_CONVERSION: :keyword:`False`}

        Class methods:
            none

        Instance attributes:
            + componentType (str):  assigned by subclasses
            + componentName (str):   assigned by subclasses
            + variable (value) - used as input to function's execute method
            + paramInstanceDefaults (dict) - defaults for instance (created and validated in Components init)
            + paramsCurrent (dict) - set currently in effect
            + value (value) - output of execute method
            + name (str) - if not specified as an arg, a default based on the class is assigned in register_category
            + prefs (PreferenceSet) - if not specified as an arg, default is created by copying ComponentPreferenceSet

        Instance methods:
            The following method MUST be overridden by an implementation in the subclass:
            - execute(variable, params)
            The following can be implemented, to customize validation of the function variable and/or params:
            - [_validate_variable(variable)]
            - [_validate_params(request_set, target_set, context)]
    COMMENT

    Arguments
    ---------

    variable : value : default ClassDefaults.variable
        specifies the format and a default value for the input to `function <Function>`.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).


    Attributes
    ----------

    variable: value
        format and default value can be specified by the :keyword:`variable` argument of the constructor;  otherwise,
        they are specified by the Function's :keyword:`ClassDefaults.variable`.

    function : function
        called by the Function's `owner <Function_Base.owner>` when it is executed.

    COMMENT:
    enable_output_type_conversion : Bool : False
        specifies whether `function output type conversion <Function_Output_Type_Conversion>` is enabled.

    output_type : FunctionOutputType : None
        used to specify the return type for the `function <Function_Base.function>`;  `functionOuputTypeConversion`
        must be enabled and implemented for the class (see `FunctionOutputType <Function_Output_Type_Conversion>`
        for details).
    COMMENT

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).

    """

    componentCategory = kwComponentCategory
    className = componentCategory
    suffix = " " + className

    registry = FunctionRegistry

    classPreferenceLevel = PreferenceLevel.CATEGORY

    variableClassDefault_locked = False

    class Params(Function.Params):
        variable = Param(np.array([0]), read_only=True)

    # Note: the following enforce encoding as 1D np.ndarrays (one array per variable)
    variableEncodingDim = 1

    paramClassDefaults = Function.paramClassDefaults.copy()
    paramClassDefaults.update({
        FUNCTION_OUTPUT_TYPE_CONVERSION: False,  # Enable/disable output type conversion
        FUNCTION_OUTPUT_TYPE: None  # Default is to not convert
    })

    def __init__(self,
                 default_variable,
                 params,
                 function=None,
                 owner=None,
                 name=None,
                 prefs=None,
                 context=None):
        """Assign category-level preferences, register category, and call super.__init__

        Initialization arguments:
        - default_variable (anything): establishes type for the variable, used for validation
        - params_default (dict): assigned as paramInstanceDefaults
        Note: if parameter_validation is off, validation is suppressed (for efficiency) (Function class default = on)

        :param default_variable: (anything but a dict) - value to assign as self.instance_defaults.variable
        :param params: (dict) - params to be assigned to paramInstanceDefaults
        :param log: (ComponentLog enum) - log entry types set in self.componentLog
        :param name: (string) - optional, overrides assignment of default (componentName of subclass)
        :return:
        """

        if context != ContextFlags.CONSTRUCTOR:
            raise FunctionError("Direct call to abstract class Function() is not allowed; use a Function subclass")

        if self.context.initialization_status == ContextFlags.DEFERRED_INIT:
            self._assign_deferred_init_name(name, context)
            self.init_args[NAME] = name
            return


        self._output_type = None
        self.enable_output_type_conversion = False

        register_category(entry=self,
                          base_class=Function_Base,
                          registry=FunctionRegistry,
                          name=name,
                          context=context)
        self.owner = owner

        super().__init__(default_variable=default_variable,
                         function=function,
                         param_defaults=params,
                         name=name,
                         prefs=prefs)

    def _parse_arg_generic(self, arg_val):
        if isinstance(arg_val, list):
            return np.asarray(arg_val)
        else:
            return arg_val

    def _validate_parameter_spec(self, param, param_name, numeric_only=True):
        """Validates function param
        Replace direct call to parameter_spec in tc, which seems to not get called by Function __init__()'s"""
        if not parameter_spec(param, numeric_only):
            owner_name = 'of ' + self.owner_name if self.owner else ""
            raise FunctionError("{} is not a valid specification for the {} argument of {}{}".
                                format(param, param_name, self.__class__.__name__, owner_name))

    def get_current_function_param(self, param_name, execution_context=None):
        if param_name == "variable":
            raise FunctionError("The method 'get_current_function_param' is intended for retrieving the current value "
                                "of a function parameter. 'variable' is not a function parameter. If looking for {}'s "
                                "default variable, try {}.instance_defaults.variable.".format(self.name, self.name))
        try:
            return self.owner._parameter_states[param_name].parameters.value.get(execution_context)
        except (AttributeError, TypeError):
            try:
                return getattr(self.parameters, param_name).get(execution_context)
            except AttributeError:
                raise FunctionError("{0} has no parameter '{1}'".format(self, param_name))

    def get_previous_value(self, execution_context=None):
        # temporary method until previous values are integrated for all parameters
        value = self.parameters.previous_value.get(execution_context)
        if value is None:
            value = self.parameters.previous_value.get()

        return value

    def convert_output_type(self, value, output_type=None):
        if output_type is None:
            if not self.enable_output_type_conversion or self.output_type is None:
                return value
            else:
                output_type = self.output_type

        value = np.asarray(value)

        # region Type conversion (specified by output_type):
        # Convert to 2D array, irrespective of value type:
        if output_type is FunctionOutputType.NP_2D_ARRAY:
            # KDM 8/10/18: mimicking the conversion that Mechanism does to its values, because
            # this is what we actually wanted this method for. Can be changed to pure 2D np array in
            # future if necessary

            converted_to_2d = np.atleast_2d(value)
            # If return_value is a list of heterogenous elements, return as is
            #     (satisfies requirement that return_value be an array of possibly multidimensional values)
            if converted_to_2d.dtype == object:
                pass
            # Otherwise, return value converted to 2d np.array
            else:
                value = converted_to_2d

        # Convert to 1D array, irrespective of value type:
        # Note: if 2D array (or higher) has more than two items in the outer dimension, generate exception
        elif output_type is FunctionOutputType.NP_1D_ARRAY:
            # If variable is 2D
            if value.ndim >= 2:
                # If there is only one item:
                if len(value) == 1:
                    value = value[0]
                else:
                    raise FunctionError("Can't convert value ({0}: 2D np.ndarray object with more than one array)"
                                        " to 1D array".format(value))
            elif value.ndim == 1:
                value = value
            elif value.ndim == 0:
                value = np.atleast_1d(value)
            else:
                raise FunctionError("Can't convert value ({0} to 1D array".format(value))

        # Convert to raw number, irrespective of value type:
        # Note: if 2D or 1D array has more than two items, generate exception
        elif output_type is FunctionOutputType.RAW_NUMBER:
            if object_has_single_value(value):
                value = float(value)
            else:
                raise FunctionError("Can't convert value ({0}) with more than a single number to a raw number".format(value))

        return value

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        # Bad outputType specification
        if value is not None and not isinstance(value, FunctionOutputType):
            raise FunctionError("value ({0}) of output_type attribute must be FunctionOutputType for {1}".
                                format(self.output_type, self.__class__.__name__))

        # Can't convert from arrays of length > 1 to number
        if (
            self.instance_defaults.variable is not None
            and safe_len(self.instance_defaults.variable) > 1
            and self.output_type is FunctionOutputType.RAW_NUMBER
        ):
            raise FunctionError(
                "{0} can't be set to return a single number since its variable has more than one number".
                format(self.__class__.__name__))

        # warn if user overrides the 2D setting for mechanism functions
        # may be removed when https://github.com/PrincetonUniversity/PsyNeuLink/issues/895 is solved properly
        # (meaning Mechanism values may be something other than 2D np array)
        try:
            # import here because if this package is not installed, we can assume the user is probably not dealing with compilation
            # so no need to warn unecessarily
            import llvmlite
            if (isinstance(self.owner, Mechanism) and (value == FunctionOutputType.RAW_NUMBER or value == FunctionOutputType.NP_1D_ARRAY)):
                warnings.warn(
                    'Functions that are owned by a Mechanism but do not return a 2D numpy array may cause unexpected behavior if '
                    'llvm compilation is enabled.'
                )
        except (AttributeError, ImportError):
            pass

        self._output_type = value

    def show_params(self):
        print("\nParams for {} ({}):".format(self.name, self.componentName))
        for param_name, param_value in sorted(self.user_params.items()):
            print("\t{}: {}".format(param_name, param_value))
        print('')

    @property
    def owner_name(self):
        try:
            return self.owner.name
        except AttributeError:
            return '<no owner>'

    def _get_context_initializer(self, execution_id):
        return tuple([])

    def _get_param_ids(self, execution_id=None):
        params = []

        for pc in self.parameters.names():
            # Filter out params not allowed in get_current_function_param
            if pc != 'function' and pc != 'value' and pc != 'variable':
                val = self.get_current_function_param(pc, execution_id)
                # or are not numeric (this includes aliases)
                if not isinstance(val, str):
                    params.append(pc)
        return params

    def _get_param_values(self, execution_id=None):
        param_init = []
        for p in self._get_param_ids():
            param = self.get_current_function_param(p, execution_id)
            if not np.isscalar(param) and param is not None:
                param = np.asfarray(param).flatten().tolist()
            param_init.append(param)

        return tuple(param_init)

    def _get_param_initializer(self, execution_id):
        return pnlvm._tupleize(self._get_param_values(execution_id))

# *****************************************   EXAMPLE FUNCTION   *******************************************************

PROPENSITY = "PROPENSITY"
PERTINACITY = "PERTINACITY"


class ArgumentTherapy(Function_Base):
    """
    ArgumentTherapy(                   \
         variable,                     \
         propensity=Manner.CONTRARIAN, \
         pertinacity=10.0              \
         params=None,                  \
         owner=None,                   \
         name=None,                    \
         prefs=None                    \
         )

    .. _ArgumentTherapist:

    Return `True` or :keyword:`False` according to the manner of the therapist.

    Arguments
    ---------

    variable : boolean or statement that resolves to one : default ClassDefaults.variable
        assertion for which a therapeutic response will be offered.

    propensity : Manner value : default Manner.CONTRARIAN
        specifies preferred therapeutic manner

    pertinacity : float : default 10.0
        specifies therapeutic consistency

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).


    Attributes
    ----------

    variable : boolean
        assertion to which a therapeutic response is made.

    propensity : Manner value : default Manner.CONTRARIAN
        determines therapeutic manner:  tendency to agree or disagree.

    pertinacity : float : default 10.0
        determines consistency with which the manner complies with the propensity.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).


    """

    # Function componentName and type (defined at top of module)
    componentName = ARGUMENT_THERAPY_FUNCTION
    componentType = EXAMPLE_FUNCTION_TYPE

    classPreferences = {
        kwPreferenceSetName: 'ExampleClassPreferences',
        kpReportOutputPref: PreferenceEntry(False, PreferenceLevel.INSTANCE),
    }

    # Variable class default
    # This is used both to type-cast the variable, and to initialize instance_defaults.variable
    variableClassDefault_locked = False

    # Mode indicators
    class Manner(Enum):
        OBSEQUIOUS = 0
        CONTRARIAN = 1

    # Param class defaults
    # These are used both to type-cast the params, and as defaults if none are assigned
    #  in the initialization call or later (using either _instantiate_defaults or during a function call)

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
                               PARAMETER_STATE_PARAMS: None
                               # PROPENSITY: Manner.CONTRARIAN,
                               # PERTINACITY:  10
                               })

    def __init__(self,
                 default_variable=None,
                 propensity=10.0,
                 pertincacity=Manner.CONTRARIAN,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(propensity=propensity,
                                                  pertinacity=pertincacity,
                                                  params=params)

        # This validates variable and/or params_list if assigned (using _validate_params method below),
        #    and assigns them to paramsCurrent and paramInstanceDefaults;
        #    otherwise, assigns paramClassDefaults to paramsCurrent and paramInstanceDefaults
        # NOTES:
        #    * paramsCurrent can be changed by including params in call to function
        #    * paramInstanceDefaults can be changed by calling assign_default
        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         context=ContextFlags.CONSTRUCTOR)

    def _validate_variable(self, variable, context=None):
        """Validates variable and returns validated value

        This overrides the class method, to perform more detailed type checking
        See explanation in class method.
        Note: this method (or the class version) is called only if the parameter_validation attribute is `True`

        :param variable: (anything but a dict) - variable to be validated:
        :param context: (str)
        :return variable: - validated
        """

        if type(variable) == type(self.ClassDefaults.variable) or \
                (isinstance(variable, numbers.Number) and isinstance(self.ClassDefaults.variable, numbers.Number)):
            return variable
        else:
            raise FunctionError("Variable must be {0}".format(type(self.ClassDefaults.variable)))

    def _validate_params(self, request_set, target_set=None, context=None):
        """Validates variable and /or params and assigns to targets

        This overrides the class method, to perform more detailed type checking
        See explanation in class method.
        Note: this method (or the class version) is called only if the parameter_validation attribute is `True`

        :param request_set: (dict) - params to be validated
        :param target_set: (dict) - destination of validated params
        :return none:
        """

        message = ""

        # Check params
        for param_name, param_value in request_set.items():

            if param_name == PROPENSITY:
                if isinstance(param_value, ArgumentTherapy.Manner):
                    # target_set[self.PROPENSITY] = param_value
                    pass  # This leaves param in request_set, clear to be assigned to target_set in call to super below
                else:
                    message = "Propensity must be of type Example.Mode"
                continue

            # Validate param
            if param_name == PERTINACITY:
                if isinstance(param_value, numbers.Number) and 0 <= param_value <= 10:
                    # target_set[PERTINACITY] = param_value
                    pass  # This leaves param in request_set, clear to be assigned to target_set in call to super below
                else:
                    message += "Pertinacity must be a number between 0 and 10"
                continue

        if message:
            raise FunctionError(message)

        super()._validate_params(request_set, target_set, context)

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """
        Returns a boolean that is (or tends to be) the same as or opposite the one passed in.

        Arguments
        ---------

        variable : boolean : default ClassDefaults.variable
           an assertion to which a therapeutic response is made.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.


        Returns
        -------

        therapeutic response : boolean

        """
        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        # Compute the function
        statement = variable
        propensity = self.get_current_function_param(PROPENSITY, execution_id)
        pertinacity = self.get_current_function_param(PERTINACITY, execution_id)
        whim = randint(-10, 10)

        if propensity == self.Manner.OBSEQUIOUS:
            value = whim < pertinacity

        elif propensity == self.Manner.CONTRARIAN:
            value = whim > pertinacity

        else:
            raise FunctionError("This should not happen if parameter_validation == True;  check its value")

        return self.convert_output_type(value)

