'''
Copyright 2020 Cisco Systems, Inc. and its affiliates.
 
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
    http://www.apache.org/licenses/LICENSE-2.0
 
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License


Program to create an Entity-Relationship Markup Language (ERML) file
from an ER diagram created as a GraphML file using yEd graph editor.

References:
    yEd - https://www.yworks.com/products/yed
    GraphML - http://graphml.graphdrawing.org/index.html

Usage: generml.py [OPTIONS]

  Read an Entity-Relationship diagram created by the yEd graph editor and
  convert it into Entity-Relationship Markup Language

  References:
  yEd - https://www.yworks.com/products/yed
  GraphML - http://graphml.graphdrawing.org/index.html

Options:
  --input TEXT    Input GraphML file (default is standard input, also
                  represented by a dash "-")
  --output TEXT   Output ERML file (default is standard output, also
                  represented by a dash "-")
  --overwrite     If specified, overwrite the output file if it already exists
  --logging TEXT  Set logging to the specified level: NOTSET, DEBUG, INFO,
                  WARNING, ERROR, CRITICAL
  --help          Show this message and exit.
'''

# TODO:
# support index specifications
# support label on edge (as a note in the ERML for the relationship)
# support edge end labels (does not appear to be natively supported in yEd)
# - needed to specify relationship roles to support more than one relationship between any two entities
# validate allowable data types

import sys
import os.path
from loguru import logger
import click
import xml.etree.ElementTree as ET
import cardinality
import re
import yaml
import jsonschema
import datetime
from util import i
from json_schema_graphml import json_schema_graphml_entity_attributes, json_schema_graphml_enum


def strip_namespace(tag):
    '''
    Strip the namespace from an element tag
    
    Example:
     - before: {http://graphml.graphdrawing.org/xmlns}node
     - after:  node
    '''
    return re.sub(r'{.*}', r'', tag)


