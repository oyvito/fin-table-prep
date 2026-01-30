"""
Analysemoduler for fin-stat-prep.
"""

from .variable_pairs import detect_variable_pairs
from .value_columns import detect_value_columns
from .aggregation import detect_aggregation_patterns_v2
from .column_mapping import find_column_mapping_with_codelists

__all__ = [
    'detect_variable_pairs',
    'detect_value_columns', 
    'detect_aggregation_patterns_v2',
    'find_column_mapping_with_codelists'
]
