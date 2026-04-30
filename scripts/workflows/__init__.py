"""Asyre Search workflow system — pre-built analysis pipelines."""

from .analyze import AnalyzeWorkflow
from .compare import CompareWorkflow
from .scout import ScoutWorkflow
from .audit import AuditWorkflow
from .monitor import MonitorWorkflow
from .pro import ProAnalyzeWorkflow

WORKFLOWS = {
    "analyze": AnalyzeWorkflow,
    "analyze-pro": ProAnalyzeWorkflow,
    "compare": CompareWorkflow,
    "scout": ScoutWorkflow,
    "audit": AuditWorkflow,
    "monitor": MonitorWorkflow,
}

__all__ = ["WORKFLOWS", "AnalyzeWorkflow", "ProAnalyzeWorkflow", "CompareWorkflow", "ScoutWorkflow", "AuditWorkflow", "MonitorWorkflow"]
