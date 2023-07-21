import sys
import dnf
import logging

log = logging.getLogger('max-installable-dnf-transaction')
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log.setLevel(logging.INFO)

log.debug("Hello World!")

container = sys.argv[1]
from_container = f'FROM {container}\nRUN dnf update -y\nRUN dnf makecache\nRUN echo "max_parallel_downloads=20" >> /etc/dnf/dnf.conf\n\n'
dnf_install = "dnf --setopt=install_weak_deps=False install -y "
run_dnf_install = f'RUN {dnf_install}'

base = dnf.Base()
base.read_all_repos()
base.fill_sack()

q = base.sack.query()
a = q.available().filter(latest=1)
# We want to skip some of the packages that indicate what the system identifies as
# as the conflicts are... a bit strange, and I need to investigate
a = a.difference(base.sack.query().filter(provides="system-release"))
a = a.difference(base.sack.query().filter(provides="fedora-release-identity"))
# Also similar with logos
a = a.difference(base.sack.query().filter(provides="generic-logos"))
a = a.difference(base.sack.query().filter(provides="generic-logos-httpd"))
installed = base.sack.query().installed()

no_conflicts = set(pkg for pkg in a)
conflicts = {}

# We hard code some known bugs
hardcoded_conflicts = {
    'crypto-devel': 'sdl-crypto-devel',
#   file /usr/lib/python3.11/site-packages/speedtest.py from install of python3-speedtest-cli-2.1.3-7.fc38.noarch conflicts with file from package speedtest-cli-2.1.3-7.fc38.noarch
    'python3-speedtest-cli': 'speedtest-cli',
#  file /usr/lib64/libSoftFloat64.a conflicts between attempted installs of sdl-softfloat-devel-3.5.0-7.20220329git4b0c326.fc38.ppc64le and softfloat-devel-3.5.0-6.20210329git42f2f99.fc38.ppc64le
    'softfloat-devel': 'sdl-softfloat-devel',
#  file /usr/lib64/libdecNumber64.a from install of sdl-decnumber-devel-3.68.0-7.20220329git3aa2f45.fc38.ppc64le conflicts with file from package decnumber-devel-3.68.0-6.20210330gitda66509.fc38.ppc64le
    'decnumber-devel': 'sdl-decnumber-devel',
#  file /usr/lib/python3.11/site-packages/iso639/__init__.py from install of python3-iso-639-0.4.5-21.fc38.noarch conflicts with file from package python3-iso639-0.1.4-21.fc38.noarch
#  file /usr/lib/python3.11/site-packages/iso639/__pycache__/__init__.cpython-311.opt-1.pyc from install of python3-iso-639-0.4.5-21.fc38.noarch conflicts with file from package python3-iso639-0.1.4-21.fc38.noarch
#  file /usr/lib/python3.11/site-packages/iso639/__pycache__/__init__.cpython-311.pyc from install of python3-iso-639-0.4.5-21.fc38.noarch conflicts with file from package python3-iso639-0.1.4-21.fc38.noarch
    'python3-iso-639': 'python3-iso639',
#   file /usr/bin/xxhsum from install of golang-github-cespare-xxhash-2.1.2-8.fc38.ppc64le conflicts with file from package xxhash-0.8.1-4.fc38.ppc64le
    'golang-github-cespare-xxhash': 'xxhash',
#  file /usr/include/ieee754.h conflicts between attempted installs of glibc-headers-s390-2.37-4.fc38.noarch and glibc-headers-x86-2.37-4.fc38.noarch
#  file /usr/include/sys/elf.h conflicts between attempted installs of glibc-headers-s390-2.37-4.fc38.noarch and glibc-headers-x86-2.37-4.fc38.noarch
#  file /usr/include/sys/ptrace.h conflicts between attempted installs of glibc-headers-s390-2.37-4.fc38.noarch and glibc-headers-x86-2.37-4.fc38.noarch
#  file /usr/include/sys/ucontext.h conflicts between attempted installs of glibc-headers-s390-2.37-4.fc38.noarch and glibc-headers-x86-2.37-4.fc38.noarch
#  file /usr/include/sys/user.h conflicts between attempted installs of glibc-headers-s390-2.37-4.fc38.noarch and glibc-headers-x86-2.37-4.fc38.noarch
    'glibc-headers-s390': 'glibc-headers-x86',
#  file /usr/bin/short-regexp from install of golang-github-fvbommel-util-0.0.3-8.fc38.ppc64le conflicts with file from package golang-vbom-util-0-0.14.20190520gitefcd4e0.fc38.ppc64le
    'golang-vbom-util': 'golang-github-fvbommel-util',
#  file /usr/bin/infocmp from install of golang-github-xo-terminfo-0-0.9.20210113gitc22d04b.fc38.ppc64le conflicts with file from package ncurses-6.4-3.20230114.fc38.ppc64le
    'golang-github-xo-terminfo': 'ncurses',
#  file /usr/bin/gotail from install of golang-github-nxadm-tail-1.4.6-9.fc37.ppc64le conflicts with file from package golang-github-hpcloud-tail-1.0.0-10.20190325gita1dbeea.fc37.ppc64le
    'golang-github-nxadm-tail': 'golang-github-hpcloud-tail',
#  file /usr/bin/arping from install of golang-github-j-keck-arping-1.0.2-6.fc38.ppc64le conflicts with file from package iputils-20221126-2.fc38.ppc64le
    'golang-github-j-keck-arping': 'iputils',
#  - package coreutils-9.1-12.fc38.ppc64le from @System conflicts with coreutils-single provided by coreutils-single-9.1-11.fc38.ppc64le from fedora
    'coreutils': 'coreutils-single',
#  file /usr/bin/stress from install of golang-x-tools-stress-1:0.6.0-2.fc38.ppc64le conflicts with file from package stress-1.0.7-1.fc38.ppc64le
    'stress': 'golang-x-tools-stress',
#  file /usr/bin/mkinfo conflicts between attempted installs of golang-github-gdamore-tcell-1.4.0-8.fc38.ppc64le and golang-github-gdamore-tcell-2-2.6.0-1.fc38.ppc64le
    'golang-github-gdamore-tcell': 'golang-github-gdamore-tcell',
#  file /usr/bin/html2text from install of golang-jaytaylor-html2text-0-0.5.20220509gitbc68cce.fc38.ppc64le conflicts with file from package python3-html2text-2020.1.16-8.fc38.noarch
    'golang-jaytaylor-html2text': 'python3-html2text',
#  file /usr/bin/golex from install of golang-modernc-golex-1.0.1-12.fc38.ppc64le conflicts with file from package golang-modernc-lex-1.1.0-2.fc38.ppc64le
    'golang-modernc-golex': 'golang-modernc-lex',
#  file /usr/share/terminfo/f/foot from install of ncurses-term-6.4-3.20230114.fc38.noarch conflicts with file from package foot-terminfo-1.14.0-2.fc38.ppc64le
#  file /usr/share/terminfo/f/foot-direct from install of ncurses-term-6.4-3.20230114.fc38.noarch conflicts with file from package foot-terminfo-1.14.0-2.fc38.ppc64le
    'foot-terminfo': 'ncurses-term',
#  file /usr/share/terminfo/d/dvtm from install of ncurses-term-6.4-3.20230114.fc38.noarch conflicts with file from package dvtm-0.15-16.fc38.ppc64le
#  file /usr/share/terminfo/d/dvtm-256color from install of ncurses-term-6.4-3.20230114.fc38.noarch conflicts with file from package dvtm-0.15-16.fc38.ppc64le
    'ncurses-term': 'dvtm',
#  file /usr/bin/jsontoml conflicts between attempted installs of golang-github-pelletier-toml-1.9.5-2.fc38.ppc64le and golang-github-pelletier-toml-2-2.0.6-2.fc38.ppc64le
#  file /usr/bin/tomljson conflicts between attempted installs of golang-github-pelletier-toml-1.9.5-2.fc38.ppc64le and golang-github-pelletier-toml-2-2.0.6-2.fc38.ppc64le
#     file /usr/bin/tomll conflicts between attempted installs of golang-github-pelletier-toml-1.9.5-2.fc38.ppc64le and golang-github-pelletier-toml-2-2.0.6-2.fc38.ppc64le
    'golang-github-pelletier-toml': 'golang-github-pelletier-toml',
#  file /usr/bin/jwt conflicts between attempted installs of golang-github-dgrijalva-jwt-3.2.0-14.fc38.ppc64le and golang-github-jwt-3.2.2-6.fc38.ppc64le
    'golang-github-dgrijalva-jwt': 'golang-github-jwt',
#  file /usr/bin/gocomplete from install of golang-github-posener-complete-2-2.0.1~alpha.13-8.fc38.ppc64le conflicts with file from package golang-github-posener-complete-1.2.3-11.fc38.ppc64le
    'golang-github-posener-complete': 'golang-github-posener-complete',
#  file /usr/bin/douceur from install of golang-github-chris-ramon-douceur-0.2.0-8.20200910gitf346305.fc38.ppc64le conflicts with file from package douceur-0.2.0-17.fc38.ppc64le
    'golang-github-chris-ramon-douceur': 'douceur',
#  file /usr/bin/pebble conflicts between attempted installs of golang-github-cockroachdb-pebble-0-0.12.20210108git48f5530.fc38.ppc64le and golang-github-letsencrypt-pebble-2.3.1-8.fc38.ppc64le
    'golang-github-cockroachdb-pebble': 'golang-github-letsencrypt-pebble',
# https://bugzilla.redhat.com/show_bug.cgi?id=2223220 Cannot install texlive-base if multimarkdown is installed (infinite loop in scriptlet)
    'texlive-base': 'multimarkdown',
#   file /usr/bin/gosumcheck from install of golang-x-exp-0-0.49.20220330git053ad81.fc38.ppc64le conflicts with file from package golang-x-mod-0.8.0-1.fc38.ppc64le
    'golang-x-exp': 'golang-x-mod',
#  file /usr/bin/protoc-gen-grpc-gateway from install of golang-github-grpc-ecosystem-gateway-2-2.7.3-8.fc38.ppc64le conflicts with file from package golang-github-grpc-ecosystem-gateway-1.16.0-10.20230117git26318a5.fc38.ppc64le
    'golang-github-grpc-ecosystem-gateway-2': 'golang-github-grpc-ecosystem-gateway',
#          file /usr/bin/systemd-sysusers from install of systemd-253.4-1.fc38.ppc64le conflicts with file from package systemd-standalone-sysusers-253.5-1.fc38.ppc64le
#  file /usr/lib/systemd/systemd-shutdown from install of systemd-253.4-1.fc38.ppc64le conflicts with file from package systemd-standalone-shutdown-253.5-1.fc38.ppc64le
#          file /usr/bin/systemd-tmpfiles from install of systemd-253.4-1.fc38.ppc64le conflicts with file from package systemd-standalone-tmpfiles-253.5-1.fc38.ppc64le
    'systemd-standalone-sysusers': 'systemd',
    'systemd': 'systemd-standalone-sysusers',
    'systemd': 'systemd-standalone-shutdown',
    'systemd': 'systemd-standalone-tmpfiles',
#  file /usr/bin/systemd-sysusers from install of systemd-253.4-1.fc38.ppc64le conflicts with file from package systemd-standalone-sysusers-253.5-1.fc38.ppc64le
#  file /usr/lib/systemd/systemd-shutdown from install of systemd-253.4-1.fc38.ppc64le conflicts with file from package systemd-standalone-shutdown-253.5-1.fc38.ppc64le
    'kubernetes': 'systemd-standalone-sysusers',
    'kubernetes': 'systemd-standalone-shutdown',
    'kubernetes-client': 'systemd-standalone-sysusers',
    'kubernetes-client': 'systemd-standalone-shutdown',
#  file /usr/bin/openapi-gen conflicts between attempted installs of golang-k8s-code-generator-1.22.0-8.fc38.ppc64le and golang-k8s-kube-openapi-0-0.25.20210813git3c81807.fc38.ppc64le
    'golang-k8s-code-generator': 'golang-k8s-kube-openapi-0',
    'cadvisor': 'systemd',
#   file /usr/bin/openapi-gen conflicts between attempted installs of golang-k8s-code-generator-1.22.0-8.fc38.ppc64le and golang-k8s-kube-openapi-0-0.25.20210813git3c81807.fc38.ppc64le
    'golang-k8s-kube-openapi': 'golang-k8s-code-generator',
    
#                            file /usr/bin/digest conflicts between attempted installs of golang-github-distribution-3-3.0.0-0.2.pre1.20221009git0122d7d.fc38.ppc64le and golang-github-docker-distribution-2.8.1-4.20220821gitbc6b745.fc38.ppc64le
#                          file /usr/bin/registry conflicts between attempted installs of golang-github-distribution-3-3.0.0-0.2.pre1.20221009git0122d7d.fc38.ppc64le and golang-github-docker-distribution-2.8.1-4.20220821gitbc6b745.fc38.ppc64le
#  file /usr/bin/registry-api-descriptor-template conflicts between attempted installs of golang-github-distribution-3-3.0.0-0.2.pre1.20221009git0122d7d.fc38.ppc64le and golang-github-docker-distribution-2.8.1-4.20220821gitbc6b745.fc38.ppc64le
    'golang-github-distribution-3': 'golang-github-docker-distribution',
#   file /usr/bin/chroma from install of golang-github-alecthomas-chroma-0.10.0-6.fc38.ppc64le conflicts with file from package golang-github-alecthomas-chroma-2-2.5.0-1.fc38.ppc64le
#  file /usr/bin/chromad from install of golang-github-alecthomas-chroma-0.10.0-6.fc38.ppc64le conflicts with file from package golang-github-alecthomas-chroma-2-2.5.0-1.fc38.ppc64le
    'golang-github-alecthomas-chroma': 'golang-github-alecthomas-chroma',
#   file /usr/bin/disco from install of mono-web-6.12.0-11.fc38.ppc64le conflicts with file from package golang-github-googleapis-gnostic-0.5.3-10.fc38.ppc64le
    'mono-web': 'golang-github-googleapis-gnostic',
    'netopeer2': 'systemd-standalone-sysusers',
#   file /usr/bin/build conflicts between attempted installs of golang-github-gohugoio-testmodbuilder-0-0.14.20201030git72e1e0c.fc38.x86_64 and edk2-tools-python-20230524-3.fc38.noarch
    'edk2-tools-python': 'golang-github-gohugoio-testmodbuilder',
# AL2023 minimal things
    'curl': 'curl-minimal',
    'gnupg2': 'gnupg2-minimal',
# more AL2023 things
# Error:
# Problem 1: package maven-amazon-corretto11-1:3.8.4-3.amzn2023.0.4.noarch conflicts with maven-jdk-binding provided by maven-amazon-corretto17-1:3.8.4-3.amzn2023.0.4.noarch
#   - package maven-amazon-corretto17-1:3.8.4-3.amzn2023.0.4.noarch conflicts with maven-jdk-binding provided by maven-amazon-corretto11-1:3.8.4-3.amzn2023.0.4.noarch
# - conflicting requests
    'maven-amazon-corretto17': 'maven-amazon-corretto11',
    'maven-amazon-corretto11': 'maven-amazon-corretto17',
# Problem 2: problem with installed package dnf-4.12.0-2.amzn2023.0.4.noarch
# - package microdnf-dnf-3.8.1-1.amzn2023.0.1.x86_64 conflicts with dnf provided by dnf-4.12.0-2.amzn2023.0.4.noarch
# - conflicting requests
    'microdnf-dnf': 'dnf',
    'dnf': 'microdnf-dnf',
#   file /usr/share/xmvn/conf/toolchains.xml conflicts between attempted installs of maven-local-amazon-corretto11-6.0.0-7.amzn2023.0.5.noarch and maven-local-amazon-corretto8-6.0.0-7.amzn2023.0.5.noarch
#  file /usr/share/xmvn/conf/toolchains.xml conflicts between attempted installs of maven-local-amazon-corretto17-6.0.0-7.amzn2023.0.5.noarch and maven-local-amazon-corretto11-6.0.0-7.amzn2023.0.5.noarch
    'maven-local-amazon-corretto11': 'maven-local-amazon-corretto17',
# Problem: problem with installed package php8.1-common-8.1.16-1.amzn2023.0.2.x86_64
#   - package php8.1-common-8.1.16-1.amzn2023.0.2.x86_64 conflicts with php-common > 8.1.99 provided by php8.2-common-8.2.7-1.amzn2023.0.1.x86_64
#   - package php8.2-common-8.2.7-1.amzn2023.0.1.x86_64 conflicts with php-common < 8.2.0 provided by php8.1-common-8.1.16-1.amzn2023.0.2.x86_64
#    - package php8.2-common-8.2.7-1.amzn2023.0.1.x86_64 conflicts with php-common < 8.2.0 provided by php8.1-common-8.1.16-1.amzn2023.0.1.x86_64
#    - package php8.2-common-8.2.7-1.amzn2023.0.1.x86_64 conflicts with php-common < 8.2.0 provided by php8.1-common-8.1.14-1.amzn2023.0.2.x86_64
#    - package php8.2-pspell-8.2.7-1.amzn2023.0.1.x86_64 requires php-common(x86-64) = 8.2.7-1.amzn2023.0.1, but none of the providers can be installed
    'php8.1-common': 'php-common',
    'php8.2-common': 'php-common',
    'php-common': 'php8.1-common',
    'php-common': 'php8.2-common',
    'php8.2-pspell': 'php-common',
    'php8.2-pspell': 'php8.1-pspell',
    'php8.2-enchant': 'php8.2-enchant',
    'php8.2-tidy': 'php8.1-tidy',
    'php8.2-gmp': 'php8.1-gmp',
    'php8.2-snmp': 'php8.1-snmp',
    'php8.2-dba': 'php8.1-dba',
    'php8.2-ldap': 'php8.1-ldap',
    'php8.2-gd': 'php8.1-gd',
    'php8.2-bcmath': 'php8.1-bcmath',
    'php8.2-odbc': 'php8.1-odbc',
    'php8.2-pgsql': 'php8.1-pgsql',
    'php8.2-pdo': 'php8.1-pdo',
    'php8.2-ffi': 'php8.1-ffi',
    'php8.2-soap': 'php8.1-soap',
    'php8.2-mysqlnd': 'php8.1-mysqlnd',
    'php8.2-intl': 'php8.1-intl',
    'php8.2-opcache': 'php8.1-opcache',
    'php8.2-mbstring': 'php8.1-mbstring',
    'php8.2-devel': 'php8.1-devel',
    'php8.2-dbg': 'php8.1-dbg',
    'php8.2-xml': 'php8.1-xml',
    'php8.2-fpm': 'php8.1-xml',
    'php8.2-embedded': 'php8.1-embedded',
#  Problem 2: problem with installed package libpq-devel-15.0-2.amzn2023.0.1.x86_64
#  - package postgresql15-private-devel-15.0-1.amzn2023.0.2.x86_64 conflicts with libpq-devel provided by libpq-devel-15.0-2.amzn2023.0.1.x86_64
#  - package postgresql15-server-devel-15.0-1.amzn2023.0.2.x86_64 requires postgresql15-private-devel, but none of the providers can be installed
    'postgresql15-private-devel': 'libpq-devel',
    'gnupg2-smime': 'gnupg2-minimal',
    'libcurl-minimal': 'libcurl',

}
for k,v in hardcoded_conflicts.items():
    for p in a.filter(name=k):
        for p_c in a.filter(name=v):
            conflicts[p] = conflicts.get(p, []) + [p_c]
            conflicts[p_c] = conflicts.get(p, []) + [p]

