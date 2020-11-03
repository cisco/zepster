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


JSON schema for Entity-Relationship Markup Language (ERML)
For the Zepster project
'''

json_schema_erml = {
    '$schema': 'http://json-schema.org/schema#',
    '$id': 'http://cisco.com/zepster.erml.schemm.json', \
    'title': 'ZepstER schema for Entity-Relationship Markup Language (ERML)',
    'type': 'object',
    'properties': {
        'generated_datetime': { 'type': 'string' },
        'source': { 'type': 'string' },
        'entities': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'entity': {
                        'type': 'object',
                        'propertyNames': {
                            'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                            'maxLength': 500
                        },
                        'properties': {
                            'type': {
                                'type': 'string',
                                'enum': [ 'unknown', 'string', 'integer', 'float', 'uuid' ]
                            },
                            'required': {
                                'type': 'string',
                                'enum': [ 'false', 'true' ]
                            },
                            'unique': {
                                'type': 'string',
                                'enum': [ 'false', 'true', 'within_parent' ]
                            }
                        }
                    }
                }
            }
        },
        'relationships': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'relationship': {
                        'type': 'object',
                        'properties': {
                            'defining': {
                                'type': 'string',
                                'enum': [ 'false', 'true' ]
                            },
                            'relationships' : {
                                'type': 'object',
                                'properties': {
                                    'participants': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'kind': {
                                                    'type': 'string',
                                                    'enum': [ 
                                                        'one', 
                                                        'subclass', 
                                                        'base_class', 
                                                        'zero_or_more',
                                                        'zero_or_one' 
                                                    ]
                                                },
                                                'name': {
                                                    'type': 'string',
                                                    'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                                                    'maxLength': 500
                                                }
                                            }
                                        }
                                    } 
                                }
                            }
                        } 
                    }
                }
            }
        },
        'enums': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'enum': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                                'maxLength': 500
                            },
                            'values': {
                                'type': 'array',
                                'items': {
                                    'oneOf': [
                                        {
                                            'type': 'string',
                                            'pattern': '^[A-Za-z_][A-Za-z0-9_]*$',
                                            'maxLength': 500
                                        },
                                        {
                                            'type': 'object',
                                            'properties': {
                                                'value': {
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
                                          # 'additionalProperties': 'false'
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
