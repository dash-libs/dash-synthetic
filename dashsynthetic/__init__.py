"""
DashSynthetic — Synthetic data generation for Databricks.
Launch the UI with dashsynthetic.launch() inside a Databricks notebook.
"""
from dashsynthetic.generator import MultiTableGenerator, SyntheticGenerator
from dashsynthetic.relationships import RelationshipGraph
from dashsynthetic.ui import launch

__version__ = "0.1.2"
__all__ = ["SyntheticGenerator", "MultiTableGenerator", "RelationshipGraph", "launch"]