log.debug(repr(conflicts))

just_broken = set({
##Error:
#  Problem 1: conflicting requests
#   - nothing provides (crate(clipboard/default) >= 0.5.0 with crate(clipboard/default) < 0.6.0~) needed by rust-reedline+clipboard-devel-0.16.0-1.fc38.noarch from fedora
# Problem 2: package rust-reedline+system_clipboard-devel-0.16.0-1.fc38.noarch from fedora requires crate(reedline/clipboard) = 0.16.0, but none of the providers can be installed
#  - conflicting requests
#  - nothing provides (crate(clipboard/default) >= 0.5.0 with crate(clipboard/default) < 0.6.0~) needed by rust-reedline+clipboard-devel-0.16.0-1.fc38.noarch from fedora
#(try to add '--skip-broken' to skip uninstallable packages)
'rust-reedline+clipboard-devel',
'rust-reedline+system_clipboard-devel',
})

# Now we compute the actual conflicts
for pkg in a:
    for c in pkg.conflicts:
        c_q = a.filter(provides=c)
        for c_pkg in c_q:
            log.debug('{} conflicts with {}'.format(pkg, c_pkg))
            # We avoid anything with any conflicts...
            if pkg.name in no_conflicts:
                no_conflicts.remove(pkg)
            if c_pkg.name in no_conflicts:
                no_conflicts.remove(c_pkg)
            conflicts[pkg] = conflicts.get(pkg, []) + [c_pkg]
    for provide in pkg.provides:
        if str(provide)[0] != '/':
            continue
        p_q = a.filter(provides=provide)
        for op in p_q:
            if op == pkg:
                continue
            log.info('{} conflicts with {} due to conflicting Provides: {}'.format(pkg, op, provide))
            if pkg.name in no_conflicts:
                no_conflicts.remove(pkg)
            if c_pkg.name in no_conflicts:
                no_conflicts.remove(c_pkg)
            conflicts[pkg] = conflicts.get(pkg, []) + [c_pkg]

