include:
  - .install
  - .user

{% from "couchdb/map.jinja" import couchdb with context %}

couchdb_install_service:
  file.copy:
    - name: /etc/init.d/couchdb
    - source: {{couchdb.tmp_dir}}/apache-couchdb-{{couchdb.version}}/etc/init/couchdb
    - force: True
    - require:
      - cmd: couchdb_install
      - user: couchdb_user
      - file: /usr/local/etc/couchdb
      - file: /usr/local/var/lib/couchdb
      - file: /usr/local/var/log/couchdb
      - file: /usr/local/var/run/couchdb

service_set_executable:
  cmd.run:
    - name: chmod +x /etc/init.d/couchdb
    - cwd:  {{couchdb.tmp_dir}}/apache-couchdb-{{couchdb.version}}
    - require:
      - file: couchdb_install_service

couchdb:
  service.running:
    - require:
      - cmd: service_set_executable