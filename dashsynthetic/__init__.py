"""
DashSynthetic — Synthetic data generation for Databricks.
Launch the UI with dashsynthetic.launch() inside a Databricks notebook.
"""
from dashsynthetic.generator import SyntheticGenerator
from dashsynthetic.ui import launch

__version__ = "0.1.0"
__all__ = ["SyntheticGenerator", "launch"]
