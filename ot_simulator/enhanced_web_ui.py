"""Enhanced Professional Web UI with real-time visualization and natural language control.

Features:
- Real-time sensor data charts (Chart.js)
- WebSocket streaming
- Integrated natural language chat interface
- Professional Databricks branding
- Multi-sensor overlay
- Historical data playback

This module now acts as a compatibility wrapper, importing from the modular web_ui package.
"""

from __future__ import annotations

# Import and re-export from the modular package
from ot_simulator.web_ui import EnhancedWebUI

__all__ = ["EnhancedWebUI"]