log.debug(repr(conflicts))

# Now we have what we think is all the packages that we *could*
# just install as one big batch. But we also have to deal
# with repoclosure problems!
#
# So a simple "dnf install -y {no_conflicts}" would work on a set of repos
# with no repoclosure problems!
#
# We also have a dict of conflicts which we can deal with later

# So, let's go deal with repoclosure

def repoclosure_issues(to_check, available):
    '''Basically copied from repoclosure code in DNF'''
    unresolved = {}
    deps = set()
    for pkg in to_check:
        unresolved[pkg] = set()
        for req in pkg.requires:
            deps.add(req)
            unresolved[pkg].add(req)

        unresolved_deps = set(x for x in deps if not available.filter(provides=x))

        unresolved_transition = {k: set(x for x in v if x in unresolved_deps)
                                 for k, v in unresolved.items()}
        return {k: v for k, v in unresolved_transition.items() if v}

all_pkgs = base.sack.query().available().filter(latest=1)
all_pkgs_to_check = base.sack.query().available().filter(latest=1)
closure_problems = repoclosure_issues(all_pkgs_to_check, all_pkgs)
for k in closure_problems.keys():
    if k in no_conflicts:
        print(f"Removing {k.name} due to repoclosure issues")
        no_conflicts.remove(k)

