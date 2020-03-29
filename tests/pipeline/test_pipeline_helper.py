# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest

from kedro.pipeline import Pipeline, node, pipeline
from kedro.pipeline.modular_pipeline import ModularPipelineError

# Different dummy func based on the number of arguments


def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


class TestPipelineHelper:
    def test_transform_dataset_names(self):
        """
        Rename some datasets, test string, list and dict formats.
        """
        raw_pipeline = Pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(biconcat, ["C", "D"], ["E", "F"], name="node2"),
                node(
                    biconcat, {"input1": "H", "input2": "J"}, {"K": "L"}, name="node3"
                ),
            ]
        )

        resulting_pipeline = pipeline(
            raw_pipeline,
            inputs={"A": "A_new", "D": "D_new", "H": "H_new"},
            outputs={"B": "B_new", "E": "E_new", "L": "L_new"},
        )

        # make sure the order is correct
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "A_new"
        assert nodes[0]._outputs == "B_new"

        assert nodes[1]._inputs == ["C", "D_new"]
        assert nodes[1]._outputs == ["E_new", "F"]

        assert nodes[2]._inputs == {"input1": "H_new", "input2": "J"}
        assert nodes[2]._outputs == {"K": "L_new"}

    def test_prefix_dataset_names(self):
        """
        Simple prefixing for dataset of all formats: str, list and dict
        """
        raw_pipeline = Pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(biconcat, ["C", "D"], ["E", "F"], name="node2"),
                node(
                    biconcat, {"input1": "H", "input2": "J"}, {"K": "L"}, name="node3"
                ),
            ]
        )
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "PREFIX.A"
        assert nodes[0]._outputs == "PREFIX.B"

        assert nodes[1]._inputs == ["PREFIX.C", "PREFIX.D"]
        assert nodes[1]._outputs == ["PREFIX.E", "PREFIX.F"]

        assert nodes[2]._inputs == {"input1": "PREFIX.H", "input2": "PREFIX.J"}
        assert nodes[2]._outputs == {"K": "PREFIX.L"}

    def test_prefixing_and_renaming(self):
        """
        Prefixing and renaming at the same time.
        Explicitly renamed  datasets should not be prefixed anymore.
        """
        raw_pipeline = Pipeline([node(biconcat, ["C", "D"], ["E", "F"])])
        resulting_pipeline = pipeline(
            raw_pipeline,
            namespace="PREFIX",
            inputs={"C": "C_new"},
            outputs={"E": "E_new"},
        )
        assert resulting_pipeline.nodes[0]._inputs == ["C_new", "PREFIX.D"]
        assert resulting_pipeline.nodes[0]._outputs == ["E_new", "PREFIX.F"]

    def test_transform_params_prefix_and_parameters(self):
        """
        Test that transform should skip `params:` and `parameters`: str, list and dict.
        """
        raw_pipeline = Pipeline(
            [
                node(identity, "parameters", "params:B", name="node1"),
                node(biconcat, ["params:C", "D"], ["parameters", "F"], name="node2"),
                node(
                    biconcat,
                    {"input1": "params:H", "input2": "parameters"},
                    {"K": "L"},
                    name="node3",
                ),
            ]
        )
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "parameters"
        assert nodes[0]._outputs == "params:B"

        assert nodes[1]._inputs == ["params:C", "PREFIX.D"]
        assert nodes[1]._outputs == ["parameters", "PREFIX.F"]

        assert nodes[2]._inputs == {"input1": "params:H", "input2": "parameters"}
        assert nodes[2]._outputs == {"K": "PREFIX.L"}
        assert nodes[2].name == "PREFIX.node3"

    def test_dataset_transcoding_mapping_base_name(self):
        raw_pipeline = Pipeline([node(biconcat, ["C@pandas", "D"], ["E@spark", "F"])])
        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", inputs={"C": "C_new"}
        )

        assert resulting_pipeline.nodes[0]._inputs == ["C_new@pandas", "PREFIX.D"]
        assert resulting_pipeline.nodes[0]._outputs == ["PREFIX.E@spark", "PREFIX.F"]

    def test_dataset_transcoding_mapping_full_dataset(self):
        raw_pipeline = Pipeline(
            [
                node(biconcat, ["A@pandas", "B"], "C"),
                node(biconcat, ["A@spark", "C"], "CC"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, inputs={"A@pandas": "Alpha"}, namespace="PREFIX"
        )

        assert resulting_pipeline.nodes[0]._inputs == ["Alpha", "PREFIX.B"]
        assert resulting_pipeline.nodes[0]._outputs == "PREFIX.C"

        assert resulting_pipeline.nodes[1]._inputs == ["PREFIX.A@spark", "PREFIX.C"]
        assert resulting_pipeline.nodes[1]._outputs == "PREFIX.CC"

    def test_empty_input(self):
        raw_pipeline = Pipeline([node(constant_output, None, ["A", "B"])])

        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", outputs={"A": "A_new"}
        )
        assert resulting_pipeline.nodes[0]._inputs is None
        assert resulting_pipeline.nodes[0]._outputs == ["A_new", "PREFIX.B"]

    def test_empty_output(self):
        raw_pipeline = Pipeline([node(biconcat, ["A", "B"], None)])

        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", inputs={"A": "A_new"}
        )
        assert resulting_pipeline.nodes[0]._inputs == ["A_new", "PREFIX.B"]
        assert resulting_pipeline.nodes[0]._outputs is None

    @pytest.mark.parametrize(
        "func, inputs, outputs, inputs_map, outputs_map, expected_missing",
        [
            # Testing inputs
            (identity, "A", "OUT", {"A": "A_new", "B": "C", "D": "E"}, {}, ["B", "D"]),
            (biconcat, ["A", "B"], "OUT", {"C": "D"}, None, ["C"]),
            (biconcat, {"input1": "A", "input2": "B"}, "OUT", {"C": "D"}, {}, ["C"]),
            # Testing outputs
            (identity, "IN", "A", {}, {"A": "A_new", "B": "C", "D": "E"}, ["B", "D"]),
            (identity, "IN", ["A", "B"], None, {"C": "D"}, ["C"]),
            (identity, "IN", {"input1": "A", "input2": "B"}, None, {"C": "D"}, ["C"]),
            # Mix of both
            (identity, "A", "B", {"A": "A_new"}, {"B": "B_new", "C": "D"}, ["C"]),
            (identity, ["A"], ["B"], {"A": "A_new"}, {"B": "B_new", "C": "D"}, ["C"]),
            (
                identity,
                {"input1": "A"},
                {"out1": "B"},
                {"A": "A_new", "C": "D"},
                {"B": "B_new", "C": "D"},
                ["C"],
            ),
        ],
    )
    def test_missing_dataset_name(
        self, func, inputs, outputs, inputs_map, outputs_map, expected_missing
    ):  # pylint: disable=too-many-arguments
        raw_pipeline = Pipeline([node(func, inputs, outputs)])

        with pytest.raises(ModularPipelineError, match=r"Failed to map datasets") as e:
            pipeline(
                raw_pipeline, namespace="PREFIX", inputs=inputs_map, outputs=outputs_map
            )
        assert ", ".join(expected_missing) in str(e.value)

    def test_node_properties_preserved(self):
        """
        Check that we don't loose any valuable properties on node cloning.
        Also an explicitly defined name should get prefixed.
        """
        raw_pipeline = Pipeline([node(identity, "A", "B", name="node1", tags=["tag1"])])
        raw_pipeline = raw_pipeline.decorate(lambda: None)
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")

        assert resulting_pipeline.nodes[0].name == "PREFIX.node1"
        assert resulting_pipeline.nodes[0].tags == {"tag1"}
        assert len(resulting_pipeline.nodes[0]._decorators) == 1

    def test_default_node_name_is_untouched(self):
        """
        Check that we don't loose any valuable properties on node cloning.
        Default node name should not get prefixed.
        """
        raw_pipeline = Pipeline([node(identity, "A", "B")])
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")

        assert not resulting_pipeline.nodes[0].name.startswith("PREFIX.")

    def test_expose_intermediate_output(self):
        """Check that we don't namespace an intermediary dataset, anywhere it
        is used - either input or output"""
        raw_pipeline = Pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
                node(identity, "C", "D", name="node3"),
                node(biconcat, ["D", "params:x"], "X", name="node4"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, outputs={"B": "B_new"}, namespace="ACTUAL"
        )
        actual_nodes = resulting_pipeline.nodes

        assert actual_nodes[0]._outputs == "B_new"
        assert actual_nodes[1]._inputs == "B_new"

        assert actual_nodes[0]._inputs == "ACTUAL.A"
        assert actual_nodes[1]._outputs == "ACTUAL.C"
        assert actual_nodes[2]._inputs == "ACTUAL.C"
        assert actual_nodes[2]._outputs == "ACTUAL.D"

        assert actual_nodes[3]._inputs == ["ACTUAL.D", "params:x"]
        assert actual_nodes[3]._outputs == "ACTUAL.X"

    def test_parameters_updated(self):
        raw_pipeline = Pipeline(
            [
                node(biconcat, ["A", "params:x"], "AA", name="node1"),
                node(biconcat, ["AA", "params:y"], "B", name="node2"),
                node(biconcat, ["B", "params:x"], "BB", name="node3"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline,
            outputs={"B": "B_new"},
            parameters={"params:x": "params:y"},
            namespace="ACTUAL",
        )
        actual_nodes = resulting_pipeline.nodes

        assert actual_nodes[0]._inputs == ["ACTUAL.A", "params:y"]
        assert actual_nodes[0]._outputs == "ACTUAL.AA"

        assert actual_nodes[1]._inputs == ["ACTUAL.AA", "params:y"]
        assert actual_nodes[1]._outputs == "B_new"

        assert actual_nodes[2]._inputs == ["B_new", "params:y"]
        assert actual_nodes[2]._outputs == "ACTUAL.BB"

    def test_parameters_specified_under_inputs(self):
        raw_pipeline = Pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "parameters"], "BB", name="node2"),
            ]
        )

        pattern = r"Parameters should be specified in the `parameters` argument"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, inputs={"params:alpha": "params:beta"})

        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, inputs={"parameters": "some_yaml_dataset"})

    def test_non_existent_parameters_mapped(self):
        raw_pipeline = Pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "CC"], "BB", name="node2"),
            ]
        )

        pattern = r"Failed to map datasets and/or parameters: params:beta"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, parameters={"params:beta": "params:gamma"})

        pattern = r"Failed to map datasets and/or parameters: parameters"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, parameters={"parameters": "some_yaml_dataset"})