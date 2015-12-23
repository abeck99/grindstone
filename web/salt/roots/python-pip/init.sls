python-pip:
  pkg.installed

Upgrade pip:
  cmd.run:
    - name: pip install --upgrade pip
    - require:
      - pkg: python-pip

pyOpenSSL:
  pkg.installed

python-devel:
  pkg.installed

virtualenv:
    pip.installed:
        - require:
            - pkg: python-pip
            - cmd: Upgrade pip
            - pkg: pyOpenSSL

virtualenvwrapper:
    pip.installed:
        - require:
            - pip: virtualenv

virtualenv-envs-1:
  file.append:
    - name: /home/vagrant/.bashrc
    - text: export WORKON_HOME=$HOME/.virtualenvs


virtualenv-envs-2:
  file.append:
    - name: /home/vagrant/.bashrc
    - text: source /usr/bin/virtualenvwrapper.sh
    - require:
        - file: virtualenv-envs-1
