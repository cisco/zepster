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


Program to generate a database schema (table definitions, etc.)
from an Entity-Relationship Markup Language (ERML) file.

Usage: genschema.py [OPTIONS]

  Read an Entity-Relationship Markup Language file and write a database
  schema SQL file

Options:
  --input TEXT                    Input Entity-Relationship Markup Language
                                  file (default is standard input, also
                                  represented by a dash "-")

  --output TEXT                   Output schema definition file (default is
                                  standard output, also represented by a dash
                                  "-")

  --overwrite                     If specified, overwrite the output file if
                                  it already exists

  --logging TEXT                  Set logging to the specified level: NOTSET,
                                  DEBUG, INFO, WARNING, ERROR, CRITICAL

  --dialect [CRDB|RS]             Set the database dialect: "CRDB" for
                                  CockroachDB [Not implemented: and "RS" for
                                  Redshift].

  --generate-keys                 [Not implemented] Indicates whether to
                                  generate synthetic keys.  Default is True.

  --generated-key-type [INTEGER|UUID]
                                  Set the data type for generated synthetic
                                  keys.  The default depends on the database
                                  dialect: UUID for CockroachDB [Not
                                  implemented: and INTEGER for Redshift].

  --help                          Show this message and exit.
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
    Generate the schema definitions and data for enum tables
    '''
    logger.debug('Entering generate_enums()')
    for enum_table in er_yaml['enums']:
        logger.debug(f'enum_table={enum_table}')
        enum_table_name = enum_table['enum']['name']
        logger.debug(f'enum_table_name={enum_table_name}')
        if 'description' in enum_table['enum']:
            print('-- Description:', file=output_object)
            enum_table_description = enum_table['enum']['description']
            for line in enum_table_description.splitlines():
                print(f'-- {line}', file=output_object)
        if 'note' in enum_table['enum']:
            if 'description' in enum_table['enum']:
                print(file=output_object)
            print('-- Note:', file=output_object)
            enum_table_note = enum_table['enum']['note']
            for line in enum_table_note.splitlines():
                print(f'-- {line}', file=output_object)
        print(f'create table {enum_table_name} (pk integer primary key, name varchar(500));', file=output_object)
        for ordinal, enum_value_or_more in enumerate(enum_table['enum']['values']):
            logger.debug(f'{i(1)}enum_value_or_more={enum_value_or_more} type={type(enum_value_or_more)}')
            if type(enum_value_or_more) == type(''):
                logger.debug(f'{i(1)}Type is string')
                enum_value = enum_value_or_more
            elif type(enum_value_or_more) == type({}):
                logger.debug(f'{i(1)}Type is dictionary')
                enum_value = enum_value_or_more['value']
                if 'description' in enum_value_or_more:
                    print('-- Description:', file=output_object)
                    enum_value_description = enum_value_or_more['description']
                    for line in enum_value_description.splitlines():
                        print(f'-- {line}', file=output_object)
                if 'note' in enum_value_or_more:
                    print('-- Note:', file=output_object)
                    enum_value_note = enum_value_or_more['note']
                    for line in enum_value_note.splitlines():
                        print(f'-- {line}', file=output_object)
            else:
                raise ValueError(f'Enum value did not match expected type of string or '
                                 f'dicitonary for enum table "{enum_table_name}". '
                                 f'Value is {enum_value_or_more}')
            # escape to prevent SQL injection
            print(f"insert into {enum_table_name} (pk, name) values ({ordinal+1}, '{enum_value}');", file=output_object)
        print(file=output_object)
    logger.debug('Leaving generate_enums()')


@logger.catch
def generate_mm_synthesized(entity_name, graph, output_object):
    '''
    Generate DDL for synthesized many-to-many mapping table
    
    Assumes synthesized many-to-many mapping tables have no attributes
    This may change with future enhancement
    '''
    logger.debug('Entering generate_mm_synthesized()')
    graph_dependees = graph[entity_name]
    logger.debug(f'{i(1)}graph_dependees={graph_dependees}')
    print(f'create table {entity_name} (', file=output_object)
    print(f'{i(1)}pk uuid not null default gen_random_uuid() primary key,', file=output_object)
    num_parents = cardinality.count(graph_dependees)
    for dependee_num, dependee in enumerate(graph_dependees):
        column_line = f'{i(1)}fk_{dependee} uuid not null references {dependee}(pk) on delete cascade'
        if dependee_num < num_parents-1:
            column_line += ','
        print(column_line, file=output_object)
    print(');\n', file=output_object)
    logger.debug('Leaving generate_mm_synthesized()')


@logger.catch
def generate_entity_comments(entity_name, entities, entity_indices, entities_pc, output_object):
    '''
    Handle entity description and note
    '''
    logger.debug('Entering generate_entity_comments()')
    entity_index = entity_indices[entity_name]
    entity = entities[entity_index]['entity']
    logger.debug(f'entity=\n{yaml.dump(entity)}')

    num_parents = 0
    entity_pc = entities_pc[entity_name]
    logger.debug(f'{i(1)}entity_pc={entity_pc}')
    parents = None
    if 'parents' in entity_pc:
        parents = entity_pc['parents']
        num_parents = cardinality.count(parents)
    num_attributes = 0
    attributes = None
    if 'attributes' in entity:
        attributes = entity['attributes']
        num_attributes = cardinality.count(attributes)
    logger.debug(f'num_parents={num_parents} num_attributes={num_attributes}')

    if 'description' in entity:
        print('-- Description:', file=output_object)
        table_description = entity['description']
        for line in table_description.splitlines():
            print(f'-- {line}', file=output_object)
    if 'note' in entity:
        if 'description' in entity:
            print(file=output_object)
        print('-- Note:', file=output_object)
        table_note = entity['note']
        for line in table_note.splitlines():
            print(f'-- {line}', file=output_object)
        print(file=output_object)
    logger.debug('Leaving generate_entity_comments()')
    return entity, parents, num_parents, attributes, num_attributes


@logger.catch
def generate_foreign_keys(parents, num_parents, num_attributes, output_object):
    '''
    Generate DDL for foreign keys
    '''
    logger.debug('Entering generate_foreign_keys()')
    if num_parents >= 1:
        logger.debug('Generating DDL for foreign keys...')
        logger.debug(f'parents=\n{json.dumps(parents, indent=4)}')
        for parent_num, parent in enumerate(parents):
            logger.debug(f'{i(1)}parent_num={parent_num} parent={parent}')
            assert cardinality.count(parent) == 1
            for parent_name, parent_vals in parent.items():
                pass
            parent_kind = parent_vals['kind']
            is_defining = False
            if 'defining' in parent_vals:
                if parent_vals['defining'] == True:
                    is_defining = True
            logger.debug(f'{i(1)}is_defining={is_defining}')
            column_line = f'{i(1)}{"fk_" + parent_name} uuid '
            if parent_kind in ['one', 'base_class']:
                column_line += 'not null '
            column_line += f'references {parent_name}(pk)'
            if is_defining:
                column_line += ' on delete cascade'
            elif parent_kind == 'zero_or_one':
                column_line += ' on delete set null'
            logger.debug(f'{i(1)}column_line={column_line}')
            if parent_num < num_parents-1 or num_attributes > 0:
                column_line += ','
            logger.debug(f'column_line={column_line}')
            print(f'{column_line}', file=output_object)
    logger.debug('Leaving generate_foreign_keys()')


@logger.catch
def generate_attribute_columns(attributes, num_attributes, output_object):
    '''
    Generate DDL for attributes
    '''
    logger.debug('Entering generate_attribute_columns()')
    if num_attributes > 0:
        logger.debug(f"type(attributes)={type(attributes)}")
        logger.debug(f"attributes={attributes}") 
        for current_attribute_num, attribute_key_values in enumerate(attributes.items()):
            logger.debug(f'current_attribute_num={current_attribute_num} attribute_key_values={attribute_key_values}')
            attribute_key = attribute_key_values[0]
            attribute_values = attribute_key_values[1]
            logger.debug(f'attribute_key={attribute_key} attribute_values={attribute_values}')
            if 'description' in attribute_values:
                print(f'{i(1)}-- Description:', file=output_object)
                attribute_description = attribute_values['description']
                for line in attribute_description.splitlines():
                    print(f'{i(1)}-- {line}', file=output_object)
            if 'note' in attribute_values:
                print(f'{i(1)}-- Note:', file=output_object)
                attribute_note = attribute_values['note']
                for line in attribute_note.splitlines():
                    print(f'{i(1)}-- {line}', file=output_object)
            logger.debug(f'{i(1)}attribute_key={attribute_key} attribute_values={attribute_values}')
            assert 'type' in attribute_values
            attribute_type = attribute_values['type']
            column_type = f'integer references {"enum_" + attribute_key + "(pk)"}' if attribute_type == 'enum' else attribute_type
            column_line = f'{i(1)}{attribute_key} {column_type}'
            logger.debug(f'column_line={column_line}')
            if 'required' in attribute_values:
                if attribute_values['required'] == True:
                    column_line += ' not null'
            if 'unique' in attribute_values:
                if attribute_values['unique'] == True:
                    column_line += ' unique'     # handle unique-within-parent
            logger.debug(f'num_attributes={num_attributes} current_attribute_num={current_attribute_num}')
            if current_attribute_num < num_attributes - 1:
                column_line += ','
            print(column_line, file=output_object)
    else:
        logger.debug('Skipping attributes because no attributes')
    logger.debug('Leaving generate_attribute_columns()')


@logger.catch
def generate_entities(er_yaml, output_object):
    '''
    Generate the schema definitions for entity tables and many-to-many mapping tables
    '''
    logger.debug('Entering generate_entities()')
    # Topologically sort the entities (so we can do foreign key constraints correctly)
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
    for entity_index, entity_obj in enumerate(entities):
        logger.debug(f'entity_index={entity_index} for entity:\n{yaml.dump(entity_obj)}')
        entity_indices.update( { entity_obj['entity']['name']: entity_index } )
    logger.debug(f'entity_indices={entity_indices}')

    # Generate table definitions for entities
    for entity_name in dependency_ordering:
        logger.debug(f'Generating table for {entity_name}')
        if entity_name in mm_synthesized:
            generate_mm_synthesized(entity_name, graph, output_object)
        else:
            entity, parents, num_parents, attributes, num_attributes = \
                generate_entity_comments(entity_name, entities, entity_indices, entities_pc, output_object)

            # Start the DDL to create the table
            print(f'create table {entity_name} (', file=output_object)
            column_line = f'{i(1)}pk uuid not null default gen_random_uuid() primary key'
            if num_parents > 0 or num_attributes > 0:
                column_line += ','
            print(column_line, file=output_object)
           
            generate_foreign_keys(parents, num_parents, num_attributes, output_object) 
            generate_attribute_columns(attributes, num_attributes, output_object)
            print(f');\n', file=output_object)

    # Generate drop table statements in proper order
    print('\n\n', file=output_object)
    for table_name in reversed(dependency_ordering):
        print(f'-- drop table if exists {table_name};', file=output_object)
    for enum in er_yaml['enums']:
        enum_table_name = enum['enum']['name']
        print(f'-- drop table if exists {enum_table_name};', file=output_object)
    logger.debug('Leaving generate_entities()')


@logger.catch
def genschema(er_yaml, input, output_object):
    '''
    Generally-callable entry point to 
    read an Entity-Relationship Markup Language file and write a database schema SQL file
    '''
    logger.debug('Entering genschema()')
    logger.debug('Before validating YAML via jsonschema.validate()')
    try:
        jsonschema.validate(instance=er_yaml, schema=json_schema_erml)
    except jsonschema.exceptions.ValidationError as ex:
        print(f'\nERROR: Invalid YAML (schema) for Entity-Relationship Markup Language input file.\n'
              f'ERROR DETAILS:\n{ex}\n', file=sys.stderr)
        sys.exit(1)
    logger.debug('After jsonschema.validate()')

    print(f'-- Database schema generated by Zepster', file=output_object)
    print(f'-- Source: {"stdin" if input == "-" else input}', file=output_object)
    print(f'-- Generated: {datetime.datetime.utcnow().isoformat()}', file=output_object)
    print(file=output_object)

    generate_enums(er_yaml, output_object)
    generate_entities(er_yaml, output_object)
    logger.debug('Leaving genschema()')


@click.command()
@click.option(
    '--input',
    default='-',
    help='Input Entity-Relationship Markup Language file (default is standard input, also represented by a dash "-")',
)
@click.option(
    '--output',
    default='-',
    help='Output schema definition file (default is standard output, also represented by a dash "-")',
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
    '--dialect',
    type=click.Choice(['CRDB', 'RS'], case_sensitive=False),
    default='CRDB',
    help='Set the database dialect: "CRDB" for CockroachDB [Not implemented: and "RS" for Redshift].',
)
@click.option(
    '--generate-keys',
    is_flag=True,
    default=True,
    help='[Not implemented] Indicates whether to generate synthetic keys.  Default is True.'
)
@click.option(
    '--generated-key-type',
    type=click.Choice(['INTEGER', 'UUID'], case_sensitive=False),
    help='Set the data type for generated synthetic keys.  The default depends on '
         'the database dialect: UUID for CockroachDB [Not implemented: and INTEGER for Redshift].',
)
@logger.catch
def main(input, output, overwrite, logging, dialect, generate_keys, generated_key_type):
    '''
    Read an Entity-Relationship Markup Language file and write a database schema SQL file
    '''

    if logging != 'WARNING':
        # Remove default logger to reset logging level from the previously-set level of WARNING to 
        # something else per https://github.com/Delgan/loguru/issues/51
        logger.remove(loguru_handler_id)
        logger.add(sys.stderr, level=logging)

    logger.debug('Entering main()')
    logger.info(f'click version is {click.__version__}')
    logger.debug(
        f'parameters: input={input} output={output} overwrite={overwrite} logging={logging} dialect={dialect} '
        f'generate_keys={generate_keys} generated_key_type={generated_key_type}'
    )

    # TODO: Additional options implementimplement
    if generated_key_type is None:
        generated_key_type = 'UUID'     # TODO: make default dependent on dialect
    if generated_key_type.upper() == 'INTEGER':
        print(f'Error: The value of "INTEGER" for the --generated-key-type option is not implemented yet.', file=sys.stderr)
        sys.exit(1)
    if dialect.upper() == 'RS':
        print(f'Error: The value of "RS" for the --dialect option is not implemented yet.', file=sys.stderr)
        sys.exit(1)
    if generate_keys == False:
        print(f'Error: The --generate-keys option is not implemented yet.  '
               'Remove the option to specify the default of generating synthetic keys.', file=sys.stderr)
        sys.exit(1)

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

    genschema(er_yaml, input, output_object)

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
