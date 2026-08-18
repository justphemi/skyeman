#!/usr/bin/env python
"""Skyeman Inc. - Django management script.
Run administrative tasks like running the dev server, migrating the DB, etc.
"""
import os
import sys


def main():
    """Run standard Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skyeman_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and on PYTHONPATH. "
            "Try: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
