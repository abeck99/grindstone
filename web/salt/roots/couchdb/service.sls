include:
  - .install
  - .user

{% from "couchdb/map.jinja" import couchdb with context %}

couchdb_install_service:
  file.copy:
    - name: /lib/systemd/system/couchdb.service
    - source: /salt/etc/couchdb.service
    - force: True
    - require:
      - cmd: couchdb_install
      - user: couchdb_user
      - file: /usr/local/etc/couchdb
      - file: /usr/local/var/lib/couchdb
      - file: /usr/local/var/log/couchdb
      - file: /usr/local/var/run/couchdb


couchdb:
  service.running:
    - require:
      - file: couchdb_install_service