for k in conflicts.keys():
    if k in no_conflicts:
        print(f"Removing {k.name} due to conflict")
        no_conflicts.remove(k)

with open('Dockerfile.onetxn', 'w') as f:
    f.write(from_container)
    f.write(run_dnf_install + ' '.join([n.name for n in no_conflicts]))
    f.write('\n')

with open('Dockerfile.one-then-therest', 'w') as f:
    f.write(from_container)
    f.write(run_dnf_install + ' '.join([n.name for n in no_conflicts]))
    f.write('\n')
    the_rest = []
    for k in closure_problems.keys():
        if k not in conflicts:
            the_rest.append(k.name)
    for p in the_rest:
        f.write(run_dnf_install)
        f.write(p)
        f.write('\n')
    f.write('\n')

no_extra_deps = []
no_extra_but_conflicts_installed = []
no_extra_but_conflicts = []
for p in no_conflicts:
    issues = repoclosure_issues([p], installed)
    if len(issues) != 0:
        continue
    to_conflict_installed = False
    for c in conflicts.get(p, []):
        if c in installed.filter(name=c.name):
            to_conflict_installed = True

    to_conflict = False
    for c in conflicts.get(p, []):
        if c in no_conflicts:
            to_conflict = True

    if to_conflict_installed:
        no_extra_but_conflicts_installed.append(p)
    elif to_conflict:
        no_extra_but_conflicts.append(p)
    else:
        no_extra_deps.append(p)

