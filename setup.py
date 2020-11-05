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


Package setup for Zepster project

Note:
    Uses Markdown instead of RST for the README
    per https://pypi.org/project/gfm-markdown-description-example/
'''

from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(name='zepster',
      version='0.1.1',
      description='Generate data-related artifacts from an Entity-Relationship diagram',
      long_description=long_description,
      long_description_content_type="text/markdown",
      classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Database',
      ],
      keywords='database data er entity relationship diagram model modeling MDE',
      url='https://github.com/cisco/zepster',
      author='Steven Hand',
      author_email='zepster@datasciguy.com',
      license='Apache',
      packages=['zepster'],
      install_requires=[
          'cardinality',
          'click',
          'jsonschema',
          'loguru',
          'PyYAML',
          'toposort'
      ],
      include_package_data=True,
      zip_safe=False)
