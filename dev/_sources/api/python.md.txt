# Python API

The package `timetoshare` validates, reads and writes manifests and checks
the table types. Install it with `pip install timetoshare`, and with
`pip install "timetoshare[tables]"` for {py:mod}`timetoshare.tables`.

The package root re-exports the public names of its modules (its
`__all__`), so `from timetoshare import validate` and
`from timetoshare.validate import validate` name the same function. Each
name is documented in the module that defines it. The validator,
{doc}`timetoshare.validate <validate>`, has its own page, since the package
root's `validate` is the function of that name.

```{toctree}
:hidden:

validate
```

% The modules are listed by hand: a recursive autosummary of the package would
% take the root's `validate` function for the module. A new module goes here.

```{eval-rst}
.. automodule:: timetoshare
   :no-members:

.. autosummary::
   :toctree: generated
   :recursive:

   catalogue
   defaults
   files
   fixtures
   font
   ids
   manifest
   serialization
   statements
   styles
   tables
   validation
```
