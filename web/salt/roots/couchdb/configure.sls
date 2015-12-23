include:
  - .source

{% from "couchdb/map.jinja" import couchdb with context %} 

ecl_env:
   environ.setenv:
     - name: ERL
     - value: /usr/local/lib/erlang/bin/erl
     - update_minion: True

eclc_env:
   environ.setenv:
     - name: ERLC
     - value: /usr/local/lib/erlang/bin/erlc
     - update_minion: True

curl_config_env:
   environ.setenv:
     - name: CURL_CONFIG
     - value: /usr/bin/curl-config
     - update_minion: True

couchdb_configure:
  cmd.run:
    - name: ./configure
    - cwd: {{couchdb.tmp_dir}}/apache-couchdb-{{couchdb.version}}
    - unless: test -f {{couchdb.tmp_dir}}/apache-couchdb-{{couchdb.version}}/src/Makefile  
    - require:
      - archive: couchdb_extract_source
      - environ: ecl_env
      - environ: eclc_env
      - environ: curl_config_env

     