#!/usr/bin/python3
import subprocess
from watchgod import watch
nginxconf = '/share/www/beton/nginx/beton.conf'

for changes in watch(nginxconf):
    result = subprocess.run(['/usr/sbin/nginx', '-s', 'reload'], capture_output=True, text=True)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
