python-pip:
    pkg.installed

pyopenssl:
	pkg.installed

ndg-httpsclient:
	pkg.installed

pyasn1:
	pkg.installed

python-virtualenv:
    pip:
        - installed

        - require:
            - pkg: pyopenssl
            - pkg: ndg-httpsclient
            - pkg: pyasn1

python-virtualenvwrapper:
    pip:
        - installed

        - require:
            - pip: python-virtualenv
