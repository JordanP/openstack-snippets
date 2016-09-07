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
    name='openstack-snippets',
    version='0.1',
    description='A CLI tool to list long running Rackspace Cloud servers.',
    url='https://github.com/JordanP/openstack-snippets',
    author='Jordan Pittier',
    author_email='jordan.pittier@gmail.com',
    license='Apache 2.0',
    install_requires=open('requirements.txt').read().splitlines(),
    classifiers=classifiers,
    packages=['.'],
    entry_points={
        'console_scripts': [
            'vmcleaner = vm_cleaner:main',
        ],
    }
)