log.info(f"There are {len(no_extra_deps)} packages that don't have deps outside of the container image...")
log.info(f"There are {len(no_extra_but_conflicts_installed)} packages that don't have deps outside of the container image but have conflicts with something in it...")
log.info(f"There are {len(no_extra_but_conflicts)} packages that don't have deps outside of the container image but conflict with something else that also has no deps...")

with open('Dockerfile.noextradeps', 'w') as f:
    f.write(from_container)
    for p in sorted(no_extra_deps, key=lambda x: x.downloadsize):
        f.write(run_dnf_install + f'{p.name}\n')

with open('Dockerfile.noextradeps-onetxn', 'w') as f:
    f.write(from_container)
    f.write("COPY noextradeps-onetxn.sh /\n")
    f.write("RUN bash -x /noextradeps-onetxn.sh\n")
with open('noextradeps-onetxn.sh', 'w') as f:
    f.write(dnf_install)
    f.write(' '.join([x.name for x in no_extra_deps]))
    f.write('\n\n')

for step in [100,200,300,400,500,1000]:
    with open(f'Dockerfile.noextradeps-batched{step}', 'w') as f:
        f.write(from_container)
        pkgs = [x.name for x in sorted(no_extra_deps, key=lambda x: x.downloadsize)]
        for i in range(0, len(pkgs), step):
            f.write(run_dnf_install)
            f.write(' '.join(pkgs[i:i+step]))
            f.write('\n')

