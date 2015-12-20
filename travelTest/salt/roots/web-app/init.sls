epel-release:
  pkg.installed

nodejs:
  pkg.installed:
    - require:
      - pkg: epel-release

npm:
  pkg.installed

couchbase:
  npm.installed:
    - require:
      - pkg: npm

node-gyp:
  npm.installed:
    - require:
      - pkg: npm

try-cb-nodejs:
  git.latest:
    - name: https://github.com/couchbaselabs/try-cb-nodejs.git
    - target: /home/vagrant/try-cb


Install depdencies:
  cmd.run:
    - name: npm install
    - cwd: /home/vagrant/try-cb
    - require:
      - pkg: npm
      - git: try-cb-nodejs
