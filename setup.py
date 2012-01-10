from setuptools import setup, find_packages

setup(
    name='cfmi',
    version='0.1',
    url='https://github.com/nocko/cfmi',
    license='BSD',
    author='Shawn Nock',
    author_email='sn253@georgetown.edu',
    description='A comprehensive MRI Lab website including scheduling, billing, and image retreival',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask>=0.7',
        'Flask-Cache',
        'Flask-SQLAlchemy',
        'Flask-WTF',
        'Flask-Testing',
        'FormAlchemy',
        'python-ldap',
        'MySQL-python',
        'pam==0.1.3',
        'nose',
        'python-memcache'
    ],
    dependency_links=['http://atlee.ca/software/pam/dist/0.1.3'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
