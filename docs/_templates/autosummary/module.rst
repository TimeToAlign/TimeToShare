{{ fullname | escape | underline }}

.. automodule:: {{ fullname }}
{%- if modules %}
   :no-members:

.. autosummary::
   :toctree:
   :recursive:
{% for item in modules %}
   {{ item.split(".")[-1] }}
{%- endfor %}
{% endif %}
