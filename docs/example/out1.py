'''
Enum definitions generated by Zepster
Source: out1.erml
Generated: 2020-10-15T22:02:28.002324
'''

from enum import Enum, unique


@unique
class Enum_headstock(Enum):
    MARTIN_STYLE = 1
    GUILD_STYLE = 2
    CLASSICAL = 3
    INLINE = 4


@unique
class Enum_fin_location(Enum):
    DORSAL = 1
    VENTRAL = 2
    PECTORAL = 3
    PELVIC = 4
    CAUDAL = 5


@unique
class Enum_matter(Enum):
    '''
    Description:
    Matter state.  Do we need a paper?
    Note:
    These are not the official values.  This is just a placeholder for the real values.
    '''
    SOLID = 1
    # Description:
    # Is semisolid a solid or a liquid?
    LIQUID = 2
    GAS = 3
    PLASMA = 4

