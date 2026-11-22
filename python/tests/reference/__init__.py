"""The validator as it stood before its schema walk was compiled.

Copies of ``timetoshare/validate.py`` and ``timetoshare/ids.py`` at commit
20fabae, the modules the compiled schema check changed, their imports
pointed at each other and at the unchanged modules of ``timetoshare``.
``test_validator_parity.py`` alone reads them: they are the oracle the
validator's diagnostics are compared with, never code to maintain.
"""
