import setuptools

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Information Technology',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
]

setuptools.setup(
    name='ospurge',
    version='0.1',
    description='OpenStack project resources cleaner',
    url='https://github.com/JordanP/openstack-snippets',
    author='Jordan Pittier',
    author_email='jordan.pittier@gmail.com',
    license='Apache 2.0',
    install_requires=open('requirements.txt').read().splitlines(),
    classifiers=classifiers,
    packages=['ospurge'],
    entry_points={
        'console_scripts': [
            'ospurge = ospurge.main:main',
        ],
    }
)
