grindstone:
  user.present:
    - fullname: Grindstone
    - home: /home/grindstone/

virtualenv-envs-1:
  file.append:
    - name: /home/grindstone/.bashrc
    - text: export WORKON_HOME=$HOME/.virtualenvs
    - require:
      - user: grindstone

virtualenv-envs-2:
  file.append:
    - name: /home/grindstone/.bashrc
    - text: source /usr/local/bin/virtualenvwrapper.sh
    - require:
        - file: virtualenv-envs-1

/home/grindstone/.virtualenvs/app:
  virtualenv.managed:
    - requirements: /web-app/requirements.txt
    - user: grindstone
    - require:
      - user: grindstone

ufw:
  pkg:
    - installed
  ufw.enabled:
    - require:
      - pkg: ufw


ufw-ssh-futon:
  ufw.allowed:
    - protocol: tcp
    - to_port: 5984
    - require:
      - pkg: ufw


ufw-ssh-fauxton:
  ufw.allowed:
    - protocol: tcp
    - to_port: 8000
    - require:
      - pkg: ufw

/etc/init/grindstone.conf:
  file.managed:
    - source: salt://web-app/files/grindstone.conf
    - mode: 644

grindstone-service:
  service.running:
    - name: grindstone
    - enable: True
    - reload: True

    - require:
      - file: virtualenv-envs-2
      - file: /etc/init/grindstone.conf
      - virtualenv: /home/grindstone/.virtualenvs/app