@logger.catch
def generml(input_file_or_object, input, output_object):
    '''
    Generally-callable entry point to
    read an Entity-Relationship diagram created by the yEd graph editor and 
    convert it into Entity-Relationship Markup Language

    \b
    References:
    yEd - https://www.yworks.com/products/yed
    GraphML - http://graphml.graphdrawing.org/index.html
    '''
    logger.debug('Entering generml()')

    graph_tag =        '{http://graphml.graphdrawing.org/xmlns}graph'
    node_tag =         '{http://graphml.graphdrawing.org/xmlns}node'
    edge_tag =         '{http://graphml.graphdrawing.org/xmlns}edge'
    data_tag =         '{http://graphml.graphdrawing.org/xmlns}data'
    GenericNode_tag =  '{http://www.yworks.com/xml/graphml}GenericNode'
    BorderStyle_tag =  '{http://www.yworks.com/xml/graphml}BorderStyle'
    PolyLineEdge_tag = '{http://www.yworks.com/xml/graphml}PolyLineEdge'
    NodeLabel_tag =    '{http://www.yworks.com/xml/graphml}NodeLabel'
    LineStyle_tag =    '{http://www.yworks.com/xml/graphml}LineStyle'
    Arrows_tag =       '{http://www.yworks.com/xml/graphml}Arrows'

    NodeLabel_attr_configuration_name =        'com.yworks.entityRelationship.label.name'
    NodeLabel_attr_configuration_attributes =  'com.yworks.entityRelationship.label.attributes'
    GenericNode_attr_configuration_BigEntity = 'com.yworks.entityRelationship.big_entity'

    logger.debug('before parse()')
    tree = ET.parse(input_file_or_object)
    logger.debug('after parse()')
    root = tree.getroot()

    logger.debug('Printing Entity-Relationship Markup Language')
    er_head = {
        "source": 'stdin' if input == '-' else input,
        "generated_datetime": datetime.datetime.utcnow().isoformat()
    }
    print(yaml.dump(er_head), file=output_object)
    er = { }
    end_kinds = set()   # delete after debugging done
    er_entities = [ ]
    er_enums = [ ]
    er_relationships = [ ]
    name_set = set()                     # To prevent duplicate entity or enum names
    ignored_entity_node_ids = set()      # So you can ignore relationships to ignored entities
    node_id_to_entity_name = { }
    graph_elem = root.find(graph_tag)
    assert graph_elem is not None, 'Expected graph tag is not present'
    for graph_child in graph_elem:
        logger.debug(f'Next graph_child: tag={strip_namespace(graph_child.tag)}')
        logger.debug(ET.tostring(graph_child, encoding='utf8').decode('utf8'))
        continue_graph_elem_loop = False
        # We only care about nodes and edges
        if graph_child.tag != node_tag and graph_child.tag != edge_tag:
            logger.debug(f'Skipping non-node/non-edge graph_child.tag={graph_child.tag}')
            continue
        number_children_graph_child = cardinality.count(graph_child)
        # violated by yEd's default (unedited) entity:
        assert number_children_graph_child == 1, "Expected the graph element's child to have only one child"

        # The data element is a child of both node and edge elements
        data_elem = graph_child.find(data_tag)
        number_children_data = cardinality.count(data_elem)
        assert number_children_data == 1, 'Expected the data element to have only 1 child'

        data_subelem = data_elem[0]
        if graph_child.tag == node_tag:
            logger.debug('Found a node')
            node_elem = graph_child
            node_id = node_elem.attrib['id']
            if data_subelem.tag == GenericNode_tag:
                GenericNode_elem = data_subelem
                assert GenericNode_elem.attrib['configuration'] == GenericNode_attr_configuration_BigEntity, \
                    'Expected the generic node "configuration" attribute to indicate a BigEntity'
                logger.debug(f'GraphML entity node {node_id}:')
                for GenericNode_subelem in GenericNode_elem:
                    logger.debug(f'{i(1)}Found a GenericNode_subelem, tag={strip_namespace(GenericNode_subelem.tag)}')
                    if GenericNode_subelem.tag == NodeLabel_tag:
                        logger.debug(f'{i(1)}The GenericNode_subelem is a NodeLabel')
                        NodeLabel_elem = GenericNode_subelem
                        NodeLabel_attr_configuration = NodeLabel_elem.attrib['configuration']
                        if NodeLabel_attr_configuration == NodeLabel_attr_configuration_name:
                            entity_name = NodeLabel_elem.text
                            logger.debug(f'{i(1)}entity_name={entity_name}')
                            if entity_name in name_set:
                                print(f'\nERROR: Duplicate name specified: {entity_name}', file=sys.stderr)
                                sys.exit(1)
                            else:
                                name_set.add(entity_name)
                        elif NodeLabel_attr_configuration == NodeLabel_attr_configuration_attributes:
                            entity_attributes = NodeLabel_elem.text
                            logger.debug(f'{i(1)}entity_attributes={entity_attributes}')
                        else:
                            # The configuration attribute can have only 2 values
                            assert False, \
                            f'''Got an unexpected value for the "configuration" attribute of the '''
                            f'''node label element: {NodeLabel_attr_configuration}'''
                    elif GenericNode_subelem.tag == BorderStyle_tag:
                        logger.debug(f"{i(1)}GenericNode_subelem.attrib['type']={GenericNode_subelem.attrib['type']}")
                        if GenericNode_subelem.attrib['type'] != 'line':
                            logger.debug(f'{i(1)}Ignoring entity because the border is not a simple solid line')
                            ignored_entity_node_ids.add(node_id)  # So we can also ignore any edges to ignored entities
                            continue_graph_elem_loop = True
                            break
                    else:
                        logger.debug(f'{i(1)}Skipping a non-label/non-border-style: GenericNode_subelem.tag={GenericNode_subelem.tag}')
                        pass
                if continue_graph_elem_loop:
                    continue
                # Now that we have an entity name and attributes, process the attributes
                logger.debug(f'{i(1)}name: {entity_name}')
                try:
                    yaml_attrs = yaml.safe_load(entity_attributes)
                except (yaml.scanner.ScannerError, yaml.parser.ParserError) as ex:
                    print(f'\nERROR: Invalid YAML (syntax) for attributes section of ' \
                          f'the "{entity_name}" entity:\n\n' \
                          f'BEGIN>>>\n{entity_attributes}\n<<<END\n\n' \
                          f'ERROR DETAILS:\n{ex}\n', file=sys.stderr)
                    sys.exit(1)
                if yaml_attrs is None:
                    pass
                else:
                    logger.debug(f'{i(1)}YAML attributes:\n' + \
                        yaml.dump(yaml_attrs, default_flow_style=False))
                    try:
                        json_schema = json_schema_graphml_enum if entity_name.lower().startswith('enum') \
                            else json_schema_graphml_entity_attributes
                        jsonschema.validate(instance=yaml_attrs, schema=json_schema)
                    except jsonschema.exceptions.ValidationError as ex:
                        print(f'\nERROR: Invalid YAML (schema) for attributes section of ' \
                              f'the "{entity_name}" entity:\n\n' \
                              f'BEGIN>>>\n{entity_attributes}\n<<<END\n\n' \
                              f'ERROR DETAILS:\n{ex}\n', file=sys.stderr)
                        sys.exit(1)
                if entity_name.lower().startswith('enum'):
                    enum_contents = {} if yaml_attrs is None \
                                    else yaml_attrs if type(yaml_attrs) == type({}) \
                                    else { "values": yaml_attrs } if type(yaml_attrs) == type([]) \
                                    else None
                    assert enum_contents is not None, 'Unexpected contents for enum entity'
                    enum_contents.update( { "name": entity_name } )
                    enum = { "enum": enum_contents }
                    er_enums.append(enum)
                else:
                    entity_contents = {} if yaml_attrs is None else yaml_attrs
                    entity_contents.update( { "name": entity_name } )
                    entity = { "entity": entity_contents }
                    er_entities.append(entity)
                    node_id_to_entity_name.update( { node_id : entity_name } )
            else:
                logger.debug(f'Skipping a non-GenericNode: data_subelem.tag={data_subelem.tag}')
                pass  # Ignoring other kinds of nodes
        elif graph_child.tag == edge_tag:
            edge_elem = graph_child
            edge_id = edge_elem.attrib['id']
            logger.debug(f'Relationship {edge_id}')
            edge_source = edge_elem.attrib['source']
            edge_target = edge_elem.attrib['target']
            if edge_source in ignored_entity_node_ids:
                logger.debug(f'{i(1)}Ignoring relationship because source connects to an ignored entity. '
                             f'edge_source={edge_source}')
                continue 
            if edge_target in ignored_entity_node_ids:
                logger.debug(f'{i(1)}Ignoring relationship because target connects to an ignored entity. '
                             f'edge_target={edge_target}')
                continue 
            entity_source = node_id_to_entity_name[edge_source]
            entity_target = node_id_to_entity_name[edge_target]
            logger.debug(f'{i(1)}edge_source={edge_source}\tentity_source={entity_source}')
            logger.debug(f'{i(1)}edge_target={edge_target}\tentity_target={entity_target}')
            if data_subelem.tag == PolyLineEdge_tag:
                PolyLineEdge_elem = data_subelem
                LineStyle_elem = PolyLineEdge_elem.find(LineStyle_tag)
                edge_LineStyle_width = LineStyle_elem.attrib['width']
                edge_LineStyle_type = LineStyle_elem.attrib['type']
                logger.debug(f'{i(1)}edge_LineStyle_width={edge_LineStyle_width} edge_LineStyle_type={edge_LineStyle_type}')
                if edge_LineStyle_type != 'line':
                    logger.debug(f'{i(1)}Ignoring relationship because it does not use a simple solid line')
                    continue
                Arrows_elem = PolyLineEdge_elem.find(Arrows_tag)
                arrow_source = Arrows_elem.attrib['source']
                arrow_target = Arrows_elem.attrib['target']
                end_kinds.add(arrow_source)
                end_kinds.add(arrow_target)
                logger.debug(f'{i(1)}arrows: source={arrow_source} target={arrow_target}')
                kind_source = arrow_source
                kind_target = arrow_target
                is_defining = False

                if arrow_source == 'white_delta':
                    logger.debug(f"{i(1)}inside branch: arrow_source == 'white_delta'")
                    assert arrow_target == 'none', 'Unexpected edge target {arrow_target} for arrow source {arrow_source}'
                    kind_source = 'base_class'
                    kind_target = 'subclass'
                    is_defining = True
                if arrow_target == 'white_delta':
                    logger.debug(f"{i(1)}inside branch: arrow_target == 'white_delta'")
                    assert arrow_source == 'none', 'Unexpected edge source {arrow_source} for arrow target {arrow_target}'
                    kind_target = 'base_class'
                    kind_source = 'subclass'
                    is_defining = True

                if arrow_source == 'crows_foot_one':
                    kind_source = 'one'
                if arrow_target == 'crows_foot_one':
                    kind_target = 'one'

                if arrow_source == 'crows_foot_one_optional':
                    kind_source = 'zero_or_one'
                if arrow_target == 'crows_foot_one_optional':
                    kind_target = 'zero_or_one'

                if arrow_source == 'crows_foot_many_optional':
                    kind_source = 'zero_or_more'
                if arrow_target == 'crows_foot_many_optional':
                    kind_target = 'zero_or_more'

                relationship = { 
                    "relationship": { 
                        "participants": [
                            { "name": entity_source,
                              "kind": kind_source },
                            { "name": entity_target,
                              "kind": kind_target }
                        ]
                    }
                }
                if edge_LineStyle_width == '3.0':    # make more general
                    if kind_source != 'one' and kind_target != 'one':
                        print(f'\nERROR: Expected an end of a defining relationship to have a cardinality of "one".  '
                              f'Instead, found cardinalities of "{kind_source}" for entity "{entity_source}" '
                              f'and "{kind_target}" for entity "{entity_target}".')
                        sys.exit(1)
                    is_defining = True
                if is_defining:
                    relationship['relationship'].update({'defining': 'true'})
                logger.debug(f'{i(1)}new relationship: {relationship}')
                er_relationships.append(relationship)
            else:
                logger.debug(f'Skipping a non-PolyLineEdge: data_subelem.tag={data_subelem.tag}')
                pass  # Ignoring other kinds of edges
        else:
            assert False, f'Expected either a node or an edge, found: {graph_child.tag}'
        
    er.update( { "entities": er_entities } )
    er.update( { "relationships": er_relationships } )
    er.update( { "enums": er_enums } )
    print(yaml.dump(er), file=output_object)
    logger.debug(f'relationship end kinds: {end_kinds}')
    logger.debug('Leaving generml()')


