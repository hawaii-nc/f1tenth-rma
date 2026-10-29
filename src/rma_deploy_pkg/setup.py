from setuptools import setup
import os
from glob import glob

package_name = 'rma_deploy_pkg'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'checkpoints'), glob('checkpoints/*.pt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ncchong',
    maintainer_email='you@example.com',
    description='RMA policy deployment for F1Tenth real car',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'rma_deployment_node = rma_deploy_pkg.rma_deployment_node:main',
        ],
    },
)
