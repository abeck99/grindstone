couchdb:
  pkg:
    - installed

  service.running:
    - enable: True
    - reload: True

nodejs:
  pkg.installed

npm:
  pkg.installed:
    - require:
      - pkg: nodejs

/usr/bin/node:
  file.symlink:
    - target: /usr/bin/nodejs

grunt-cli:
  npm.installed:
    - require:
      - pkg: npm

fauxton-repo:
  git.latest:
    - name: https://github.com/apache/couchdb-fauxton.git
    - target: /web-app-deps/fauxton
    - rev: v1.0.7

fauxton-npm-deps:
  cmd.run:
    - name: sudo npm install
    - cwd: /web-app-deps/fauxton
    - require:
      - git: fauxton-repo
      - pkg: npm





# grunt-cli:
#   npm.installed:
#     - require:
#       - pkg: npm
#
# fauxton-repo:
#   git.latest:
#     - name: https://github.com/apache/couchdb-fauxton.git
#     - target: /web-app-deps/fauxton
#     - rev: v1.0.7
#
# fauxton-npm-deps:
#   cmd.run:
#     - name: sudo npm install
#     - cwd: /web-app-deps/fauxton
#     - require:
#       - git: fauxton-repo
#       - pkg: npm
#
# run-fauxton:
#   cmd.run:
#     - name: grunt dev
#     - cwd: /web-app-deps/fauxton
#     - require:
#       - service: couchdb
#       - cmd: fauxton-npm-deps
#       - npm: grunt-cli



# fauxton:
#   npm.installed:
#     - require:
#       - pkg: npm
#       - file: /usr/bin/node
#
# grunt-cli:
#   npm.installed:
#     - require:
#       - npm: fauxton
#
# run-fauxton:
#   cmd.run:
#     - name: fauxton
#     - require:
#       - service: couchdb
#       - npm: grunt-cli

