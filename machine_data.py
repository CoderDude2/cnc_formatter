from dataclasses import dataclass
from enum import Enum


class Diameter(Enum):
    PI10 = 0
    PI14 = 1


class AbutmentType(Enum):
    DS = 1
    ASC = 2
    AOT_AND_TLOC = 3
    AOT_PLUS = 4


@dataclass
class MachineData:
    machine_number: int
    supported_diameter: Diameter
    supported_abutment: AbutmentType
    ending_machine_code: str
