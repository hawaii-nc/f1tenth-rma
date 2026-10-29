from setuptools import find_packages, setup

package_name = 'f1tenth_research'

setup(
    name=package_name,
    version='1.0.0',
    # find_packages so envs/, models/, etc. get installed too (bug C11)
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'numpy', 'torch', 'gymnasium', 'pyyaml', 'scipy'],
    zip_safe=True,
    maintainer='Nathan Chong',
    maintainer_email='hawaii-nc@users.noreply.github.com',
    description='Rapid Motor Adaptation for F1TENTH: training, evaluation, safety metrics',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop = f1tenth_research.teleop_node:main',
            'pure_pursuit = f1tenth_research.pure_pursuit:main',
            'recorder = f1tenth_research.recorder_node:main',
            'il_driver = f1tenth_research.il_driver:main',
        ],
    },
)
