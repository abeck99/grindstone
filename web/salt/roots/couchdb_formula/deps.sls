{% from "couchdb/map.jinja" import couchdb with context %}

{% for pkg in couchdb.group_packages %}
{{pkg}}:
  pkg.group_installed
{% endfor %}

couchdb_install_deps:
  pkg.installed:
    - pkgs:
       {% for pkg in couchdb.packages %}
       - {{pkg}}
       {% endfor %}



