/home/vagrant/.virtualenvs/app:
    virtualenv.managed:
        - user: vagrant
        - requirements: /web-app/requirements.txt

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
