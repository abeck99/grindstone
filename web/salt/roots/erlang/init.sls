wget:
  pkg.installed


erlang_create_tmp:
  file.directory:
    - name: /tmp/erlang-build
    - makedirs: True


erlang_extract_source:
  archive.extracted:
    - name: /tmp/erlang-build
    - source: http://erlang.org/download/otp_src_R16B02.tar.gz
    - source_hash: ca63bcde0e5ae0f2df9457f97b3115a4
    - archive_format: tar
    - if_missing: /tmp/erlang-build/otp_src_R16B02
    - tar_options: z
    - require:
      - file: erlang_create_tmp


erlang_configure:
  cmd.run:
    - name: ./configure
    - cwd: /tmp/erlang-build/otp_src_R16B02
    - unless: test -f /tmp/erlang-build/otp_src_R16B02/Makefile
    - require:
      - archive: erlang_extract_source


erlang_install:
  cmd.run:
    - name: make && make install
    - unless: test -f /usr/local/bin/erlc
    - cwd: /tmp/erlang-build/otp_src_R16B02
    - require:
      - cmd: erlang_configure
