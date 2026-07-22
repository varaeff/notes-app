"""Boundary for the future reminder delivery worker.

The worker is intentionally not wired into application startup yet. The next
feature step can put the scan loop here without mixing delivery orchestration
into routers or Telegram settings services.
"""
