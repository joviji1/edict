"""Edict backend worker package.

Keep package init side-effect free.
Do not import worker modules here, otherwise `python -m app.workers.xxx`
will preload the target module through package init and trigger runpy warnings.
"""