for step in [100,200,300,400,500,1000]:
    with open(f'Dockerfile.noextradeps1st_batched{step}', 'w') as f:
        f.write(from_container)
        pkgs = [x.name for x in sorted(no_extra_deps, key=lambda x: x.downloadsize)]
        for i in range(0, len(pkgs), step):
            f.write(f"# no_extra_deps step {i}\n")
            f.write(run_dnf_install)
            f.write(' '.join(pkgs[i:i+step]))
            f.write('\n')
        f.write("# DONE with no_extra_deps\n\n")
        nc_pkgs = []
        for x in no_conflicts:
            if x.name not in pkgs and x.name not in just_broken:
                nc_pkgs.append(x)
        n_c = [x.name for x in sorted(nc_pkgs, key=lambda x: x.downloadsize)]
        step=100
        for i in range(0, len(n_c), step):
            f.write(f"# no_conflicts step {i}\n")
            l = ' '.join(n_c[i:i+step])
            f.write(run_dnf_install + f'{l}\n')
        f.write('\n')

with open('Dockerfile.batched100', 'w') as f:
    f.write(from_container)
    step=100
    n_c = [k for k in sorted([n.name for n in no_conflicts])]
    for i in range(0, len(n_c), step):
        l = ' '.join(n_c[i:i+step])
        f.write(run_dnf_install + f'{l}\n')
    f.write('\n')

