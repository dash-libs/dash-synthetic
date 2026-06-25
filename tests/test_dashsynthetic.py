"""Unit tests for SyntheticGenerator (no Spark required)."""
import pytest


def test_import():
    import dashsynthetic
    assert hasattr(dashsynthetic, "__version__")


def test_launch_importable():
    from dashsynthetic import launch
    assert callable(launch)


def test_main_class_importable():
    from dashsynthetic import SyntheticGenerator
    assert SyntheticGenerator is not None
