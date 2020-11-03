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


JSON schemas for the YAML that specifies various kinds of information
in the Entity-Relationship diagram created in the yEd graph editor
'''


json_schema_graphml_entity_attributes = {
    '$schema': 'http://json-schema.org/schema#',
    '$id': 'http://cisco.com/zepster.graphml_entity_attributes.schema.json', \
    'title': 'ZepstER schema for format of the attribute block in an entity in yEd', \
    'description': 'In the yEd graph editor, using the E-R (Entity-Relationship) diagram, ' \
                   'an entity has two strings: an entity name and a string to represent ' \
                   'the attributes.  The attributes string must be valid YAML. ' \
                   'This schema defines the format of that YAML.',
    'type': 'object',
    'properties': {
        'attributes': {
                'type': 'object',
                'propertyNames': {
                    'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'
                },
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': [ 'unknown', 'string', 'integer', 'float', 'uuid' ]
                    },
                    'required': {
                        'type': 'boolean'
                    },
                    'unique': {
                        'type': 'string',
                        'enum': [ 'false', 'true', 'within_parent' ]
                    },
                    'identifying': {
                        'oneOf': [
                            {
                                'description': 'Indicate an identifying attribute set with just one attribute.  Default false.',
                                'type': 'boolean'
                            },
                            {
                                'description': 'Indicate an attribute in an identifying attribute set (ordered set), and where it appears in that set (1-based)',
                                'type': 'number',
                                'minimum': 1
                            }
                        ]

                    }
                },
                #'additionalProperties': 'false'
        },
        'desc': {
            'description': 'A brief statement that explains what the entity is',
            'type': 'string',
            'maxLength': 20000
        },
        'note': {
            'description': 'Additional notes on the entity',
            'type': 'string',
            'maxLength': 20000
        }
    },
    #'additionalProperties': 'false'
    # ... is there a way to constrain attribute names to be unique? ...
}


json_schema_graphml_enum = {
    '$schema': 'http://json-schema.org/schema#',
    '$id': 'http://cisco.com/zepster.graphml_enum.schema.json',
    'title': 'ZepstER schema for format of enums in the attribute block in an entity in yEd',
    'description': 'In the yEd graph editor, using the E-R (Entity-Relationship) diagram, ' \
                   'an entity symbol is used for two purposes: to define entities proper, and ' \
                   'to define enums.  Within the entity symbol, there are two strings: ' \
                   'an entity name and a string to represent ' \
                   'the attributes.  The attributes string must be valid YAML, ' \
                   'but that YAML has a different schema if the entity symbol is being used ' \
                   'to define an enum.  This schema defines the format of that YAML for an enum.',
    'definitions': {
        'enum_array': {
            'type': 'array',
            'items': {
                'oneOf': [
                    {
                        'description': 'An enum value',
                        'type': 'string',
                        'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                        'maxLength': 500
                    },
                    {
                        'description': 'An enum value with optional description and/or note',
                        'type': 'object',
                        'properties': {
                            'value': {
                                'description': 'An enum value',
                                'type': 'string',
                                'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                                'maxLength': 500
                            },
                            'desc': {
                                'description': 'A brief statement that explains what the enum value is for',
                                'type': 'string',
                                'maxLength': 20000
                            },
                            'note': {
                                'description': 'Additional notes on the enun value',
                                'type': 'string',
                                'maxLength': 20000
                            },
                        },
                        'required': [ 'value' ],
#                            'additionalProperties': 'false'
                    }
                ]
            }
        }
    },
    'oneOf': [
        { '$ref': '#/definitions/enum_array' },
        {
            'description': 'An array of enum values with an optional description and/or note on ' \
                           'the enum values as a whole',
            'type': 'object',
            'properties': {
                'values': { '$ref': '#/definitions/enum_array' },
                'desc': {
                    'description': 'A brief statement that explains what the set of enum values is for',
                    'type': 'string',
                    'maxLength': 20000
                },
                'note': {
                    'description': 'Additional notes on the set of enun values',
                    'type': 'string',
                    'maxLength': 20000
                }
            }
        }
    ]
}
# ...and constrain array items to be unique