@click.command()
@click.option(
    '--input',
    default='-',
    help='Input GraphML file (default is standard input, also represented by a dash "-")',
)
@click.option(
    '--output',
    default='-',
    help='Output ERML file (default is standard output, also represented by a dash "-")',
)
@click.option(
    '--overwrite',
    is_flag=True,
    default=False,
    help='If specified, overwrite the output file if it already exists',
)
@click.option(
    '--logging',
    type=str,
    default='WARNING',
    help='Set logging to the specified level: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL',
)
@logger.catch
def main(input, output, overwrite, logging):
    '''
    Read an Entity-Relationship diagram created by the yEd graph editor and 
    convert it into Entity-Relationship Markup Language

    \b
    References:
    yEd - https://www.yworks.com/products/yed
    GraphML - http://graphml.graphdrawing.org/index.html
    '''

    if logging != 'WARNING':
        # Remove default logger to reset logging level from the previously-set level of WARNING to 
        # something else per https://github.com/Delgan/loguru/issues/51
        logger.remove(loguru_handler_id)
        logger.add(sys.stderr, level=logging)

    logger.debug('Entering main()')
    logger.info(f'click version is {click.__version__}')
    logger.debug(
        f'parameters: input={input} output={output} overwrite={overwrite} logging={logging}'
    )

    if input == '-':
        input_file_or_object = sys.stdin
    else:
        if os.path.exists(input):
            input_file_or_object = input
        else:
            print(f'Error: Specified input file does not exist: {input}', file=sys.stderr)
            sys.exit(1)

    if output == '-':
        output_object = sys.stdout
    else:
        if overwrite == False and os.path.exists(output):
            print(f'Error: Specified output file already exists: {output}', file=sys.stderr)
            sys.exit(1)

        try:
            output_object = open(output, 'w')
        except IOError as ex:
            print(f'ERROR: Unable to write to the specified output file {output}.\n'
                  f'Details: {ex}', file=sys.stderr)
            sys.exit(1)

    generml(input_file_or_object, input, output_object)

    if output != '-':
        output_object.close()
    logger.debug('Leaving main()')
    

if __name__ == "__main__":
    try:
        # Remove default logger to reset logging level from the default of DEBUG to something else
        # per https://github.com/Delgan/loguru/issues/51
        logger.remove(0)
        global loguru_handler_id
        loguru_handler_id = logger.add(sys.stderr, level='WARNING')

        main()
    finally:
        logger.info(f'exiting {__name__}')
