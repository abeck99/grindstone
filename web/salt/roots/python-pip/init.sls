python-pip:
  pkg.installed

Upgrade pip:
  cmd.run:
    - name: pip install --upgrade pip
    - require:
      - pkg: python-pip

python-openssl:
  pkg.installed

python-dev:
  pkg.installed

virtualenv:
    pip.installed:
        - require:
            - pkg: python-pip
            - cmd: Upgrade pip
            - pkg: python-openssl

virtualenvwrapper:
    pip.installed:
        - require:
            - pip: virtualenv
