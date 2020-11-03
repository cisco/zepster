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


Utilities for Zepster
'''

from loguru import logger
import cardinality
import json
import yaml
from toposort import toposort_flatten


def i(level):
    '''
    Create a string to indent the specified number of levels
    '''
    level_size = 2
    return ' ' * level_size * level


@logger.catch
def topological_sort_entities(er_yaml):
    '''
    Topologically sort the entities (so we can do foreign key constraints correctly)
    and create info on synthesized many-to-many mapping tables.
    ref: https://pypi.org/project/toposort/
    '''
    logger.debug('Entering topological_sort_entities()')
    # Populate the graph with empty sets of dependents
    graph = { }
    mm_synthesized = set()                 # Many-to-many mapping tables inferred from m:m relationships
    for relationship in er_yaml['relationships']:
        for participant in relationship['relationship']['participants']:
            graph.update( { participant['name']: set() } )
    logger.debug(f'Initial empty dependency graph:\n{yaml.dump(graph)}')
    # Identify and store the dependents
    for relationship in er_yaml['relationships']:
        participants = relationship['relationship']['participants']
        p0 = participants[0]
        p1 = participants[1]
        logger.debug(f'p0={p0} p1={p1}')
        lex_first = p0['name'] if p0['name'] < p1['name'] else p1['name']
        lex_last = p1['name'] if p0['name'] == lex_first else p0['name']
        if p0['kind']  in [ 'one', 'zero_or_one' ]:
            if p1['kind'] in [ 'one', 'zero_or_one' ]:
                # if self loop then skip
                if p0['name'] == p1['name']:
                    logger.debug(f'{i(1)}Self loop so skipping')
                    continue
                # else make later lexically depend on former lexically
                logger.debug(f'{i(1)}Making latter lexically depend on former lexically')
                graph[lex_last].add(lex_first)
            elif p1['kind'] == 'zero_or_more':
                # make p1 depend on p0
                logger.debug(f'{i(1)}Making p1 depend on p0')
                graph[p1['name']].add(p0['name'])
            else:
                assert False
        elif p0['kind'] == 'zero_or_more':
            if p1['kind'] in [ 'one', 'zero_or_one' ]:
                # make p0 depend on p1
                logger.debug(f'{i(1)}Making p0 depend on p1')
                graph[p0['name']].add(p1['name'])
            elif p1['kind'] == 'zero_or_more':
                # create a new mm node
                mm_name = '_' + lex_first + '_mm_' + lex_last
                logger.debug(f'{i(1)}Creating a new many-many mapping node "{mm_name}" and making it depend on both p0 and p1')
                mm_synthesized.add(mm_name)
                graph.update( { mm_name: set([lex_first, lex_last]) } )
            else:
                assert False
        elif p0['kind'] == 'base_class':
            if p1['kind'] == 'subclass':
                # make p1 depend on p0  (assumes table-per-level inheritance)
                logger.debug(f'{i(1)}Making p1 depend on p0')
                graph[p1['name']].add(p0['name'])
            else:
                assert False
        elif p0['kind'] == 'subclass':
            if p1['kind'] == 'base_class':
                # make p0 depend on p1  (assumes table-per-level inheritance)
                logger.debug(f'{i(1)}Making p0 depend on p1')
                graph[p0['name']].add(p1['name'])
            else:
                assert False
    dependency_ordering = toposort_flatten(graph)
    logger.debug('')
    logger.debug(f'Final dependency graph:\n{yaml.dump(graph)}')
    logger.debug(f'dependency_ordering:\n{json.dumps(dependency_ordering, indent=4)}')
    logger.debug(f'mm_synthesized:\n{mm_synthesized}')
    logger.debug('Leaving topological_sort_entities()')
    return graph, dependency_ordering, mm_synthesized


@logger.catch
def build_entity_parents_and_children(er_yaml):
    '''
    Build parents and children for each entity

    Relationship kinds:
     base_class      parent
     one             parent
     subclass        child
     zero_or_more    child
     zero_or_one     parent
    '''
    logger.debug('Entering build_entity_parents_and_children()')
    entities_pc = {}
    for relationship_outer in er_yaml['relationships']:
        logger.debug(f'relationship_outer={relationship_outer}')
        relationship = relationship_outer['relationship']
        logger.debug(f'relationship={relationship}')
        is_defining = False
        if 'defining' in relationship:
            if relationship['defining'] == 'true':
                is_defining = True
        logger.debug(f'is_defining={is_defining}')
        participants = relationship['participants']
        logger.debug(f'participants={participants}')
        assert cardinality.count(participants) == 2
        for participant_index, participant in enumerate(participants):
            logger.debug(f'{i(1)}participant_index={participant_index} participant={participant}')
            other_participant_index = 1 if participant_index == 0 else 0
            participant_name = participant['name']
            participant_kind = participant['kind']
            logger.debug(f'{i(2)}participant_name={participant_name} participant_kind={participant_kind}')
            other_participant = participants[other_participant_index]
            logger.debug(f'{i(2)}other_participant_index={other_participant_index} other_participant={other_participant}')
            other_participant_name = other_participant['name']
            other_participant_kind = other_participant['kind']
            logger.debug(f'{i(2)}other_participant_name={other_participant_name} other_participant_kind={other_participant_kind}')
            if participant_name in entities_pc:
                logger.debug(f'{i(2)}Using existing participating_entity_pc')
                participating_entity_pc = entities_pc[participant_name]
            else:
                logger.debug(f'{i(2)}Making new participating_entity_pc')
                participating_entity_pc = {}
                entities_pc.update( { participant_name: participating_entity_pc } )
            logger.debug(f'{i(2)}participating_entity_pc={participating_entity_pc}')
            if participant_kind in ['zero_or_more', 'subclass']:
                logger.debug(f"{i(2)}TRUE: participant_kind in ['zero_or_more', 'subclass']")
                if participant_kind == 'zero_or_more' and other_participant_kind == 'zero_or_more':
                    logger.debug('Skipping many-to-many relationship as it is handled elsewhere')
                    continue
                if 'parents' in participating_entity_pc:
                    logger.debug(f'{i(2)}Using existing participating_entity_pc_parents')
                    participating_entity_pc_parents = participating_entity_pc['parents']
                else:
                    logger.debug(f'{i(2)}Making new participating_entity_pc_parents')
                    participating_entity_pc_parents = []
                    participating_entity_pc.update( { 'parents': participating_entity_pc_parents } )
                participating_entity_pc_parents.append( { other_participant_name: { 'kind': other_participant_kind, 'defining': is_defining } } )
                logger.debug(f'{i(2)}participating_entity_pc_parents={participating_entity_pc_parents}')
            elif participant_kind in ['one', 'zero_or_one', 'base_class']:
                logger.debug(f"{i(2)}TRUE: participant_kind in ['one', 'zero_or_one', 'base_class']")
                if 'children' in participating_entity_pc:
                    logger.debug(f'{i(2)}Using existing participating_entity_pc_children')
                    participating_entity_pc_children = participating_entity_pc['children']
                else:
                    logger.debug(f'{i(2)}Making new participating_entity_pc_children')
                    participating_entity_pc_children = []
                    participating_entity_pc.update( { 'children': participating_entity_pc_children } )
                participating_entity_pc_children.append( { other_participant_name: { 'kind': other_participant_kind, 'defining': is_defining } } )
                logger.debug(f'{i(2)}participating_entity_pc_children={participating_entity_pc_children}')
            else:
                assert False
    logger.debug('Leaving build_entity_parents_and_children()')
    return entities_pc
