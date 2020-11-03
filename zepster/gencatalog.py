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


Program to generate a data catalog
from an Entity-Relationship Markup Language (ERML) file.

Usage: gencatalog.py [OPTIONS]

  Read an Entity-Relationship Markup Language
  file and write a data catalog output file

Options:
  --input TEXT    Input Entity-Relationship Markup Language file (default is
                  standard input, also represented by a dash "-")
  --output TEXT   Output catalog file (default is standard output, also
                  represented by a dash "-")
  --overwrite     If specified, overwrite the output file if it already exists
  --logging TEXT  Set logging to the specified level: NOTSET, DEBUG, INFO,
                  WARNING, ERROR, CRITICAL
  --format TEXT   Set the catalog format: (currently only "md")
  --help          Show this message and exit.
'''

import sys
import os.path
from loguru import logger
import click
import cardinality
import yaml
import jsonschema
import datetime
from json_schema_erml import json_schema_erml
import json
from util import i, topological_sort_entities, build_entity_parents_and_children


@logger.catch
def generate_enums(er_yaml, output_object):
    '''
    Generate the catalog doc for the enums
    '''
    logger.debug('Entering generate_enums()')
    enums = er_yaml['enums']
    logger.debug(f"enums=\n{json.dumps(enums, indent=4)}")

    # Index the enums
    enum_indices = { }
    for enum_index, enum_outer in enumerate(enums):
        enum = enum_outer['enum']
        logger.debug(f'enum_index={enum_index} for enum:\n{yaml.dump(enum)}')
        enum_indices.update( { enum['name']: enum_index } )
    logger.debug(f'enum_indices=\n{json.dumps(enum_indices, indent=4)}')

    klist = list(enum_indices.keys()).copy()
    klist.sort()
    for enum_name in klist:
        enum_index = enum_indices[enum_name]
        enum_outer = enums[enum_index]
        enum = enum_outer['enum']
        logger.debug(f'enum_index={enum_index} enum={enum}')
        print('---', file=output_object)
        print(f'## {enum_name}\n', file=output_object)
        if 'description' in enum:
            print('**Description:**  ', file=output_object)
            enum_description = enum['description']
            for line in enum_description.splitlines():
                print(f'{line}  ', file=output_object)
        if 'note' in enum:
            print('**Note:**  ', file=output_object)
            enum_note = enum['note']
            for line in enum_note.splitlines():
                print(f'{line}  ', file=output_object)
        if 'description' in enum or 'note' in enum:
            print(file=output_object)
        print(f'PK | Name | Description | Note', file=output_object)
        print(f'-- | ---- | ----------- | ----', file=output_object)
        for ordinal, enum_value_or_more in enumerate(enum['values']):
            logger.debug(f'{i(1)}enum_value_or_more={enum_value_or_more} type={type(enum_value_or_more)}')
            enum_value_description = ''
            enum_value_note = ''
            if type(enum_value_or_more) == type(''):
                logger.debug(f'{i(1)}Type is string')
                enum_value = enum_value_or_more
            elif type(enum_value_or_more) == type({}):
                logger.debug(f'{i(1)}Type is dictionary')
                enum_value = enum_value_or_more['value']
                if 'description' in enum_value_or_more:
                    enum_value_description = enum_value_or_more['description']
                    #for line in enum_value_description.splitlines():
                    #    print(f'-- {line}', file=output_object)
                if 'note' in enum_value_or_more:
                    enum_value_note = enum_value_or_more['note']
                    #for line in enum_value_note.splitlines():
                    #    print(f'-- {line}', file=output_object)
            else:
                raise ValueError(f'Enum value did not match expected type of string or '
                                 f'dictionary for enum table "{enum_name}". '
                                 f'Value is {enum_value_or_more}')
            print(f'{ordinal+1} | {enum_value} | {enum_value_description} | {enum_value_note}', file=output_object) 
        print(file=output_object)
    logger.debug('Leaving generate_enums()')


@logger.catch
def generate_entities(er_yaml, output_object):
    '''
    Generate the data catalog info for entity tables
    '''
    logger.debug('Entering generate_entities()')
    # Topologically sort the entities (so we can get the synthesized many-to-many mapping tables)
    graph, dependency_ordering, mm_synthesized = topological_sort_entities(er_yaml)
    logger.debug(f'graph={graph}')
    logger.debug(f'dependency_ordering={dependency_ordering}')
    logger.debug(f'mm_synthesized={mm_synthesized}')
 
    entities_pc = build_entity_parents_and_children(er_yaml)
    logger.debug(f'after build_entity_parents_and_children(): entities_pc={json.dumps(entities_pc, indent=4)}')

    entities = er_yaml['entities']
    logger.debug(f'entities={yaml.dump(entities)}')

    # Index the entities
    entity_indices = { }
    for entity_index, entity_outer in enumerate(entities):
        entity = entity_outer['entity']
        logger.debug(f'entity_index={entity_index} for entity:\n{yaml.dump(entity)}')
        entity_indices.update( { entity['name']: entity_index } )
    logger.debug(f'entity_indices=\n{json.dumps(entity_indices, indent=4)}')

    # Generate catalog info for entities
    klist = list(entity_indices.keys()).copy()
    klist.sort()
    for entity_name in klist:
        entity_index = entity_indices[entity_name]
        entity_outer = entities[entity_index]
        entity = entity_outer['entity']
        logger.debug(f'Generating catalog info for: entity_index={entity_index} entity={entity}')

        print('---', file=output_object)
        print(f'## {entity_name}\n', file=output_object)
        if 'description' in entity:
            print('**Description:**  ', file=output_object)
            entity_description = entity['description']
            for line in entity_description.splitlines():
                print(f'{line}  ', file=output_object)
        if 'note' in entity:
            print('**Note:**  ', file=output_object)
            entity_note = entity['note']
            for line in entity_note.splitlines():
                print(f'{line}  ', file=output_object)
        if 'attributes' in entity:
            if 'description' in entity or 'note' in entity:
                print(file=output_object)
            print('### Columns:', file=output_object)
            print(f'\nNum | Name | Type | Unique | Description | Note', file=output_object)
            print(f'--- | ---- | ---- | ------ | ----------- | ----', file=output_object)
            for ordinal, attr_items in enumerate(entity['attributes'].items()):
                attr_name = attr_items[0]
                attr_details = attr_items[1]
                logger.debug(f'{i(1)}attr_name={attr_name} attr_details={attr_details}')
                attr_type = attr_details['type'] if 'type' in attr_details else ''
                attr_unique = attr_details['unique'] if 'unique' in attr_details else ''
                attr_description = attr_details['description'] if 'description' in attr_details else ''
                attr_note = attr_details['note'] if 'note' in attr_details else ''
                print(f'{ordinal+1} | {attr_name} | {attr_type} | {attr_unique} | {attr_description} | {attr_note}', file=output_object)

        # Generate relationships section
        parents_count = 0
        children_count = 0
        mm_count = 0
        if entity_name in entities_pc:
            entity_pc = entities_pc[entity_name]
            if 'parents' in entity_pc:
                parents = entity_pc['parents']
                parents_count = cardinality.count(parents)
            if 'children' in entity_pc:
                children = entity_pc['children']
                children_count = cardinality.count(children)
        mm_participating = set()
        for mm in mm_synthesized:
            if entity_name in graph[mm]:
                mm_participating.add(mm) 
        mm_count = cardinality.count(mm_participating)
        logger.debug(f'mm_participating={mm_participating}')
        logger.debug(f'parents_count={parents_count} children_count={children_count} mm_count={mm_count}')
        if (parents_count >= 1 or children_count >= 1 or mm_count >= 1) and \
            ('description' in entity or 'note' in entity or 'attributes' in entity):
            print(file=output_object)
        if parents_count >= 1 or children_count >= 1:
            print('### Relationships:', file=output_object)
        if parents_count >= 1:
            print('#### Parents', file=output_object )
            print('Name | Kind | Defining', file=output_object )
            print('---- | ---- | --------', file=output_object )
            for parent in parents:
                assert cardinality.count(parent) == 1
                for parent_name, parent_details in parent.items():
                    pass
                logger.debug(f'parent_name={parent_name} parent_details={parent_details}')
                relationship_kind = parent_details['kind']
                is_defining = parent_details['defining'] if 'defining' in parent_details else False
                print(f'{parent_name} | {relationship_kind} | {is_defining}', file=output_object)
        if children_count >= 1:
            print('#### Children', file=output_object )
            print('Name | Kind | Defining', file=output_object )
            print('---- | ---- | --------', file=output_object )
            for child in children:
                assert cardinality.count(child) == 1
                for child_name, child_details in child.items():
                    pass
                logger.debug(f'child_name={child_name} child_details={child_details}')
                relationship_kind = child_details['kind']
                is_defining = child_details['defining'] if 'defining' in child_details else False
                print(f'{child_name} | {relationship_kind} | {is_defining}', file=output_object)
        if mm_count >= 1:
            print('#### Many-to-Many Relationships', file=output_object )
            print('Other Entity Name | Kind', file=output_object )
            print('----------------- | ----', file=output_object )
            for mm in mm_participating:
                for participant in graph[mm]:
                    if participant == entity_name:
                        continue
                    print(f'{participant} | zero_or_more', file=output_object)
        print(file=output_object)
    logger.debug('Leaving generate_entities()')


@logger.catch
def gencatalog(er_yaml, input, output_object):
    '''
    Generaly callable entry point to read an Entity-Relationship Markup Language file and write a data catalog output file
    '''
    logger.debug('Entering gencatalog()')
    logger.debug('Before validating YAML via jsonschema.validate()')
    try:
        jsonschema.validate(instance=er_yaml, schema=json_schema_erml)
    except jsonschema.exceptions.ValidationError as ex:
        print(f'\nERROR: Invalid YAML (schema) for Entity-Relationship Markup Language input file.\n'
              f'ERROR DETAILS:\n{ex}\n', file=sys.stderr)
        sys.exit(1)
    logger.debug('After jsonschema.validate()')

    print(f'# Entity Summary', file=output_object)
    print(f'Generated by Zepster  ', file=output_object)
    print(f'Source: {"stdin" if input == "-" else input}  ', file=output_object)
    print(f'Generated: {datetime.datetime.utcnow().isoformat()}', file=output_object)
    print(file=output_object)

    generate_enums(er_yaml, output_object)
    generate_entities(er_yaml, output_object)
    logger.debug('Leaving gencatalog()')


@click.command()
@click.option(
    '--input',
    default='-',
    help='Input Entity-Relationship Markup Language file (default is standard input, also represented by a dash "-")',
)
@click.option(
    '--output',
    default='-',
    help='Output catalog file (default is standard output, also represented by a dash "-")',
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
@click.option(
    '--format',
    type=str,
    default='md',
    help='Set the catalog format: (currently only "md")',
)
@logger.catch
def main(input, output, overwrite, logging, format):
    '''
    Read an Entity-Relationship Markup Language file and write a data catalog output file
    '''

    if logging != 'WARNING':
        # Remove default logger to reset logging level from the previously-set level of WARNING to 
        # something else per https://github.com/Delgan/loguru/issues/51
        logger.remove(loguru_handler_id)
        logger.add(sys.stderr, level=logging)

    logger.debug('Entering main()')
    logger.info(f'click version is {click.__version__}')
    logger.debug(
        f'parameters: input={input} output={output} overwrite={overwrite} logging={logging} format={format}'
    )

    close_input_object = False
    close_output_object = False

    if output == '-':
        output_object = sys.stdout
    else:
        if overwrite == False and os.path.exists(output):
            print(f'Error: Specified output file already exists: {output}', file=sys.stderr)
            sys.exit(1)

        try:
            output_object = open(output, 'w')
            close_output_object = True
        except IOError as ex:
            print(f'ERROR: Unable to write to the specified output file {output}.\n'
                  f'Details: {ex}', file=sys.stderr)
            sys.exit(1)

    if input == '-':
        input_object = sys.stdin
    else:
        if os.path.exists(input):
            try:
                input_object = open(input, 'r')
                close_input_object = True
            except IOError as ex:
                print(f'ERROR: Unable to read the specified input file {input}.\n'
                      f'Details: {ex}', file=sys.stderr)
                sys.exit(1)
        else:
            print(f'Error: Specified input file does not exist: {input}', file=sys.stderr)
            sys.exit(1)

    logger.debug('Before reading YAML via yaml.safe_load()')
    try:
        er_yaml = yaml.safe_load(input_object)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as ex:
        print(f'\nERROR: Invalid YAML (syntax) for Entity-Relationship Markup Language input file.\n'
              f'ERROR DETAILS:\n{ex}\n', file=sys.stderr)
        sys.exit(1)
    logger.debug('After yaml.safe_load()')

    gencatalog(er_yaml, input, output_object)

    if close_input_object:
        input_object.close()
    if close_output_object:
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
